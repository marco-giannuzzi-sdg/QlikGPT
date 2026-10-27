#!/usr/bin/env python3
"""QlikGPT App Lineage: declarative, script-derived QVD producer/consumer graph.

GitHub QVS and app manifests are the source. This is not Qlik runtime lineage:
dynamic paths, untracked loads, remote SQL and cross-space DataFiles links
require a dedicated metadata connector rather than inference.
"""
from __future__ import annotations

from collections import defaultdict, deque
import argparse
import json
from pathlib import Path
import re
from urllib.parse import quote
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "lineage" / "APP_LINEAGE.md"
JSON_OUTPUT = ROOT / "lineage" / "graph.json"
BT = chr(96)

SOURCE_RE = re.compile(
    r"\bFROM\s+(?P<quoted>\[[^\]\r\n]+\]|'[^'\r\n]+'|\"[^\"\r\n]+\")"
    r"\s*\(\s*(?P<format>[a-z][a-z0-9]*)\s*(?:,[^)]*)?\)",
    re.IGNORECASE,
)
STORE_RE = re.compile(
    r"\bSTORE\s+(?P<table>[a-z_][a-z0-9_]*)"
    r"\s+INTO\s+(?P<quoted>\[[^\]\r\n]+\]|'[^'\r\n]+'|\"[^\"\r\n]+\")"
    r"\s*\(\s*(?P<format>[a-z][a-z0-9]*)\s*\)",
    re.IGNORECASE,
)
RESIDENT_RE = re.compile(r"\bRESIDENT\s+([a-z_][a-z0-9_]*)", re.IGNORECASE)
AUTO_RE = re.compile(r"\bAUTOGENERATE\s+(\d+)", re.IGNORECASE)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def without_comments(text: str) -> str:
    """Mask QVS line and block comments, preserving QVS line numbers."""
    # Full line comments. Do NOT split on //: lib://DataFiles is an URI.
    text = re.sub(
        r"(?m)^[ \t]*//[^\r\n]*",
        lambda m: " " * len(m.group()),
        text,
    )
    return re.sub(
        r"/\*.*?\*/",
        lambda m: re.sub(r"[^\r\n]", " ", m.group()),
        text,
        flags=re.DOTALL,
    )


def parse_qvs(text: str) -> dict:
    text = without_comments(text)
    parsed = {"reads": [], "writes": [], "residents": [], "autogenerate": []}
    def make_entry(match, direction):
        raw = match.group("quoted")[1:-1].strip()
        fmt = match.group("format").lower()
        if not raw:
            raise ValueError("Empty Qlik source URI")
        if not raw.startswith("lib://"):
            # Relative file paths cannot be safely compared across app spaces.
            raise ValueError(f"Qlik source path must declare lib://: {raw}")
        entry = {
            "uri": raw, "format": fmt,
            "line": text.count("\n", 0, match.start()) + 1,
        }
        if direction == "writes":
            entry["table"] = match.group("table")
        return entry
    for match in SOURCE_RE.finditer(text):
        parsed["reads"].append(make_entry(match, "reads"))
    for match in STORE_RE.finditer(text):
        parsed["writes"].append(make_entry(match, "writes"))
    parsed["residents"] = list(dict.fromkeys(
        m.group(1) for m in RESIDENT_RE.finditer(text)
    ))
    parsed["autogenerate"] = [int(m.group(1)) for m in AUTO_RE.finditer(text)]
    for direction in ("reads", "writes"):
        # A source can be read twice, but return a single declaration per line.
        parsed[direction].sort(key=lambda x: (x["line"], x["uri"]))
    return parsed


def registry() -> dict:
    # Reuse the existing deployment contract; never create a second source
    # of truth for application names, script paths or Qlik IDs.
    from deploy import APPS
    from semantic_catalog import MANIFESTS
    ids = load(ROOT / "deployment" / "app-ids.json")
    out = {}
    for key, name, script in APPS:
        if key.startswith("etl"):
            out[key] = {"key":key, "name":name, "type":"etl",
                        "script":script, "appId":ids.get(key)}
    for key, manifest_path in MANIFESTS.items():
        config = load(manifest_path)
        if key in out:
            raise ValueError(f"Duplicate application key {key}")
        out[key] = {"key":key, "name":config["appName"],
                    "type":"presentation", "script":config["loadScript"],
                    "manifest":manifest_path.relative_to(ROOT).as_posix(),
                    "appId":ids.get(key)}
    if not out:
        raise ValueError("Cannot build lineage without applications")
    for key, app in out.items():
        path = ROOT / app["script"]
        if not path.is_file() or ROOT not in path.resolve().parents:
            raise ValueError(f"{key}: missing/unsafe QVS {app['script']}")
        ident = app["appId"]
        if ident:
            try:
                UUID(ident)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{key}: invalid saved Qlik app ID") from exc
    return out


