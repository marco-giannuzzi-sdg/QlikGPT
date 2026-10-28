#!/usr/bin/env python3
"""Deploy authored Sales Overview JSON through Qlik CLI; QIX only audits state.

QLIK_API_KEY stays in a GitHub secret and is never logged. Idempotent on reruns.
"""
from __future__ import annotations
from copy import deepcopy
import json
import math
import subprocess
import tempfile
import os
from pathlib import Path
import sys
import urllib.parse


from model_registry import active_model

ROOT = Path(__file__).resolve().parents[1]
MODEL = active_model()
CONFIG = MODEL.root / "apps" / "presentation1-filters.json"


class Qix:
    def __init__(self, app_id: str):
        import websocket
        tenant = os.environ["QLIK_TENANT"].rstrip("/")
        token = os.environ["QLIK_API_KEY"]
        if not tenant.startswith("https://") or not token:
            raise RuntimeError("Qlik tenant/API key is not configured")
        url = "wss://" + tenant.removeprefix("https://") + "/app/" + urllib.parse.quote(app_id, safe="")
        self.ws = websocket.create_connection(
            url, header={"Authorization": "Bearer " + token},
            origin=tenant, timeout=45,
        )
        self.request_id = 0

    def call(self, handle: int, method: str, params: dict | list | None = None) -> dict:
        self.request_id += 1
        wanted_id = self.request_id
        message = {
            "jsonrpc": "2.0", "id": wanted_id,
            "handle": handle, "method": method,
        }
        if params is not None:
            message["params"] = params
        self.ws.send(json.dumps(message))
        for _ in range(200):
            response = json.loads(self.ws.recv())
            if response.get("id") != wanted_id:
                continue
            if "error" in response:
                err = response["error"]
                raise RuntimeError(
                    f"QIX {method} error {err.get('code')}: {err.get('message')}"
                )
            return response.get("result", {})
        raise RuntimeError(f"No matching QIX response for {method}")

    def close(self) -> None:
        self.ws.close()


def find_child(qix: Qix, parent: int, child_id: str) -> int | None:
    """Use GetChild for a specific known ID; some engines reject GetChildInfos."""
    try:
        result = qix.call(parent, "GetChild", {"qId": child_id})
        return result["qReturn"]["qHandle"]
    except RuntimeError as exc:
        error = str(exc)
        # A missing object can return -32602 or a not-found error from QIX.
        # Never suppress unrelated authentication / session / application errors.
        if "error -32602" in error or "not found" in error.lower():
            return None
        raise


def sync_sheet_grid(qix: Qix, sheet: int, target: dict) -> None:
    """Reconcile the persisted sheet grid before updating child visuals."""
    existing_sheet = qix.call(sheet, "GetProperties", [])["qProp"]
    updated_sheet = dict(existing_sheet)
    updated_sheet.update({k: v for k, v in target.items()
                          if k not in {"qChildren", "qInfo"}})
    qix.call(sheet, "SetProperties", [updated_sheet])
    live_sheet = qix.call(sheet, "GetProperties", [])["qProp"]
    if live_sheet.get("columns") != target["columns"] or live_sheet.get("rows") != target["rows"]:
        raise RuntimeError("Native sheet dimensions did not persist")
    expected_cells = {
        (cell["name"], cell["col"], cell["row"], cell["colspan"], cell["rowspan"])
        for cell in target["cells"]
    }
    actual_cells = {
        (cell["name"], cell["col"], cell["row"], cell["colspan"], cell["rowspan"])
        for cell in live_sheet.get("cells", [])
    }
    if actual_cells != expected_cells:
        raise RuntimeError("Native sheet cell placement differs from versioned layout")
    print(
        f"Native sheet geometry VERIFIED: {target['columns']}x{target['rows']} "
        f"/ {len(expected_cells)} cells", flush=True
    )




ALLOWED_TYPES = {"sheet", "kpi", "filterpane", "listbox", "text-image", "linechart", "barchart", "table", "piechart"}
RETIRED = {"qlikgpt_brand_header": "text-image", "qlikgpt_nav_shared_kpis": "button"}
SHEET = "qlikgpt_sales_overview"


