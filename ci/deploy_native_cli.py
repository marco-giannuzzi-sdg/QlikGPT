"""Write a new native sheet through Qlik CLI; QIX is used only for readback/audit."""
from __future__ import annotations
import copy
import importlib.util
import math
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
APP = "07dfa926-4895-4fb2-af4c-eac90e9eb2cb"
SHEET = "qlikgpt_sales_native"
SOURCE = ROOT / "ui/native-overview/sheet.json"

def cli(*args):
    print("+ qlik " + " ".join(args), flush=True)
    result = subprocess.run(["qlik", *args], cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Qlik CLI failed: " + result.stderr[-2000:])
    return result.stdout

def walk(tree):
    yield tree["qProperty"]
    for child in tree.get("qChildren", []):
        yield from walk(child)

TITLE_STYLE = {"sheetTitleBgColor": "#142840", "sheetTitleGradientColor": "#142840",
               "sheetTitleColor": "#FFFFFF"}

def styled_app_tree(previous):
    tree = copy.deepcopy(previous)
    tree["qProperty"].update(TITLE_STYLE)
    return tree

def main():
    from deploy_visuals import Qix
    from deploy_premium import protected_snapshot
    spec = importlib.util.spec_from_file_location("native_generator", ROOT / "ui/native-overview/generate.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.write()
    expected_tree = json.loads(SOURCE.read_text(encoding="utf-8"))[0]
    expected = {props["qInfo"]["qId"]: props for props in walk(expected_tree)}
    allowed = {"sheet", "kpi", "filterpane", "listbox", "text-image", "linechart", "barchart", "table", "piechart"}
    if any(props["qInfo"]["qType"] not in allowed for props in expected.values()):
        raise RuntimeError("Only built-in native objects are permitted")
    registry = json.loads((ROOT / "semantic-models/sales/deployment/app-ids.json").read_text())
    if registry["presentation"] != APP:
        raise RuntimeError("Unexpected target application")
    qix = Qix(APP)
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": APP})["qReturn"]["qHandle"]
        before = protected_snapshot(qix, doc)
        reload_before = qix.call(doc, "GetAppLayout", [])["qLayout"].get("qLastReloadTime")
        app_list = qix.call(doc, "CreateSessionObject", {"qProp": {
            "qInfo": {"qType": "qlikgpt-title-preflight"},
            "qAppObjectListDef": {"qType": "appprops", "qData": {}}}})["qReturn"]["qHandle"]
        app_items = qix.call(app_list, "GetLayout", [])["qLayout"]["qAppObjectList"]["qItems"]
        if len(app_items) != 1:
            raise RuntimeError("Expected exactly one existing app properties object")
        app_id = app_items[0]["qInfo"]["qId"]
        app_handle = qix.call(doc, "GetObject", {"qId": app_id})["qReturn"]["qHandle"]
        app_before = qix.call(app_handle, "GetFullPropertyTree", [])["qPropEntry"]
        app_target = styled_app_tree(app_before)
        listing = qix.call(doc, "CreateSessionObject", {"qProp": {
            "qInfo": {"qType": "qlikgpt-native-preflight"},
            "qAppObjectListDef": {"qType": "sheet", "qData": {}}}})["qReturn"]["qHandle"]
        infos = qix.call(listing, "GetLayout", [])["qLayout"]["qAppObjectList"]["qItems"]
        if any(item["qInfo"]["qId"] == SHEET for item in infos):
            sheet = qix.call(doc, "GetObject", {"qId": SHEET})["qReturn"]["qHandle"]
            previous = qix.call(sheet, "GetFullPropertyTree", [])["qPropEntry"]
            if previous["qProperty"].get("description") != "qlikgpt-native-cli-v1":
                raise RuntimeError("Sheet ID is owned by another implementation")
            retired = {p["qInfo"]["qId"]: p for p in walk(previous)
                       if p["qInfo"]["qId"] not in expected}
            # Only the duplicate header explicitly requested for removal may retire.
            for ident, prop in retired.items():
                if (ident != "qlikgpt_native_header" or prop["qInfo"]["qType"] != "text-image"
                        or prop.get("title") != "Sales Intelligence"):
                    raise RuntimeError("Unmanaged children exist; refusing to replace them")

        # All persistent writes are full-tree imports via the CLI.
        # Preserve unrelated app styling, theme and children; change only native title colors.
        app_source = ROOT / "ui/native-overview/app-title.generated.json"
        app_source.write_text(json.dumps([app_target], ensure_ascii=False), encoding="utf-8")
        cli("app", "object", "set", str(app_source), "--app", APP)
        if qix.call(app_handle, "GetFullPropertyTree", [])["qPropEntry"] != app_target:
            raise RuntimeError("Native title colors or unrelated app properties differ after CLI import")
        print("NATIVE APP TITLE VERIFIED: navy background, white text; unrelated settings preserved", flush=True)
        # This is the only sheet write path. GenericObjectEntry recursively
        # materializes native children; qChildren is never a custom qProperty.
        cli("app", "object", "set", str(SOURCE), "--app", APP)

        sheet = qix.call(doc, "GetObject", {"qId": SHEET})["qReturn"]["qHandle"]
        live = qix.call(sheet, "GetFullPropertyTree", [])["qPropEntry"]
        actual = {p["qInfo"]["qId"]: p for p in walk(live)}
        if set(actual) != set(expected):
            raise RuntimeError("CLI did not persist the expected native object hierarchy")
        data = {}
        for ident, target in expected.items():
            props = actual[ident]
            if props["qInfo"]["qType"] != target["qInfo"]["qType"]:
                raise RuntimeError("Native object type mismatch: " + ident)
            if any(c.get("key") == "general" for c in target.get("components", [])):
                expected_general = next(c for c in target["components"] if c["key"] == "general")
                observed_general = next((c for c in props.get("components", []) if c["key"] == "general"), None)
                if observed_general != expected_general:
                    raise RuntimeError("Native component styles did not persist: " + ident)
            target_cube = target.get("qHyperCubeDef")
            if target_cube:
                observed_cube = props["qHyperCubeDef"]
                for key in ("qMeasures", "qDimensions"):
                    if [x.get("qLibraryId") for x in observed_cube.get(key, [])] != [x.get("qLibraryId") for x in target_cube.get(key, [])]:
                        raise RuntimeError("Master bindings differ: " + ident)
                if any(x.get("qDef", {}).get("qDef", "").strip() for x in observed_cube.get("qMeasures", [])):
                    raise RuntimeError("Unexpected inline measure")
                handle = qix.call(doc, "GetObject", {"qId": ident})["qReturn"]["qHandle"]
                cube = qix.call(handle, "GetLayout", [])["qLayout"]["qHyperCube"]
                if cube.get("qError") or cube.get("qSize", {}).get("qcy", 0) < 1:
                    raise RuntimeError("Native chart has no Engine data: " + ident)
                data[ident] = cube
                print("NATIVE DATA VERIFIED:", target["qInfo"]["qType"], ident, flush=True)
            target_list = target.get("qListObjectDef")
            if target_list:
                if props["qListObjectDef"].get("qLibraryId") != target_list["qLibraryId"]:
                    raise RuntimeError("Filter master binding differs")
                handle = qix.call(doc, "GetObject", {"qId": ident})["qReturn"]["qHandle"]
                if qix.call(handle, "GetLayout", [])["qLayout"]["qListObject"]["qSize"]["qcy"] < 1:
                    raise RuntimeError("Native filter has no values")
                print("NATIVE FILTER VERIFIED:", ident, flush=True)
        revenue = data["qlikgpt_native_kpi_0"]["qDataPages"][0]["qMatrix"][0][0]["qNum"]
        for ident in ("qlikgpt_native_market_detail", "qlikgpt_native_channels"):
            chart = data[ident]
            rows = [row for page in chart["qDataPages"] for row in page["qMatrix"]]
            if len(rows) != chart["qSize"]["qcy"] or not math.isclose(
                    sum(row[1]["qNum"] for row in rows), revenue, rel_tol=1e-9, abs_tol=0.01):
                raise RuntimeError("Breakdown revenue does not reconcile with KPI: " + ident)
        print("BREAKDOWN REVENUE RECONCILED: table and donut equal governed revenue KPI", flush=True)
        if protected_snapshot(qix, doc) != before:
            raise RuntimeError("Protected semantic assets changed")
        if qix.call(doc, "GetAppLayout", [])["qLayout"].get("qLastReloadTime") != reload_before:
            raise RuntimeError("Reload timestamp changed")
        # Independent CLI round trip as an additional hierarchy check.
        exported = json.loads(cli("app", "object", "properties", SHEET, "--full", "--app", APP, "--json"))
        if isinstance(exported, list):
            exported = exported[0]
        if "qPropEntry" in exported:
            exported = exported["qPropEntry"]
        if {p["qInfo"]["qId"] for p in walk(exported)} != set(expected):
            raise RuntimeError("CLI full-tree roundtrip differs")
        print("CLI FULL-TREE VERIFIED:", len(actual), "native objects", flush=True)
        print("SEMANTIC SNAPSHOT UNCHANGED. DATA RELOADS: 0.", flush=True)
    finally:
        qix.close()
    print("NATIVE SHEET: " + registry["tenant"].rstrip("/") + "/sense/app/" + APP + "/sheet/" + SHEET + "/state/analysis")

if __name__ == "__main__":
    main()
