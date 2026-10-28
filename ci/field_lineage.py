#!/usr/bin/env python3
"""QlikGPT evidence-based static field lineage: QVS -> QVD -> catalog -> visual.

Recognizes the explicitly supported LOAD/FROM, RESIDENT, AUTOGENERATE, STORE
QVS subset. Unknown field references produce warnings, not guessed edges.
No Qlik API or reload is required. Source paths and line numbers are retained.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, deque
import json
from pathlib import Path
import re
from app_lineage import build as app_build, registry, without_comments
from model_registry import active_model, ROOT

MODEL = active_model()
OUT = MODEL.root / "lineage" / "END_TO_END.md"
OUT_JSON = MODEL.root / "lineage" / "end_to_end.json"
BT = chr(96)
LOAD = re.compile(
    r"(?ims)^[ \t]*(?:(?P<table>[A-Za-z_]\w*)[ \t]*:[ \t]*\n[ \t]*)?"
    r"(?:NoConcatenate\s+)?LOAD\s+(?:DISTINCT\s+)?(?P<columns>.*?)\s+"
    r"(?P<kind>FROM|RESIDENT|AUTOGENERATE)\s+"
    r"(?P<input>\[[^\]\r\n]+\]\s*\(\s*qvd\s*\)|[A-Za-z_]\w*|\d+)"
    r"\s*(?:WHERE\s+(?P<where>.*?))?\s*;"
)
ALIAS = re.compile(r"(?is)^(.*?)\s+AS\s+(\[[^\]]+\]|[A-Za-z_]\w*)$")
LITERALS = re.compile(r"'(?:''|[^'])*'|\"(?:\"\"|[^\"])*\"")
TOKENS = re.compile(r"\b[A-Za-z_]\w*\b")
KEYWORDS = {"DISTINCT","AND","OR","NOT","NULL","TRUE","FALSE","AS","IS","IN","LIKE"}

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def path_of(path):
    return path.relative_to(ROOT).as_posix()

def reference(path, line):
    return {"path":path, "line":line}

def line_of(text, needle):
    pos = text.find(needle)
    return text.count("\n",0,pos)+1 if pos>=0 else 1

def split_columns(text):
    parts=[]; begin=0; depth=0; quote=None; i=0
    while i < len(text):
        c=text[i]
        if quote:
            if c==quote:
                if i+1<len(text) and text[i+1]==quote:
                    i+=2;continue
                quote=None
        elif c in "'\"":
            quote=c
        elif c=="(":
            depth+=1
        elif c==")":
            depth-=1
            if depth<0:raise ValueError("Invalid QVS function nesting")
        elif c=="," and depth==0:
            part=text[begin:i]
            if part.strip():parts.append((part.strip(),begin+len(part)-len(part.lstrip())))
            begin=i+1
        i+=1
    if depth or quote:raise ValueError("Unbalanced QVS function/quote")
    part=text[begin:]
    if part.strip():parts.append((part.strip(),begin+len(part)-len(part.lstrip())))
    return parts

def parse_loads(text,path):
    plain=without_comments(text)
    blocks=[];warnings=[]
    for m in LOAD.finditer(plain):
        if not m.group("table"):
            warnings.append(f"{path}#L{line_of(plain,m.group(0)[:15])}: unnamed LOAD (skipped)")
            continue
        columns=[]
        for raw,offset in split_columns(m.group("columns")):
            alias=ALIAS.match(raw)
            expr=alias.group(1).strip() if alias else raw.strip()
            name=alias.group(2).strip("[]") if alias else expr.strip("[]")
            line=plain.count("\n",0,m.start("columns")+offset)+1
            if expr!="*" and not re.fullmatch(r"[A-Za-z_]\w*|\[[^\]]+\]",name):
                warnings.append(f"{path}#L{line}: unaliased expression unsupported")
                continue
            columns.append({"field":name,"expression":expr,"line":line})
        kind=m.group("kind").upper()
        source=m.group("input")
        if kind=="FROM":source=source.split("]")[0][1:]
        blocks.append({"table":m.group("table"),"kind":kind,"source":source,
                       "columns":columns,"where":(m.group("where") or "").strip(),
                       "line":plain.count("\n",0,m.start())+1})
    n=len(re.findall(r"(?im)^\s*LOAD\s+",plain))
    if len(blocks)!=n:
        warnings.append(f"{path}: recognized {len(blocks)}/{n} LOAD statements; cannot infer unparsed loads")
    if re.search(r"\$\(|\b(SQL|JOIN|KEEP|MAPPING|APPLYMAP|INCLUDE)\b",plain,re.I):
        warnings.append(f"{path}: advanced/dynamic script requires dedicated parser")
    return blocks,warnings

def fields_used(expression,available):
    """Identify field references using a known schema; unresolved tokens are NOT linked."""
    if "$(" in expression:
        return set(),{"dynamic"}
    text=LITERALS.sub(lambda m:" "*len(m.group()),expression)
    brackets=re.findall(r"\[([^\]]+)\]",text)
    text=re.sub(r"\[[^\]]+\]", " ",text)
    funcs={m.group(1).upper() for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(",text)}
    used=set();unknown=set()
    for token in brackets+TOKENS.findall(text):
        if token in available:used.add(token)
        elif token.upper() in funcs or token.upper() in KEYWORDS:continue
        else:unknown.add(token)
    return used,unknown

class Graph:
    def __init__(self):
        self.nodes={};self.edges={};self.warnings=[]
    def node(self,ident,typ,label,**kwargs):
        obj={"id":ident,"type":typ,"label":label,**kwargs}
        if ident in self.nodes and self.nodes[ident]!=obj:
            raise ValueError(f"Duplicate/conflicting node {ident}")
        self.nodes[ident]=obj
        return ident
    def edge(self,a,b,typ,source):
        if a not in self.nodes or b not in self.nodes:
            raise ValueError(f"Unresolved edge {a} -> {b}")
        self.edges[(a,b,typ)]={"from":a,"to":b,"kind":typ,"source":source}
    def result(self,apps):
        return {"schemaVersion":1,"modelId":MODEL.id,
                "scope":"static versioned QVS/catalog/JSON; no runtime scan",
                "apps":apps,
                "nodes":sorted(self.nodes.values(),key=lambda x:x["id"]),
                "edges":sorted(self.edges.values(),key=lambda x:(x["from"],x["to"],x["kind"])),
                "warnings":sorted(set(self.warnings))}

def node_field(app,table,name):
    return f"table:{app}:{table}.{name}"

def node_qvd(uri,name):
    return f"qvd:{uri}#{name}"

def node_logical(app,name):
    return f"logical:{app}:{name}"

def build():
    apps=registry()
    appgraph=app_build(apps)
    g=Graph()
    g.warnings.extend(appgraph["warnings"])
    tables=defaultdict(dict)
    qvds=defaultdict(dict)
    scripts={}
    parsed={}
    for app,meta in apps.items():
        script=(ROOT/meta["script"]).read_text(encoding="utf-8")
        scripts[app]=script
        blocks,warnings=parse_loads(script,meta["script"])
        parsed[app]=blocks;g.warnings.extend(warnings)
    pending=set(apps)
    order=[]
    while pending:
        ready=sorted(app for app in pending if not any(
            c["downstream"]==app and c["upstream"] in pending
            for c in appgraph["connections"]))
        if not ready:raise ValueError("App dependency cycle")
        order+=ready
        pending-=set(ready)
    for app in order:
        script_path=apps[app]["script"]
        for block in parsed[app]:
            table,kind,source=block["table"],block["kind"],block["source"]
            inputs=(qvds.get(source,{}) if kind=="FROM" else
                    tables.get((app,source),{}) if kind=="RESIDENT" else {})
            if kind!="AUTOGENERATE" and not inputs:
                g.warnings.append(f"{app}.{table}: no proven schema for {kind} {source}")
            cols=block["columns"]
            if any(c["expression"]=="*" for c in cols):
                if len(cols)!=1:g.warnings.append(f"{app}.{table}: mixed LOAD * unsupported")
                cols=[{"field":name,"expression":name,"line":cols[0]["line"]}
                      for name in sorted(inputs)] if inputs else []
                if not cols:g.warnings.append(f"{app}.{table}: unresolved LOAD * expansion")
            filter_fields=set()
            if block["where"]:
                filter_fields,unknown=fields_used(block["where"],set(inputs))
                if unknown:g.warnings.append(f"{app}.{table}: unresolved WHERE {sorted(unknown)}")
            for c in cols:
                name,expr=c["field"],c["expression"]
                ident=node_field(app,table,name)
                src=reference(script_path,c["line"])
                g.node(ident,"table_field",f"{app}.{table}.{name}",app=app,table=table,
                       field=name,expression=expr,origin="synthetic" if kind=="AUTOGENERATE" else "derived",
                       source=src)
                if name in tables[(app,table)]:
                    raise ValueError(f"Duplicate LOAD output field {ident}")
                tables[(app,table)][name]=ident
                used,unknown=fields_used(expr,set(inputs))
                if unknown and kind!="AUTOGENERATE":
                    g.warnings.append(f"{script_path}#L{c['line']}: unresolved {sorted(unknown)} for {ident}")
                if kind=="AUTOGENERATE":continue
                for field in sorted(used):g.edge(inputs[field],ident,"value",src)
                for field in sorted(filter_fields):
                    g.edge(inputs[field],ident,"row_filter",
                           reference(script_path,block["line"]))
        for store in appgraph["apps"][app]["writes"]:
            uri=store["uri"];table=store["table"]
            for name,field_id in sorted(tables.get((app,table),{}).items()):
                ident=node_qvd(uri,name)
                src=reference(script_path,store["line"])
                g.node(ident,"qvd_field",f"{Path(uri).name}.{name}",
                       uri=uri,field=name,source=src)
                qvds[uri][name]=ident
                g.edge(field_id,ident,"store_qvd",src)
            if not tables.get((app,table)):
                g.warnings.append(f"{app}: STORE of unparsed table {table}")
        if apps[app]["type"]=="presentation":
            for (app_key,table),items in sorted(tables.items()):
                if app_key!=app:continue
                for field,ident in sorted(items.items()):
                    logical=node_logical(app,field)
                    g.node(logical,"logical_field",f"{app}.{field}",app=app,field=field)
                    g.edge(ident,logical,"field_binding",g.nodes[ident]["source"])
    catalogs={}
    for typ,key in (("measure","measures"),("dimension","dimensions"),("variable","variables")):
        filepath=MODEL.catalog(key)
        txt=filepath.read_text(encoding="utf-8")
        catalog={c["id"]:c for c in load_json(filepath)[key]}
        catalogs[typ]=catalog
        for ident,item in catalog.items():
            node=f"{typ}:{ident}"
            src=reference(path_of(filepath),line_of(txt,'"id": "'+ident+'"'))
            g.node(node,typ,item.get("title",item.get("name",ident)),
                   catalogId=ident,expression=item.get("expression",item.get("definition")),
                   source=src)
            if typ=="variable":continue
            raw=item["expression"] if typ=="measure" else ",".join(item["fields"])
            for app,meta in apps.items():
                if meta["type"]!="presentation":continue
                logicals={n["field"]:n["id"] for n in g.nodes.values()
                          if n["type"]=="logical_field" and n["app"]==app}
                used,unknown=fields_used(raw,set(logicals))
                if unknown:g.warnings.append(f"{ident}: unresolved fields in {app}: {sorted(unknown)}")
                if typ=="measure" and set(item.get("requiredFields",[]))!=used:
                    g.warnings.append(f"{ident}: requiredFields differ from parsed expression for {app}")
                for field in sorted(used):
                    g.edge(logicals[field],node,"semantic_dependency",src)
    for app,path in MODEL.presentation_manifests().items():
        manifest=load_json(path)
        mtxt=path.read_text(encoding="utf-8")
        g.node(f"app:{app}","application",manifest["appName"],app=app,
               appId=apps[app]["appId"],source=reference(path_of(path),1))
        for typ,key in (("measure","catalogMeasures"),("dimension","catalogDimensions"),
                        ("variable","catalogVariables")):
            for ident in manifest.get(key,[]):
                if ident not in catalogs[typ]:raise ValueError(f"Unknown subscription {typ}:{ident}")
                sub=f"subscription:{app}:{typ}:{ident}"
                src=reference(path_of(path),line_of(mtxt,'"'+ident+'"'))
                g.node(sub,"subscription",f"{app} / {ident}",app=app,
                       catalogType=typ,catalogId=ident,source=src)
                g.edge(f"{typ}:{ident}",sub,"subscribed_by",src)
        objfile=ROOT/manifest["dashboardSource"]
        otxt=objfile.read_text(encoding="utf-8")
        def walk(obj,sheet_id=None):
            info=obj.get("qInfo",{});oid=info.get("qId")
            if not oid:return
            if info.get("qType")=="sheet":sheet_id=oid
            src=reference(path_of(objfile),line_of(otxt,'"qId": "'+oid+'"'))
            node=f"object:{app}:{oid}"
            typ="sheet" if oid==sheet_id else "visual"
            g.node(node,typ,obj.get("title",oid),app=app,objectId=oid,
                   sheetId=sheet_id,chartType=info.get("qType"),source=src)
            cube=obj.get("qHyperCubeDef",{})
            for typ,key in (("measure","qMeasures"),("dimension","qDimensions")):
                for entry in cube.get(key,[]):
                    ident=entry.get("qLibraryId")
                    sub=f"subscription:{app}:{typ}:{ident}"
                    if sub not in g.nodes:
                        g.warnings.append(f"{app}/{oid}: unresolved/inline {typ} {ident}")
                    else:
                        g.edge(sub,node,"visual_use",
                               reference(path_of(objfile),line_of(otxt,'"qLibraryId": "'+ident+'"')))
            # Inline sorting is an additional data influence, not a catalog measure.
            def sort_expressions(value):
                if isinstance(value,dict):
                    e=value.get("qExpression",{})
                    if isinstance(e,dict) and isinstance(e.get("qv"),str):yield e["qv"]
                    for child in value.values():yield from sort_expressions(child)
                elif isinstance(value,list):
                    for child in value:yield from sort_expressions(child)
            logicals={n["field"]:n["id"] for n in g.nodes.values()
                      if n["type"]=="logical_field" and n["app"]==app}
            for expr in sorted(set(sort_expressions(cube.get("qDimensions",[])))):
                used,unknown=fields_used(expr,set(logicals))
                if unknown:g.warnings.append(f"{app}/{oid}: unresolved sort expression {expr}")
                for field in used:
                    g.edge(logicals[field],node,"inline_sort",
                           reference(path_of(objfile),line_of(otxt,'"qv": "'+expr+'"')))
            for child in obj.get("qChildren",[]):walk(child,sheet_id)
        for sheet in load_json(objfile):walk(sheet)
        if manifest.get("filterSource"):
            filepath=ROOT/manifest["filterSource"]
            ftxt=filepath.read_text(encoding="utf-8")
            for f in load_json(filepath):
                oid=f["id"];sub=f"subscription:{app}:dimension:{f['dimensionId']}"
                node=f"object:{app}:{oid}"
                g.node(node,"filter",f["label"],app=app,objectId=oid,
                       chartType="filter",source=reference(path_of(filepath),
                                                           line_of(ftxt,'"id": "'+oid+'"')))
                if sub not in g.nodes:g.warnings.append(f"{app}/{oid}: unresolved filter dimension")
                else:g.edge(sub,node,"filter_use",
                            reference(path_of(filepath),
                                      line_of(ftxt,'"dimensionId": "'+f['dimensionId']+'"')))
    return g.result({key:{"name":a["name"],"appId":a["appId"],"script":a["script"]}
                     for key,a in sorted(apps.items())})

def reachable(report,seeds,backward=False,exclude_row_filters=False):
    adj=defaultdict(set)
    for e in report["edges"]:
        if exclude_row_filters and e["kind"]=="row_filter":continue
        a,b=(e["to"],e["from"]) if backward else (e["from"],e["to"])
        adj[a].add(b)
    seen=set(seeds);pending=deque(sorted(seeds))
    while pending:
        for nxt in sorted(adj[pending.popleft()]):
            if nxt not in seen:seen.add(nxt);pending.append(nxt)
    return seen

def locate(report,selector):
    if ":" not in selector:raise ValueError("Expected kind:identifier selector")
    kind,value=selector.split(":",1)
    if kind in ("measure","dimension","variable","qvd","object"):
        matches={n["id"] for n in report["nodes"] if n["id"]==selector}
    elif kind=="field":
        matches={n["id"] for n in report["nodes"] if n["type"]=="logical_field" and n["field"]==value}
    elif kind=="source":
        matches={n["id"] for n in report["nodes"] if n["type"]=="table_field" and
                 n["app"]+"."+n["table"]+"."+n["field"]==value}
    else:raise ValueError(f"Unsupported selector type {kind}")
    if not matches:raise ValueError(f"No proven lineage for {selector}")
    return matches

def impact(report,selector):
    seeds=locate(report,selector)
    upstream=reachable(report,seeds,backward=True)
    downstream=reachable(report,seeds)
    byid={n["id"]:n for n in report["nodes"]}
    def choose(ids,types):
        return sorted([{"id":n["id"],"label":n["label"],
                        **({"app":n["app"]} if "app" in n else {})}
                       for ident in ids if (n:=byid[ident])["type"] in types],
                      key=lambda n:n["id"])
    inc={e["to"] for e in report["edges"]}
    return {"selector":selector,"matched":sorted(seeds),
            "upstreamOrigins":choose({x for x in upstream if x not in inc},
                                     {"table_field","qvd_field"}),
            "upstreamFields":choose(upstream,{"table_field","qvd_field","logical_field"}),
            "impactedMeasures":choose(downstream,{"measure"}),
            "impactedDimensions":choose(downstream,{"dimension"}),
            "impactedApps":sorted({byid[x]["app"] for x in downstream
                                  if byid[x]["type"]=="subscription"}),
            "impactedObjects":choose(downstream,{"visual","filter"}),
            "warnings":report["warnings"]}

def file_link(src):
    return f"[{src['path']}#L{src['line']}](../../../{src['path']}#L{src['line']})"

def render(report):
    byid={n["id"]:n for n in report["nodes"]}
    counts={typ:len([x for x in report["nodes"] if x["type"]==typ])
            for typ in ("table_field","qvd_field","measure","dimension","visual","filter")}
    lines=[
        "# Sales — End-to-End Field Lineage", "",
        "**Lineage statico con evidenze file/riga:** QVS → QVD → campi associativi → "
        "Semantic Catalog → manifest applicativi → grafici e filtri.", "",
        f"**Copertura:** {len(report['apps'])} app, {counts['table_field']} campi tabella, "
        f"{counts['qvd_field']} campi QVD, {counts['measure']} misure, "
        f"{counts['dimension']} dimensioni, {counts['visual']} visualizzazioni, "
        f"{counts['filter']} filtri.", "",
        "[Grafo JSON dettagliato](end_to_end.json) · [App Lineage](APP_LINEAGE.md) · "
        "[Semantic Usage](../catalog/USAGE.md)", "",
        "## Misure: origini e utilizzo", "",
        "| Misura | Campi Presentation | Origini upstream | App e KPI/grafici | Definizione |",
        "| --- | --- | --- | --- | --- |",
    ]
    for node in [n for n in report["nodes"] if n["type"]=="measure"]:
        ident=node["id"]
        upstream=reachable(report,{ident},backward=True,exclude_row_filters=True)
        origins={x for x in upstream if byid[x]["type"]=="table_field" and
                 byid[x].get("origin")=="synthetic"}
        logicals=sorted({byid[x]["field"] for x in upstream if byid[x]["type"]=="logical_field"})
        downstream=reachable(report,{ident})
        targets=sorted({byid[x]["app"]+"/"+byid[x]["objectId"] for x in downstream
                        if byid[x]["type"]=="visual"})
        lines.append("| "+BT+node["catalogId"]+BT+" | "+", ".join(logicals)+" | "+
                     (", ".join(BT+byid[x]["label"]+BT for x in sorted(origins)) or "Da verificare")+
                     " | "+(", ".join(BT+x+BT for x in targets) or "**Non utilizzata**")+
                     " | "+file_link(node["source"])+" |")
    lines += ["", "## Passaggi intermedi verificati per ciascuna misura", "",
              "Ogni arco qui sotto è un collegamento documentato: campo sorgente, "
              "trasformazione ETL, QVD, campo del modello associativo, "
              "definizione semantica, sottoscrizione e oggetto Qlik.",
              "Le relazioni **row_filter** sono escluse da questi percorsi di valore "
              "e riportate nella sezione successiva.", ""]
    for measure in (n for n in report["nodes"] if n["type"] == "measure"):
        mid = measure["id"]
        upstream = reachable(report, {mid}, backward=True, exclude_row_filters=True)
        downstream = reachable(report, {mid})
        chain = upstream | downstream
        edges = [e for e in report["edges"] if e["kind"] not in ("row_filter", "inline_sort")
                 and e["from"] in chain and e["to"] in chain]
        lines += ["### " + measure["label"] + " (" + BT + measure["catalogId"] + BT + ")",
                  "", "| Da | A | Relazione | Evidenza nel repository |",
                  "| --- | --- | --- | --- |"]
        for e in edges:
            left, right = byid[e["from"]], byid[e["to"]]
            # For a QVD field, the actual storage location is the lib:// URI
            # declared in STORE/FROM, not a repository file.
            def display(node):
                label = node["label"]
                if node["type"] == "qvd_field":
                    label = node["uri"] + "#" + node["field"]
                elif node["type"] == "subscription":
                    label = node["app"] + ": " + node["catalogId"]
                return BT + label.replace("|", "\\|") + BT
            lines.append("| " + display(left) + " | " + display(right) + " | " +
                         BT + e["kind"] + BT + " | " + file_link(e["source"]) + " |")
        lines.append("")
    lines += ["## Dipendenze che filtrano le righe", "",
              "Un campo utilizzato da un WHERE può cambiare i risultati dei KPI "
              "anche senza entrare nell'espressione di calcolo. Gli archi di questo "
              "tipo vengono mantenuti separati nel JSON e nella impact analysis.",
              "", "| Input | Output filtrato | Dove |",
              "| --- | --- | --- |"]
    for e in report["edges"]:
        if e["kind"] != "row_filter":
            continue
        lines.append("| " + BT + byid[e["from"]]["label"] + BT + " | " +
                     BT + byid[e["to"]]["label"] + BT + " | " +
                     file_link(e["source"]) + " |")
    lines.append("")
    lines+=["","## Dimensioni e filtri","","| Dimensione | Campo | Visualizzazioni/filtri | Definizione |",
            "| --- | --- | --- | --- |"]
    for node in [n for n in report["nodes"] if n["type"]=="dimension"]:
        upstream=reachable(report,{node["id"]},backward=True,exclude_row_filters=True)
        fields=sorted({byid[x]["field"] for x in upstream if byid[x]["type"]=="logical_field"})
        downstream=reachable(report,{node["id"]})
        targets=sorted({byid[x]["app"]+"/"+byid[x]["objectId"] for x in downstream
                        if byid[x]["type"] in ("visual","filter")})
        lines.append("| "+BT+node["catalogId"]+BT+" | "+", ".join(fields)+" | "+
                     (", ".join(BT+x+BT for x in targets) or "Non utilizzata")+
                     " | "+file_link(node["source"])+" |")
    lines+=["","## Variabili","",
            "Le variabili del catalogo sono versionate e possono essere sottoscritte; "
            "non risultano referenziate da espressioni dei visual attuali. Non si inventano utilizzi.", "",
            "| Variabile | App sottoscritte |",
            "| --- | --- |"]
    for node in [n for n in report["nodes"] if n["type"]=="variable"]:
        apps=sorted(n["app"] for n in report["nodes"] if n["type"]=="subscription"
                    and n["catalogId"]==node["catalogId"] and n["catalogType"]=="variable")
        lines.append("| "+BT+node["catalogId"]+BT+" | "+(", ".join(apps) or "Nessuna")+" |")
    lines+=["","## Esempi di impact analysis","",
            "- "+BT+"python3 ci/field_lineage.py --impact source:etl1.RawOrders.Quantity"+BT+
            " — include la propagazione dei WHERE che filtrano le righe.",
            "- "+BT+"python3 ci/field_lineage.py --impact field:Revenue"+BT+
            " — misure, KPI, grafici e ordinamenti.",
            "- "+BT+"python3 ci/field_lineage.py --impact measure:qlikgpt_shared_margin_pct"+BT+
            " — app e oggetti a valle, fonti a monte.",
            "- "+BT+"python3 ci/field_lineage.py --check"+BT+" — controlla i report generati.", "",
            "## Tipi di arco e limiti","",
            "- **value**: dipendenza di calcolo; **row_filter**: influisce sul numero delle righe "
            "(WHERE), non necessariamente sul valore; **inline_sort**: influenza l'ordinamento.",
            "- **store_qvd / field_binding**: percorso QVD e campo logico Qlik.",
            "- **semantic_dependency / subscribed_by / visual_use / filter_use**: "
            "catalogo, sottoscrizione e oggetto versionato.",
            "- Dati ETL1 sintetici generati da AUTOGENERATE/Rand(), non sorgenti aziendali reali.",
            "- Non rappresenta il Qlik runtime, dati aggiornati, oggetti manuali, SQL, "
            "join, mapping, campi dinamici o spazi Qlik non condivisi.",
            "- Qualunque collegamento non dimostrato dai file viene omesso e segnalato.", "",
            "## Avvisi del parser",""]
    lines+=["- "+w.replace("|","\\|") for w in report["warnings"]] or ["Nessuna anomalia rilevata nel subset supportato."]
    return "\n".join(lines)+"\n"

def main():
    p=argparse.ArgumentParser(description="QlikGPT governed end-to-end field lineage")
    p.add_argument("--check",action="store_true")
    p.add_argument("--impact",help="field:Revenue, measure:..., source:etl1.RawOrders.Quantity")
    args=p.parse_args()
    report=build()
    if args.impact:
        print(json.dumps(impact(report,args.impact),ensure_ascii=False,indent=2))
    elif args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8")!=render(report):
            raise SystemExit("END_TO_END.md out of date")
        if not OUT_JSON.exists() or load_json(OUT_JSON)!=report:
            raise SystemExit("end_to_end.json out of date")
        print("End-to-end lineage reports current")
    else:
        OUT.parent.mkdir(parents=True,exist_ok=True)
        OUT.write_text(render(report),encoding="utf-8")
        OUT_JSON.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
        print(f"End-to-end lineage: {len(report['nodes'])} nodes, "
              f"{len(report['edges'])} edges, {len(report['warnings'])} warnings; zero reloads")

if __name__=="__main__":
    main()