def nodes(tree):
    yield tree["qProperty"]
    for child in tree.get("qChildren", []):
        yield from nodes(child)


def property_tree(properties):
    """Transport adapter only: authored JSON properties remain the source of truth."""
    props = deepcopy(properties)
    children = props.pop("qChildren", [])
    tree = {"qProperty": props}
    if children:
        tree["qChildren"] = [property_tree(child) for child in children]
    return tree


def overview_tree(source, filters):
    target = next((item for item in source if item.get("qInfo", {}).get("qId") == SHEET), None)
    if target is None:
        raise ValueError("Missing Sales Overview in presentation1-objects.json")
    tree = property_tree(target)
    panes = [item for item in tree.get("qChildren", [])
             if item["qProperty"]["qInfo"]["qId"] == "qlikgpt_filter_panel"]
    if len(panes) != 1:
        raise ValueError("Expected the declared qlikgpt_filter_panel")
    if panes[0].get("qChildren"):
        raise ValueError("Filter definitions belong in presentation1-filters.json")
    children = []
    for item in filters:
        ident, dimension, label = item["id"], item["dimensionId"], item["label"]
        if not ident.startswith("qlikgpt_list_"):
            raise ValueError("Unexpected filter ID: " + ident)
        props = {
            "qInfo": {"qId": ident, "qType": "listbox"}, "qExtendsId": "",
            "visualization": "listbox", "title": label, "showTitle": True,
            "searchEnabled": True, "autoConfirm": True,
            "layoutOptions": {"dataLayout": "singleColumn", "dense": True},
            "qListObjectDef": {"qStateName": "$", "qLibraryId": dimension,
                "qInitialDataFetch": [{"qTop": 0, "qLeft": 0, "qWidth": 1, "qHeight": 1000}]},
            "components": [{"key": "theme",
                "header": {"fontFamily": "Arial", "fontSize": "12px",
                           "fontColor": {"index": -1, "color": "#142840", "alpha": 1}},
                "content": {"fontFamily": "Arial", "fontSize": "12px"}}],
        }
        children.append(property_tree(props))
    panes[0]["qChildren"] = children
    return tree


def validate_tree(tree, manifest):
    ids = set()
    for prop in nodes(tree):
        ident, kind = prop["qInfo"]["qId"], prop["qInfo"]["qType"]
        if ident in ids or kind not in ALLOWED_TYPES:
            raise ValueError("Duplicate ID or unsupported visualization: " + ident)
        ids.add(ident)
        cube = prop.get("qHyperCubeDef", {})
        for measure in cube.get("qMeasures", []):
            if measure.get("qLibraryId") not in manifest["catalogMeasures"]:
                raise ValueError("Unsubscribed measure in " + ident)
            if measure.get("qDef", {}).get("qDef", "").strip():
                raise ValueError("Inline measure in " + ident)
        for dim in cube.get("qDimensions", []):
            if dim.get("qLibraryId") not in manifest["catalogDimensions"]:
                raise ValueError("Unsubscribed dimension in " + ident)
            if any(f.strip() for f in dim.get("qDef", {}).get("qFieldDefs", []) if isinstance(f, str)):
                raise ValueError("Inline dimension in " + ident)
        if prop.get("qListObjectDef", {}).get("qLibraryId") not in (None, *manifest["catalogDimensions"]):
            raise ValueError("Unsubscribed filter dimension in " + ident)
        if kind == "table":
            width = len(cube["qDimensions"]) + len(cube["qMeasures"])
            if (cube.get("columnOrder") != list(range(width)) or
                    len(cube.get("columnWidths", [])) != width or
                    cube["qInitialDataFetch"][0]["qWidth"] != width):
                raise ValueError("Update the table column metadata for " + ident)


def validate_retired(previous, expected_ids):
    for prop in nodes(previous):
        ident, kind = prop["qInfo"]["qId"], prop["qInfo"]["qType"]
        if ident not in expected_ids and RETIRED.get(ident) != kind:
            raise RuntimeError("Unmanaged child would be removed: " + ident)