def edges_and_impacts(keys: list[str], connections: list[dict]) -> tuple[dict, dict]:
    adjacency = {key: set() for key in keys}
    for conn in connections:
        adjacency[conn["upstream"]].add(conn["downstream"])
    state = {}
    def visit(key):
        if state.get(key) == 1:
            raise ValueError(f"Cycle detected in app lineage at {key}")
        if state.get(key) == 2:
            return
        state[key] = 1
        for dest in sorted(adjacency[key]):
            visit(dest)
        state[key] = 2
    for key in keys:
        visit(key)
    impact = {}
    for key in keys:
        descendants = set()
        pending = deque(sorted(adjacency[key]))
        while pending:
            dest = pending.popleft()
            if dest in descendants:
                continue
            descendants.add(dest)
            pending.extend(sorted(adjacency[dest]))
        impact[key] = {
            "direct": sorted(adjacency[key]),
            "transitive": sorted(descendants),
            "indirect": sorted(descendants - adjacency[key]),
        }
    return {key: sorted(adjacency[key]) for key in keys}, impact


def build(applications: dict) -> dict:
    apps = {}
    resource_uses = defaultdict(lambda: {"reads": [], "writes": [], "format": ""})
    warnings = []
    for key, source in applications.items():
        app = {**source}
        parsed = parse_qvs((ROOT / app["script"]).read_text(encoding="utf-8"))
        app.update(parsed)
        apps[key] = app
        for direction in ("reads", "writes"):
            for entry in parsed[direction]:
                uri = entry["uri"]
                asset = resource_uses[uri]
                if asset["format"] and asset["format"] != entry["format"]:
                    raise ValueError(f"Same URI with incompatible data formats: {uri}")
                asset["format"] = entry["format"]
                asset[direction].append({"app": key, "script": app["script"], **entry})
        raw = without_comments((ROOT / app["script"]).read_text(encoding="utf-8"))
        if re.search(r"\bSQL\s+(?:SELECT|EXEC|WITH)\b|\bLIB\s+CONNECT\s+TO\b",
                     raw, flags=re.IGNORECASE):
            warnings.append(
                f"{key}: SQL/connect statements require additional connector-level lineage"
            )
        if re.search(r"\$\([^)]*\)", raw):
            warnings.append(f"{key}: dynamic QVS expressions/paths need manual verification")
    resources, links = [], []
    app_edges = defaultdict(set)
    for uri, uses in sorted(resource_uses.items()):
        producing = sorted({x["app"] for x in uses["writes"]})
        consuming = sorted({x["app"] for x in uses["reads"]})
        if len(producing) > 1:
            raise ValueError(
                f"Ambiguous QVD/file producer: {uri} written by {producing}"
            )
        producer = producing[0] if producing else None
        if not producer and consuming:
            warnings.append(
                f"Resource read with no QVS producer in this repository: {uri}"
            )
        resources.append({
            "id": f"resource:{uri}", "uri": uri, "format": uses["format"],
            "producer": producer, "consumers": consuming,
            "reads": uses["reads"], "writes": uses["writes"],
        })
        for target in consuming:
            if not producer or producer == target:
                continue
            app_edges[(producer, target)].add(uri)
            links.append({
                "upstream": producer, "downstream": target,
                "resource": uri, "kind": uses["format"],
            })
    connections = [
        {"upstream": up, "downstream": down, "resources": sorted(uris)}
        for (up, down), uris in sorted(app_edges.items())
    ]
    _, impact = edges_and_impacts(list(apps), connections)
    return {
        "schemaVersion": 1,
        "source": "QVS scripts and GitHub app registry (static declarations, not live Qlik metadata)",
        "tenant": load(ROOT / "deployment" / "app-ids.json").get("tenant"),
        "apps": apps,
        "resources": resources,
        "connections": connections,
        "resourceLinks": sorted(
            links, key=lambda x:(x["upstream"],x["downstream"],x["resource"])
        ),
        "impact": impact,
        "warnings": warnings,
    }


def app_link(report: dict, key: str) -> str:
    app = report["apps"][key]
    if app.get("appId") and report.get("tenant"):
        return f"[{app['name']}]({report['tenant']}/sense/app/{app['appId']})"
    return app["name"] + " (nessun App ID)"


