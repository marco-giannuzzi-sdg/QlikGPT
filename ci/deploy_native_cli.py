"""Write a new native sheet through Qlik CLI; QIX is used only for readback/audit."""
from __future__ import annotations
import importlib.util
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

def main():
    from deploy_visuals import Qix
    from deploy_premium import protected_snapshot
    spec = importlib.util.spec_from_file_location("native_generator", ROOT / "ui/native-overview/generate.py")
    generator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(generator)
    generator.write()
    expected_tree = json.loads(SOURCE.read_text(encoding="utf-8"))[0]
    expected = {props["qInfo"]["qId"]: props for props in walk(expected_tree)}
    allowed = {"sheet", "kpi", "filterpane", "listbox", "text-image", "linechart", "barchart"}
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
        listing = qix.call(doc, "CreateSessionObject", {"qProp": {
            "qInfo": {"qType": "qlikgpt-native-preflight"},
            "qAppObjectListDef": {"qType": "sheet", "qData": {}}}})["qReturn"]["qHandle"]
        infos = qix.call(listing, "GetLayout", [])["qLayout"]["qAppObjectList"]["qItems"]
        if any(item["qInfo"]["qId"] == SHEET for item in infos):
            sheet = qix.call(doc, "GetObject", {"qId": SHEET})["qReturn"]["qHandle"]
            previous = qix.call(sheet, "GetFullPropertyTree", [])["qPropEntry"]
            if previous["qProperty"].get("description") != "qlikgpt-native-cli-v1":
                raise RuntimeError("Sheet ID is owned by another implementation")
            if set(p["qInfo"]["qId"] for p in walk(previous)) - set(expected):
                raise RuntimeError("Unmanaged children exist; refusing to replace them")

        # This is the only persistent write path. GenericObjectEntry recursively
        # materializes native children; qChildren is never a custom qProperty.
        cli("app", "object", "set", str(SOURCE), "--app", APP)

        sheet = qix.call(doc, "GetObject", {"qId": SHEET})["qReturn"]["qHandle"]
        live = qix.call(sheet, "GetFullPropertyTree", [])["qPropEntry"]
        actual = {p["qInfo"]["qId"]: p for p in walk(live)}
        if set(actual) != set(expected):
            raise RuntimeError("CLI did not persist the expected native object hierarchy")
        for ident, target in expected.items():
            props = actual[ident]
            if props["qInfo"]["qType"] != target["qInfo"]["qType"]:
                raise RuntimeError("Native object type mismatch: " + ident)
            if target.get("components"):
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
                print("NATIVE DATA VERIFIED:", target["qInfo"]["qType"], ident, flush=True)
            target_list = target.get("qListObjectDef")
            if target_list:
                if props["qListObjectDef"].get("qLibraryId") != target_list["qLibraryId"]:
                    raise RuntimeError("Filter master binding differs")
                handle = qix.call(doc, "GetObject", {"qId": ident})["qReturn"]["qHandle"]
                if qix.call(handle, "GetLayout", [])["qLayout"]["qListObject"]["qSize"]["qcy"] < 1:
                    raise RuntimeError("Native filter has no values")
                print("NATIVE FILTER VERIFIED:", ident, flush=True)
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
