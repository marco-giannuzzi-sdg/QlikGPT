#!/usr/bin/env python3
"""Generate the declarative Semantic Catalog 2.0 usage/impact report.

The report is derived ONLY from catalog manifests and versioned dashboard JSON,
not runtime usage or Qlik sheet interaction events. Fail on bad references.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
C = ROOT / "catalog"
APP = ROOT / "apps"
OUTPUT = C / "USAGE.md"
OUTPUT_JSON = C / "usage.json"
TENANT = "https://sdggroup-it.eu.qlikcloud.com"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def read_catalog(kind):
    file = C / ({"measure": "measures.json", "dimension": "dimensions.json", "variable": "variables.json"}[kind])
    key = {"measure":"measures","dimension":"dimensions","variable":"variables"}[kind]
    arr = load(file)[key]
    ids = [m["id"] for m in arr]
    if len(ids) != len(set(ids)):
        raise ValueError(f"Duplicate {kind} IDs")
    return {m["id"]:m for m in arr}


def read_apps():
    data = {}
    apps = load(ROOT / "deployment" / "app-ids.json")
    for path in sorted(APP.glob("presentation[0-9]*.json")):
        if not re.fullmatch(r"presentation[0-9]+\.json", path.name):
            continue
        m = load(path)
        key = m["appKey"]
        data[key] = {
            **m, "manifest": path.relative_to(ROOT).as_posix(),
            "appId": apps.get(key, ""),
            "visuals": load(ROOT / m["dashboardSource"]),
        }
    return data


def nodes(sheet):
    """Walk top-level and nested QIX children; no synthetic or guessed refs."""
    stack=[sheet]
    while stack:
        item=stack.pop()
        yield item
        stack.extend(reversed(item.get("qChildren", [])))


def field_names(expr):
    return set(re.findall(r"\$\((vQlikGPT[A-Za-z0-9_]+)\)", expr or ""))


def generate():
    catalog = {kind:read_catalog(kind) for kind in ("measure","dimension","variable")}
    apps = read_apps()
    attrs={"measure":"catalogMeasures","dimension":"catalogDimensions","variable":"catalogVariables"}
    entry=[]
    for kind,items in catalog.items():
        for ident,item in items.items():
            entry.append({"kind":kind, "id":ident,
                "name":item.get("title",item.get("name")), "version":item.get("version"),
                "apps":[], "visuals":[], "definitions":item})
    lookup={(x["kind"],x["id"]):x for x in entry}
    warnings=[]
    for key,app in apps.items():
        subs={}
        for kind,attr in attrs.items():
            ids=app.get(attr,[])
            if len(ids)!=len(set(ids)):
                raise ValueError(f"{key}: duplicate subscriptions {attr}")
            missing=set(ids)-set(catalog[kind])
            if missing:raise ValueError(f"{key}: unknown {kind} references: {sorted(missing)}")
            subs[kind]=set(ids)
            for ident in ids:lookup[(kind,ident)]["apps"].append(key)
        for sheet in app["visuals"]:
            sheet_name=sheet.get("title",sheet.get("qInfo",{}).get("qId",""))
            for obj in nodes(sheet):
                visualid=obj.get("qInfo",{}).get("qId")
                qtype=obj.get("qInfo",{}).get("qType")
                if not visualid or not obj.get("qHyperCubeDef"):
                    continue
                cube=obj["qHyperCubeDef"]
                for qkind,qobjs in (("measure",cube.get("qMeasures",[])),
                                    ("dimension",cube.get("qDimensions",[]))):
                    for ref in qobjs:
                        ident=ref.get("qLibraryId")
                        if ident:
                            if ident not in subs[qkind]:
                                raise ValueError(f"{key}/{visualid}: missing catalog subscription for {qkind}:{ident}")
                            lookup[(qkind,ident)]["visuals"].append({
                                "app":key,"sheet":sheet_name,"visualId":visualid,
                                "visualType":qtype,
                            })
                        elif qkind=="dimension":
                            fields=ref.get("qDef",{}).get("qFieldDefs",[])
                            warnings.append(f"{key} · {visualid}: dimensione inline ({', '.join(fields)}) non collegata a master dimension")
                        else:
                            warnings.append(f"{key} · {visualid}: misura inline non governata")
                        # Variable references in inline component expressions.
                        serialized=json.dumps(ref,ensure_ascii=False)
                        for variable in catalog["variable"].values():
                            if variable["name"] in field_names(serialized) and variable["id"] in subs["variable"]:
                                lookup[("variable",variable["id"])]["visuals"].append({
                                    "app":key,"sheet":sheet_name,"visualId":visualid,
                                    "visualType":qtype,
                                })
    return {"schemaVersion":2,"source":"GitHub declarations (not QIX runtime usage)",
            "apps":{key:{"name":v["appName"],"appId":v["appId"],"manifest":v["manifest"]}
                    for key,v in apps.items()},
            "items":entry, "warnings":list(dict.fromkeys(warnings))}


def render(report):
    apps=report["apps"]
    lines=[
        "# QlikGPT — Semantic Catalog 2.0 | Usage & Impact",
        "",
        "> Report **generato dai manifest e dagli oggetti versionati su GitHub**. "
        "Le sottoscrizioni rappresentano master item attesi nelle app; le visualizzazioni "
        "sono ricavate dai riferimenti `qLibraryId` dichiarati, non da telemetria QIX runtime.",
        "",
        "## Applicazioni",
        "",
        "| Applicazione | Qlik Cloud | Manifest |",
        "| --- | --- | --- |",
    ]
    for key,app in apps.items():
        link=f"[Apri app]({TENANT}/sense/app/{app['appId']})" if app["appId"] else "Non creata"
        lines.append(f"| {app['name']} | {link} | [Manifest](../{app['manifest']}) |")
    lines.extend(["","## Matrice delle dipendenze","","**✓** = master item sottoscritto, **—** = assente. Il numero di grafici che lo referenziano è mostrato separatamente.",""])
    lines.append("| Tipo | Elemento | "+" | ".join(apps)+" | Grafici collegati |")
    lines.append("| --- | --- | "+" | ".join(":---:" for _ in apps)+" | ---: |")
    for e in report["items"]:
        subs=["✓" if app in e["apps"] else "—" for app in apps]
        count=len({(v["app"],v["visualId"]) for v in e["visuals"]})
        lines.append(f"| {e['kind']} | `{e['id']}` — {e['name']} | "+
            " | ".join(subs)+f" | {count} |")
    lines.extend(["", "## Impatto per oggetto", "",
                  "In caso di modifica, il deployment sincronizza **solo le app sottoscritte**. "
                  "Le visualizzazioni che usano `qLibraryId` ereditano la definizione aggiornata.", ""])
    for e in report["items"]:
        links=", ".join(f"[{key}]({TENANT}/sense/app/{apps[key]['appId']})"
                        for key in e["apps"]) or "Nessuna (disponibile per uso futuro)"
        ids=", ".join(f"`{x['app']}/{x['visualId']}`" for x in e["visuals"]) or "Nessuna referenza diretta"
        lines.extend([f"### {e['name']} · `{e['id']}`",
            f"**Tipo:** {e['kind']} · **Versione:** {e['version']}",
            f"**Applicazioni:** {links}",
            f"**Visualizzazioni collegate:** {ids}", ""])
    if report["warnings"]:
        lines.extend(["## Riferimenti non centralizzati (da valutare)",""])
        lines.extend(f"- {w}" for w in report["warnings"])
        lines.append("")
    lines.extend(["## Come si usa","",
        "Modifica **[catalog/measures.json](measures.json)**, **[catalog/dimensions.json](dimensions.json)** "
        "oppure **[catalog/variables.json](variables.json)**; associa gli ID alle app nei rispettivi manifest. "
        "Il report è aggiornato dal workflow GitHub Actions senza usare il computer dell'autore.",
        "",
        "Per i dettagli strutturati e per altri strumenti, usa **[usage.json](usage.json)**.",
        ""])
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description="QlikGPT declarative semantic usage report")
    parser.add_argument("--check",action="store_true")
    parser.add_argument("--impact",help="kind:id, e.g. measure:qlikgpt_shared_revenue")
    args=parser.parse_args()
    report=generate()
    if args.impact:
        kind,ident=args.impact.split(":",1)
        item=next((x for x in report["items"] if x["kind"]==kind and x["id"]==ident),None)
        if item is None:raise ValueError("Unknown catalog item")
        print(json.dumps({"type":kind,"id":ident,"apps":item["apps"],
                          "visuals":item["visuals"]},indent=2,ensure_ascii=False))
    elif args.check:
        if not OUTPUT.exists() or render(report)!=OUTPUT.read_text(encoding="utf-8"):
            raise SystemExit("USAGE.md is stale. Run python3 ci/catalog_report.py")
        if not OUTPUT_JSON.exists() or report != load(OUTPUT_JSON):
            raise SystemExit("usage.json is stale. Run python3 ci/catalog_report.py")
        print("Semantic Catalog usage report up to date.")
    else:
        OUTPUT.write_text(render(report),encoding="utf-8")
        OUTPUT_JSON.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(f"Semantic Catalog 2.0: {len(report['items'])} objects, {len(report['apps'])} apps, "
              f"{len(report['warnings'])} non-governed visual dimension references.")


if __name__=="__main__":
    main()