def script_link(path: str, line: int | None = None) -> str:
    suffix = f"#L{line}" if line else ""
    return f"[{path}](../{path}{suffix})"


def graph_mermaid(report: dict, detailed: bool) -> list[str]:
    apps = report["apps"]
    if detailed:
        lines = ["flowchart LR"]
        app_ids = {key: f"app_{n}" for n,key in enumerate(apps)}
        asset_ids = {r["uri"]: f"asset_{n}" for n,r in enumerate(report["resources"])}
        for key,app in apps.items():
            short = "ETL1 — RAW" if key=="etl1" else (
                "ETL2 — TRANSFORM" if key=="etl2" else app["name"].replace("QlikGPT - ", "")
            )
            lines.append(f'    {app_ids[key]}["{short}"]')
        for resource in report["resources"]:
            label=resource["uri"].split("/")[-1]
            lines.append(f'    {asset_ids[resource["uri"]]}[("{label}")]')
            for record in resource["writes"]:
                lines.append(f'    {app_ids[record["app"]]} -->|STORE| {asset_ids[resource["uri"]]}')
            for record in resource["reads"]:
                lines.append(f'    {asset_ids[resource["uri"]]} -->|FROM| {app_ids[record["app"]]}')
    else:
        lines = ["flowchart LR"]
        ids = {key:f"app_{n}" for n,key in enumerate(apps)}
        for key,app in apps.items():
            lines.append(f'    {ids[key]}["{app["name"].replace("QlikGPT - ", "")}"]')
        for conn in report["connections"]:
            via=", ".join(uri.split("/")[-1] for uri in conn["resources"])
            lines.append(f'    {ids[conn["upstream"]]} -->|"{via}"| {ids[conn["downstream"]]}')
    return lines