def cli(app_id, *arguments):
    print("+ qlik app " + " ".join(arguments) + " --app " + app_id, flush=True)
    result = subprocess.run(["qlik", "app", *arguments, "--app", app_id],
                            cwd=ROOT, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError("Qlik CLI failed: " + result.stderr[-2000:])
    return result.stdout


def semantic_snapshot(qix, doc, manifest):
    result = {"script": qix.call(doc, "GetScript", []).get("qScript"),
              "reload": qix.call(doc, "GetAppLayout", [])["qLayout"].get("qLastReloadTime")}
    for method, key in (("GetMeasure", "catalogMeasures"), ("GetDimension", "catalogDimensions")):
        result[key] = {}
        for ident in manifest[key]:
            handle = qix.call(doc, method, {"qId": ident})["qReturn"]["qHandle"]
            result[key][ident] = qix.call(handle, "GetProperties", [])["qProp"]
    return result


def sheet_snapshots(qix, doc):
    listing = qix.call(doc, "CreateSessionObject", {"qProp": {
        "qInfo": {"qType": "qlikgpt-overview-audit"},
        "qAppObjectListDef": {"qType": "sheet", "qData": {}}}})["qReturn"]["qHandle"]
    items = qix.call(listing, "GetLayout", [])["qLayout"]["qAppObjectList"]["qItems"]
    snapshots = {}
    for item in items:
        ident = item["qInfo"]["qId"]
        handle = qix.call(doc, "GetObject", {"qId": ident})["qReturn"]["qHandle"]
        snapshots[ident] = qix.call(handle, "GetFullPropertyTree", [])["qPropEntry"]
    return snapshots


def audit(qix, doc, expected, actual):
    wanted = {p["qInfo"]["qId"]: p for p in nodes(expected)}
    observed = {p["qInfo"]["qId"]: p for p in nodes(actual)}
    if set(wanted) != set(observed):
        raise RuntimeError("Native Overview hierarchy differs from JSON")
    for key in ("cells", "columns", "rows", "title"):
        if actual["qProperty"].get(key) != expected["qProperty"].get(key):
            raise RuntimeError("Overview sheet layout did not persist: " + key)
    data = {}
    for ident, target in wanted.items():
        prop = observed[ident]
        if prop["qInfo"]["qType"] != target["qInfo"]["qType"]:
            raise RuntimeError("Native type differs: " + ident)
        if prop.get("components", []) != target.get("components", []):
            raise RuntimeError("Native styles differ: " + ident)
        cube = target.get("qHyperCubeDef")
        if cube:
            for key in ("qMeasures", "qDimensions"):
                if [v.get("qLibraryId") for v in prop["qHyperCubeDef"].get(key, [])] != [
                        v.get("qLibraryId") for v in cube.get(key, [])]:
                    raise RuntimeError("Master bindings differ: " + ident)
            if any(v.get("qDef", {}).get("qDef", "").strip()
                   for v in prop["qHyperCubeDef"]["qMeasures"]):
                raise RuntimeError("Inline measure persisted: " + ident)
            handle = qix.call(doc, "GetObject", {"qId": ident})["qReturn"]["qHandle"]
            live_cube = qix.call(handle, "GetLayout", [])["qLayout"]["qHyperCube"]
            if live_cube.get("qError") or live_cube["qSize"]["qcy"] < 1:
                raise RuntimeError("Native object has no Engine data: " + ident)
            data[ident] = live_cube
            print("OVERVIEW DATA VERIFIED:", ident, flush=True)
        if target.get("qListObjectDef"):
            if prop["qListObjectDef"].get("qLibraryId") != target["qListObjectDef"]["qLibraryId"]:
                raise RuntimeError("Filter master binding differs: " + ident)
            handle = qix.call(doc, "GetObject", {"qId": ident})["qReturn"]["qHandle"]
            if qix.call(handle, "GetLayout", [])["qLayout"]["qListObject"]["qSize"]["qcy"] < 1:
                raise RuntimeError("Native filter has no values: " + ident)
            print("OVERVIEW FILTER VERIFIED:", ident, flush=True)
    revenue = data["qlikgpt_kpi_revenue"]["qDataPages"][0]["qMatrix"][0][0]["qNum"]
    for ident in ("qlikgpt_chart_month", "qlikgpt_chart_market", "qlikgpt_table_sales", "qlikgpt_chart_channel"):
        cube = data[ident]
        rows = [row for page in cube["qDataPages"] for row in page["qMatrix"]]
        if len(rows) != cube["qSize"]["qcy"] or not math.isclose(
                sum(row[len(cube["qDimensionInfo"])]["qNum"] for row in rows),
                revenue, rel_tol=1e-9, abs_tol=0.01):
            raise RuntimeError("Revenue breakdown does not reconcile: " + ident)
    print("OVERVIEW REVENUE RECONCILED: trend, market, detail and channel match KPI", flush=True)


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Expected presentation app ID as argument")
    app_id = sys.argv[1]
    state = json.loads(MODEL.state_path.read_text(encoding="utf-8"))
    if app_id != state["presentation"]:
        raise ValueError("Only the registered first Presentation app may be updated")
    manifest = json.loads(MODEL.presentation_manifests()["presentation"].read_text(encoding="utf-8"))
    source = json.loads((ROOT / manifest["dashboardSource"]).read_text(encoding="utf-8"))
    definitions = json.loads((ROOT / manifest["filterSource"]).read_text(encoding="utf-8"))
    expected = overview_tree(source, definitions)
    validate_tree(expected, manifest)
    qix = Qix(app_id)
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": app_id})["qReturn"]["qHandle"]
        before = semantic_snapshot(qix, doc, manifest)
        sheets_before = sheet_snapshots(qix, doc)
        if SHEET not in sheets_before:
            raise RuntimeError("The existing Sales Overview sheet was not found")
        previous = sheets_before.pop(SHEET)
        validate_retired(previous, {p["qInfo"]["qId"] for p in nodes(expected)})
        # Preserve unrelated root properties; authored layout/styling takes precedence.
        merged = deepcopy(previous["qProperty"])
        merged.pop("qChildren", None)
        merged.update(expected["qProperty"])
        expected["qProperty"] = merged
        with tempfile.TemporaryDirectory(prefix="qlikgpt-overview-") as directory:
            payload = Path(directory) / "overview-entry.json"
            payload.write_text(json.dumps([expected], ensure_ascii=False), encoding="utf-8")
            # Sole persistent write: CLI imports declared properties as physical children.
            cli(app_id, "object", "set", str(payload))
        handle = qix.call(doc, "GetObject", {"qId": SHEET})["qReturn"]["qHandle"]
        actual = qix.call(handle, "GetFullPropertyTree", [])["qPropEntry"]
        audit(qix, doc, expected, actual)
        exported = json.loads(cli(app_id, "object", "properties", SHEET, "--full", "--json"))
        if isinstance(exported, list):
            exported = exported[0]
        exported = exported.get("qPropEntry", exported)
        if {p["qInfo"]["qId"] for p in nodes(exported)} != {p["qInfo"]["qId"] for p in nodes(expected)}:
            raise RuntimeError("CLI full-tree round trip differs")
        if semantic_snapshot(qix, doc, manifest) != before:
            raise RuntimeError("Semantic definitions or reload timestamp changed")
        sheets_after = sheet_snapshots(qix, doc)
        sheets_after.pop(SHEET)
        if sheets_after != sheets_before:
            raise RuntimeError("Another sheet changed during the Overview deployment")
        print("OVERVIEW CLI FULL-TREE VERIFIED:", len(list(nodes(actual))), "native objects", flush=True)
        print("SEMANTIC SNAPSHOT UNCHANGED. OTHER SHEETS UNCHANGED. DATA RELOADS: 0.", flush=True)
    finally:
        qix.close()


if __name__ == "__main__":
    main()
