#!/usr/bin/env python3
"""QlikGPT Executive V1: reusable native Qlik presentation scaffold and QA.

The registry, catalog subscriptions, and UI tokens remain the source of truth.
--check validates versioned dashboard JSON; --new-* previews or explicitly
writes a new Presentation manifest + sheet. No Qlik API and no reload here.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re

from model_registry import ROOT, active_model

MODEL = active_model()
TOKENS = ROOT / "ui" / "design-tokens.json"
THEME = ROOT / "ui" / "themes" / "qlikgpt-executive-v1" / "theme.json"
QEXT = ROOT / "ui" / "themes" / "qlikgpt-executive-v1" / "qlikgpt-executive-v1.qext"

def read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def tokens():
    t = read(TOKENS)
    if t.get("schemaVersion") != 1 or t.get("templateId") != "qlikgpt-executive-v1":
        raise ValueError("Unknown UI design-token contract")
    for key, value in t["colors"].items():
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", value):
            raise ValueError(f"Invalid color token: {key}")
    if t["grid"]["columns"] != 24:
        raise ValueError("Native Qlik template expects 24 grid columns")
    theme = read(THEME)
    ext = read(QEXT)
    if ext.get("type") != "theme" or ext.get("name") != t["templateId"]:
        raise ValueError("QEXT metadata must match tokens")
    if theme["_variables"]["@qlikgpt-navy"] != t["colors"]["navy"]:
        raise ValueError("Theme and UI palette diverged")
    if theme["_variables"]["@qlikgpt-teal"] != t["colors"]["teal"]:
        raise ValueError("Theme chart palette and UI tokens diverged")
    if theme["_variables"]["@qlikgpt-blue"] != t["colors"]["blue"]:
        raise ValueError("Versioned optional theme color diverged from palette")
    return t

def color(value):
    return {"index": -1, "color": value}

def background(value):
    return {"background": {"useColorExpression": False, "color": color(value)}}

def native_card_style(background_color: str, *, decorated: bool = True) -> dict:
    """Versioned Qlik native object styling; no uploaded application theme."""
    t = tokens()["colors"]
    return {
        "background": {"useColorExpression": False, "color": color(background_color)},
        "border": {
            "width": 1 if decorated else 0,
            "radius": 12,
            "color": color(t["border"]),
        },
        "shadow": {
            "size": "small" if decorated else "none",
            "color": color("#A7B7D1"),
        },
    }


def text_block(ident, markdown, *, dark=False):
    t = tokens()
    return {
        "qInfo": {"qId": ident, "qType": "text-image"},
        "qExtendsId": "", "visualization": "text-image",
        "title": ident, "showTitles": False,
        "markdown": markdown, "images": [], "responsive": True,
        "background": {"color": t["colors"]["paleBlue"] if dark else t["colors"]["canvas"]},
        "style": native_card_style(t["colors"]["paleBlue"] if dark else t["colors"]["canvas"],decorated=False)
    }

def navigation_button(ident, label, destination, *, target_title=None):
    """Native Qlik action-button: documented navigation.openWebsite contract."""
    t=tokens()
    if not destination.startswith("https://") or "/sense/app/" not in destination:
        raise ValueError("Navigation must target an HTTPS Qlik Sense application")
    return {
        "qInfo": {"qId": ident, "qType": "button"}, "qExtendsId": "",
        "visualization": "button", "title": target_title or label,
        "showTitles": False, "showDetails": False,
        "actions": [],
        "navigation": {"action": "openWebsite", "websiteUrl": destination,
                       "sameWindow": False},
        "style": {
            **native_card_style(t["colors"]["navy"], decorated=False),
            "label": label, "showLabel": True,
            "font": {"fontFamily": t["fontFamily"],
                     "color": {"useColorExpression": False,
                               "color": color(t["colors"]["inverse"])}},
            "background": {"useColorExpression": False,
                           "color": color(t["colors"]["navy"])}
        }
    }

def kpi(ident, label, measure):
    t=tokens()
    return {
        "qInfo": {"qId": ident, "qType": "kpi"}, "qExtendsId": "",
        "visualization": "kpi", "title": label, "showTitles": True,
        "showDetails": False, "textAlign": "left", "fontSize": "M",
        "showMeasureTitle": False, "layoutBehavior": "Responsive",
        "qHyperCubeDef": {
            "qDimensions": [],
            "qMeasures": [{"qLibraryId": measure, "qType": "measure",
                           "qDef": {"qDef": "", "qLabel": label}}],
            "qInitialDataFetch": [{"qLeft": 0, "qTop": 0,
                                    "qWidth": 1, "qHeight": 1}]
        },
        "style": native_card_style(t["colors"]["card"])
    }

def cell(ident, typ, col, row, colspan, rowspan, rows):
    if col < 0 or row < 0 or colspan <= 0 or rowspan <= 0:
        raise ValueError("Invalid Qlik grid position")
    if col + colspan > 24 or row + rowspan > rows:
        raise ValueError("Qlik cell outside sheet grid")
    return {
        "name": ident, "type": typ, "col": col, "row": row,
        "colspan": colspan, "rowspan": rowspan,
        "bounds": {
            "x": col * 100 / 24, "y": row * 100 / rows,
            "width": colspan * 100 / 24, "height": rowspan * 100 / rows
        }
    }

def sheet(key, title, measures, destination):
    """Reusable 24-column executive starting sheet, not a fake chart."""
    if not re.fullmatch(r"presentation[0-9]+", key):
        raise ValueError("New app key must look like presentation3")
    if not 1 <= len(measures) <= 4:
        raise ValueError("The executive KPI row supports 1..4 measures")
    t=tokens()
    prefix="qlikgpt_"+key
    sheet_id=prefix+"_overview"
    rows=22
    header=text_block(
        prefix+"_header",
        "%[QlikGPT  /  "+title+"](6)^[EXECUTIVE OVERVIEW  •  GOVERNED ANALYTICS](2)",
        dark=True,
    )
    nav=navigation_button(prefix+"_nav", "APRI OVERVIEW  →", destination)
    intro=text_block(
        prefix+"_intro",
        "%[Executive Overview](5)^[Un unico spazio per esplorare le performance di business.](2)",
    )
    section=text_block(
        prefix+"_section",
        "%[01 / BUSINESS PULSE](3)^[Indicatori governati dal modello semantico](2)",
    )
    insights=text_block(
        prefix+"_insights",
        "%[02 / PERFORMANCE EXPLORER](3)^[Aggiungere grafici Qlik nativi dopo aver associato le dimensioni del catalogo](2)",
    )
    details=text_block(
        prefix+"_detail",
        "Visualizzazioni Qlik native: associa misure e dimensioni con qLibraryId, senza formule inline.",
    )
    children=[header,nav,intro,section]
    cells=[
        cell(header["qInfo"]["qId"],"text-image",0,0,18,3,rows),
        cell(nav["qInfo"]["qId"],"button",18,0,6,3,rows),
        cell(intro["qInfo"]["qId"],"text-image",0,3,24,3,rows),
        cell(section["qInfo"]["qId"],"text-image",0,6,24,1,rows),
    ]
    width=24//len(measures)
    for i,(mid,label) in enumerate(measures):
        ident=prefix+"_kpi_"+str(i+1)
        children.append(kpi(ident,label,mid))
        span=24-(i*width) if i==len(measures)-1 else width
        cells.append(cell(ident,"kpi",i*width,7,span,4,rows))
    children.extend([insights,details])
    cells.append(cell(insights["qInfo"]["qId"],"text-image",0,11,24,1,rows))
    cells.append(cell(details["qInfo"]["qId"],"text-image",0,12,24,10,rows))
    return [{
        "qInfo":{"qId":sheet_id,"qType":"sheet"}, "qExtendsId":"",
        "qMetaDef":{"title":title,"description":"QlikGPT Executive V1 template"},
        "title":title,"description":"Governed native Qlik analytics",
        "rank":0,"columns":24,"rows":rows,"gridMode":"edit",
        "background": {"color":t["colors"]["canvas"]},
        "backgroundColor":color(t["colors"]["canvas"]),
        "style":native_card_style(t["colors"]["canvas"],decorated=False),
        "cells":cells,
        "qChildListDef":{"qData":{"title":"/title","description":"/description",
                                   "type":"/qInfo/qType","id":"/qInfo/qId"}},
        "qChildren":children
    }]

def new_files(key,app_name,measure_ids):
    t=tokens()
    if key in MODEL.data["presentations"] or (MODEL.root/"apps"/(key+".json")).exists():
        raise ValueError("Application manifest already exists")
    if not re.fullmatch(r"presentation[3-9][0-9]*",key):
        raise ValueError("New Presentation keys start from presentation3")
    if not app_name.strip():
        raise ValueError("Missing application name")
    catalog=read(MODEL.catalog("measures"))
    byid={m["id"]:m for m in catalog["measures"]}
    if len(measure_ids)!=len(set(measure_ids)) or not measure_ids:
        raise ValueError("Select unique measure IDs")
    if not set(measure_ids)<=set(byid):
        raise ValueError("Some measure IDs do not belong to the model catalog")
    known=read(MODEL.state_path)
    reference=known.get("presentation")
    if not reference:
        raise ValueError("A Qlik navigation target must be provisioned")
    url=known["tenant"].rstrip("/")+"/sense/app/"+reference
    mpath=MODEL.prefix+"/apps/"+key+".json"
    opath=MODEL.prefix+"/apps/"+key+"-objects.json"
    manifest={
        "appKey":key,"appName":app_name,"loadScript":MODEL.presentation_script,
        "uiTemplate":t["templateId"],"catalogMeasures":measure_ids,
        "catalogDimensions":[],"catalogVariables":[],
        "dashboardSource":opath,
        "description":"Generated QlikGPT Executive V1 scaffold. Add subscribed dimensions and visuals as needed."
    }
    objects=sheet(key,app_name,[(mid,byid[mid]["title"]) for mid in measure_ids],url)
    return {mpath:manifest,opath:objects}

def validate_dashboard(dashboard,t,filename):
    if not isinstance(dashboard,list) or not dashboard:
        raise ValueError(f"{filename}: sheets missing")
    for sh in dashboard:
        if sh.get("columns")!=24:
            raise ValueError(f"{filename}: expected 24-column grid")
        children={obj["qInfo"]["qId"]:obj for obj in sh.get("qChildren",[])}
        if len(children)!=len(sh.get("qChildren",[])):
            raise ValueError(f"{filename}: duplicate native child IDs")
        occupied=set()
        for c in sh.get("cells",[]):
            if c["name"] not in children:
                raise ValueError(f"{filename}: cell lacks a matching QIX child")
            if c["col"]<0 or c["row"]<0 or c["col"]+c["colspan"]>24 or c["row"]+c["rowspan"]>sh["rows"]:
                raise ValueError(f"{filename}: invalid native grid cell")
            for x in range(c["col"],c["col"]+c["colspan"]):
                for y in range(c["row"],c["row"]+c["rowspan"]):
                    if (x,y) in occupied:
                        raise ValueError(f"{filename}: overlapping Qlik grid cells")
                    occupied.add((x,y))
        if {c["name"] for c in sh.get("cells",[])}!=set(children):
            raise ValueError(f"{filename}: child without layout cell")
        brands=[obj for obj in children.values()
                if obj["qInfo"]["qType"]=="text-image" and "QlikGPT" in obj.get("markdown","")
                and obj.get("background",{}).get("color")==t["colors"]["paleBlue"]]
        if not brands:
            raise ValueError(f"{filename}: missing executive branded header")
        nav=[obj for obj in children.values() if obj["qInfo"]["qType"]=="button" and
             obj.get("navigation",{}).get("action")=="openWebsite"]
        if not nav:
            raise ValueError(f"{filename}: missing native navigation button")
        for obj in children.values():
            if obj["qInfo"]["qType"]=="kpi":
                actual=obj.get("style",{}).get("background",{}).get("color",{}).get("color")
                if actual not in {t["colors"]["card"], t["colors"]["softBlue"], t["colors"]["softTeal"]}:
                    raise ValueError(f"{filename}: KPI card diverges from design tokens")
    return len(dashboard)

def check():
    t=tokens()
    count=0
    for app,path in MODEL.presentation_manifests().items():
        manifest=read(path)
        if manifest.get("uiTemplate")!=t["templateId"]:
            raise ValueError(f"{app}: no approved UI template in manifest")
        count+=validate_dashboard(read(ROOT/manifest["dashboardSource"]),t,app)
    print(f"UI TEMPLATE VALIDATED: {len(MODEL.presentation_manifests())} apps, "
          f"{count} sheets, {t['templateId']}, no reload")

def main():
    p=argparse.ArgumentParser(description="QlikGPT native dashboard template")
    p.add_argument("--check",action="store_true")
    p.add_argument("--new-key",help="e.g. presentation3 (new app only)")
    p.add_argument("--app-name",default="")
    p.add_argument("--measures",default="",help="comma-separated existing catalog measure IDs")
    p.add_argument("--write",action="store_true",
                   help="Write model-local files: committing them can bootstrap a new Qlik app")
    args=p.parse_args()
    if args.check:
        if args.new_key or args.write:raise ValueError("--check cannot create apps")
        check()
        return
    if not args.new_key:
        p.error("Specify --check or --new-key")
    files=new_files(args.new_key,args.app_name,
                    [x.strip() for x in args.measures.split(",") if x.strip()])
    if args.write:
        for name in files:
            if (ROOT/name).exists():
                raise ValueError("Refusing to overwrite existing file: "+name)
        for name,body in files.items():
            target=ROOT/name
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_text(json.dumps(body,indent=2,ensure_ascii=False)+"\n",
                              encoding="utf-8")
        print("Generated "+", ".join(sorted(files)))
        print("WARNING: Commit may bootstrap a new Qlik app; existing bootstrap can reload.")
    else:
        print(json.dumps(files,indent=2,ensure_ascii=False))
        print("PREVIEW ONLY: nothing written; pass --write explicitly to create files.")

if __name__=="__main__":
    main()