def render(report: dict) -> str:
    apps = report["apps"]
    lines = [
        "# QlikGPT — App Lineage & Impact Analysis", "",
        "> Lineage **statico derivato dagli script QVS su GitHub**. Le dipendenze "
        "tra app sono inferite quando una scrive un QVD/file con STORE e "
        "un'altra legge lo stesso URI con FROM. Non è il lineage operativo "
        "rilevato dal tenant e non certifica l'ultimo reload né il contenuto del QVD.",
        "",
        "## Mappa delle dipendenze tra applicazioni", "",
        BT*3+"mermaid", *graph_mermaid(report, detailed=False), BT*3, "",
        "## Data flow — applicazioni e QVD", "",
        BT*3+"mermaid", *graph_mermaid(report, detailed=True), BT*3, "",
        "## Applicazioni e input/output", "",
        "| Applicazione | Script QVS | Legge | Produce |", "| --- | --- | --- | --- |",
    ]
    for key,app in apps.items():
        reads=", ".join(BT+x["uri"].split("/")[-1]+BT for x in app["reads"]) or "—"
        writes=", ".join(BT+x["uri"].split("/")[-1]+BT for x in app["writes"]) or "—"
        lines.append(f"| {app_link(report,key)} | {script_link(app['script'])} | {reads} | {writes} |")
    lines.extend(["", "## Dipendenze dirette", "",
                  "| App sorgente | App dipendente | QVD o file condiviso | Evidenza QVS |",
                  "| --- | --- | --- | --- |"])
    if not report["connections"]:
        lines.append("| — | — | Nessuna dipendenza inter-app rilevata | — |")
    for c in report["connections"]:
        for uri in c["resources"]:
            asset=next(a for a in report["resources"] if a["uri"]==uri)
            write=next(x for x in asset["writes"] if x["app"]==c["upstream"])
            read=next(x for x in asset["reads"] if x["app"]==c["downstream"])
            evidence=f"{script_link(write['script'],write['line'])} (STORE) / {script_link(read['script'],read['line'])} (FROM)"
            lines.append(
                f"| {app_link(report,c['upstream'])} | {app_link(report,c['downstream'])} | "
                f"{BT}{uri}{BT} | {evidence} |"
            )
    lines.extend(["", "## Impact Analysis — a valle di ogni app", "",
                  "Impatto **potenziale** della modifica o indisponibilità di un'app/del suo output. "
                  "Il report non avvia reload e non sostituisce l'analisi delle modifiche alle misure del Semantic Catalog.",
                  "",
                  "| Applicazione | Impatto diretto | Impatto indiretto | Totale a valle |",
                  "| --- | --- | --- | --- |"])
    for key in apps:
        impact=report["impact"][key]
        direct=", ".join(impact["direct"]) or "—"
        indirect=", ".join(impact["indirect"]) or "—"
        total=", ".join(impact["transitive"]) or "—"
        lines.append(f"| {app_link(report,key)} | {direct} | {indirect} | {total} |")
    lines.extend(["", "## Dettagli per applicazione", ""])
    for key,app in apps.items():
        upstream=sorted({c["upstream"] for c in report["connections"] if c["downstream"]==key})
        impact=report["impact"][key]
        lines.extend([
            f"### {app['name']}", "",
            f"- **Qlik Cloud:** {app_link(report,key)}",
            f"- **Script:** {script_link(app['script'])}",
            f"- **Upstream diretti:** {', '.join(upstream) if upstream else 'Nessuno nel repository'}",
            f"- **Downstream diretti:** {', '.join(impact['direct']) if impact['direct'] else 'Nessuno'}",
            f"- **Downstream complessivi:** {', '.join(impact['transitive']) if impact['transitive'] else 'Nessuno'}",
        ])
        if app["residents"]:
            lines.append("- **Tabelle RESIDENT locali:** "+", ".join(app["residents"]))
        if app["autogenerate"]:
            lines.append("- **Sorgente dati:** AUTOGENERATE "+", ".join(map(str,app["autogenerate"]))+" (dati sintetici)")
        for record in app["reads"]:
            lines.append(f"- **FROM ({record['format']}):** {BT}{record['uri']}{BT} — {script_link(app['script'],record['line'])}")
        for record in app["writes"]:
            lines.append(f"- **STORE ({record['format']}):** {BT}{record['uri']}{BT} — {script_link(app['script'],record['line'])}")
        lines.append("")
    if report["warnings"]:
        lines.extend(["## Elementi non risolti", ""])
        lines.extend("- "+warning for warning in report["warnings"])
        lines.append("")
    lines.extend([
        "## Ambito e limiti", "",
        "- L'identificazione è basata su letture FROM e scritture STORE dichiarate nei QVS versionati. "
        "Per QVD con nomi dinamici, INCLUDE non tracciati, SQL/REST, trasformazioni complesse o altri data source occorrono adattatori aggiuntivi.",
        "- Il collegamento tra URI DataFiles uguali **presuppone** che le app possano risolverli nello stesso spazio/percorso condiviso: la sola stringa lib:// non dimostra l'identità della risorsa se cambiano gli spazi.",
        "- Oggetti o app creati manualmente fuori dal repository non compaiono automaticamente. "
        "Per le Presentation aggiunte via manifest, il report individua automaticamente lo script condiviso.",
        "- Una dipendenza nel grafo esprime **potenziale propagazione** di una modifica ai dati, "
        "non una regola di scheduling: la CI attuale ha un processo di reload distinto.",
        "- Il Semantic Catalog governa misure, dimensioni e variabili; "
        "la [mappa semantica](../catalog/USAGE.md) è complementare al presente lineage dei dati.",
        "",
        "## Utilizzo", "",
        "- [Grafo machine-readable](graph.json) per integrazioni e controlli.",
        "- Analisi di una singola app: "+BT+"python3 ci/app_lineage.py --app etl1"+BT,
        "- Rigenerazione (GitHub Actions): "+BT+"python3 ci/app_lineage.py"+BT,
        "- Verifica che i report siano aggiornati: "+BT+"python3 ci/app_lineage.py --check"+BT,
        "",
    ])
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description="GitHub QlikGPT application/QVD lineage")
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--app",help="Show upstream and downstream impact of an app key")
    args=parser.parse_args()
    result=build(registry())
    if args.app:
        if args.app not in result["apps"]:
            raise ValueError(f"Unknown app: {args.app}")
        upstream=sorted({
            c["upstream"] for c in result["connections"]
            if c["downstream"]==args.app
        })
        print(json.dumps({
            "app":args.app, "upstreamDirect":upstream,
            **result["impact"][args.app],
        },indent=2,ensure_ascii=False))
    elif args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8")!=render(result):
            raise SystemExit("App lineage Markdown is stale")
        if not JSON_OUTPUT.is_file() or load(JSON_OUTPUT)!=result:
            raise SystemExit("App lineage JSON is stale")
        print("App lineage reports up to date")
    else:
        OUTPUT.parent.mkdir(parents=True,exist_ok=True)
        OUTPUT.write_text(render(result),encoding="utf-8")
        JSON_OUTPUT.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(f"App lineage: {len(result['apps'])} apps, "
              f"{len(result['resources'])} resources, "
              f"{len(result['connections'])} direct app edges, "
              f"{len(result['warnings'])} warnings.")


if __name__=="__main__":
    main()
