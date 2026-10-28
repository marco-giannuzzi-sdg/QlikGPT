#!/usr/bin/env python3
"""Deploy native Qlik Sales Overview sheet, charts, KPI and filters using QIX.

QLIK_API_KEY stays in a GitHub secret and is never logged. Idempotent on reruns.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import urllib.parse

import websocket

from model_registry import active_model

ROOT = Path(__file__).resolve().parents[1]
MODEL = active_model()
CONFIG = MODEL.root / "apps" / "presentation1-filters.json"


class Qix:
    def __init__(self, app_id: str):
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



def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Expected presentation app ID as argument")
    definitions = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(definitions, list):
        raise TypeError("apps/presentation1-filters.json must be an array")

    source = json.loads((MODEL.root / "apps" / "presentation1-objects.json").read_text(encoding="utf-8"))
    target = next(
        (obj for obj in source if obj.get("qInfo", {}).get("qId") == "qlikgpt_sales_overview"),
        None,
    )
    if target is None:
        raise RuntimeError("Missing Sales Overview in apps/presentation1-objects.json")

    qix = Qix(sys.argv[1])
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": sys.argv[1]})["qReturn"]["qHandle"]
        sheet = qix.call(doc, "GetObject", {"qId": "qlikgpt_sales_overview"})["qReturn"]["qHandle"]
        if sheet is None:
            raise RuntimeError("Qlik Sales Overview sheet not found")

        sync_sheet_grid(qix, sheet, target)

        # qlik app build may store an embedded qChildren JSON array without
        # creating native QIX children. Ensure actual Engine relationships.
        for props in target.get("qChildren", []):
            child_id = props["qInfo"]["qId"]
            native = find_child(qix, sheet, child_id)
            qix_properties = {k: v for k, v in props.items() if k != "qChildren"}
            qix_properties.setdefault("qExtendsId", "")
            if native is None:
                qix.call(sheet, "CreateChild", [qix_properties])
                native = find_child(qix, sheet, child_id)
                if native is None:
                    raise RuntimeError(f"QIX did not create native sheet object: {child_id}")
                print(f"Created native sheet object: {child_id}", flush=True)
            else:
                print(f"Native sheet object exists: {child_id}", flush=True)
                qix.call(native, "SetProperties", [qix_properties])

        pane = find_child(qix, sheet, "qlikgpt_filter_panel")
        if pane is None:
            raise RuntimeError("Native filterpane was not linked to sheet by QIX")
        for item in definitions:
            item_id, dim_id, label = item["id"], item["dimensionId"], item["label"]
            if not item_id.startswith("qlikgpt_list_"):
                raise ValueError(f"Unexpected listbox ID: {item_id}")
            properties = {
                "qInfo": {"qId": item_id, "qType": "listbox"},
                "qExtendsId": "",
                "visualization": "listbox",
                "title": label,
                "showTitle": True,
                "searchEnabled": True,
                "autoConfirm": True,
                "layoutOptions": {"dataLayout": "singleColumn", "dense": True},
                "qListObjectDef": {
                    "qStateName": "$",
                    "qLibraryId": dim_id,
                    "qDef": {"qFieldDefs": [""], "qFieldLabels": [""]},
                    "qInitialDataFetch": [
                        {"qTop": 0, "qHeight": 100, "qLeft": 0, "qWidth": 1}
                    ],
                },
            }
            existing = find_child(qix, pane, item_id)
            if existing is None:
                qix.call(pane, "CreateChild", [properties])
                existing = find_child(qix, pane, item_id)
                if existing is None:
                    raise RuntimeError(f"QIX did not create listbox: {item_id}")
                print(f"Created native Qlik filter: {label}", flush=True)
            else:
                qix.call(existing, "SetProperties", [properties])
                print(f"Updated native Qlik filter: {label}", flush=True)
            native_filter_props = qix.call(existing, "GetProperties", [])["qProp"]
            persisted_id = native_filter_props.get("qListObjectDef", {}).get("qLibraryId")
            if persisted_id != dim_id:
                raise RuntimeError(f"Listbox {item_id} must reference master dimension {dim_id}; got {persisted_id}")
            list_layout = qix.call(existing, "GetLayout", [])["qLayout"]
            row_count = list_layout.get("qListObject", {}).get("qSize", {}).get("qcy", 0)
            if row_count < 1:
                raise RuntimeError(f"Listbox {item_id} with master dimension {dim_id} has no values")
            print(f"FILTER MASTER VERIFIED {item_id} => {dim_id}, values={row_count}", flush=True)

        # Contract check: every chart/KPI must actually reference a catalog
        # master measure, not merely contain a valid-looking qLibraryId in JSON.
        for visual in target.get("qChildren", []):
            wanted = visual.get("qHyperCubeDef", {}).get("qMeasures", [])
            if not wanted:
                continue
            hid = find_child(qix, sheet, visual["qInfo"]["qId"])
            props_read = qix.call(hid, "GetProperties", [])["qProp"]
            actual = props_read.get("qHyperCubeDef", {}).get("qMeasures", [])
            if len(actual) != len(wanted):
                raise RuntimeError("Wrong number of visual measures")
            for expected, observed in zip(wanted, actual):
                mid = expected.get("qLibraryId")
                if not mid or observed.get("qLibraryId") != mid:
                    raise RuntimeError("Visual is not using catalog master: " + visual["qInfo"]["qId"])
                if observed.get("qDef", {}).get("qDef", "").strip():
                    raise RuntimeError("Inline master formula found in " + visual["qInfo"]["qId"])
            expected_dims = visual.get("qHyperCubeDef", {}).get("qDimensions", [])
            actual_dims = props_read.get("qHyperCubeDef", {}).get("qDimensions", [])
            if len(expected_dims) != len(actual_dims):
                raise RuntimeError(f"Unexpected dimension count in {visual['qInfo']['qId']}")
            for wanted_dim, observed_dim in zip(expected_dims, actual_dims):
                dimension_id = wanted_dim.get("qLibraryId")
                if not dimension_id or observed_dim.get("qLibraryId") != dimension_id:
                    raise RuntimeError(
                        f"Chart {visual['qInfo']['qId']} is not linked to master dimension {dimension_id}"
                    )
                if any(f.strip() for f in observed_dim.get("qDef", {}).get("qFieldDefs", []) if isinstance(f,str)):
                    raise RuntimeError(f"Chart {visual['qInfo']['qId']} still contains inline fields")
                print(f"CHART DIMENSION MASTER VERIFIED {visual['qInfo']['qId']} => {dimension_id}", flush=True)
            print("Catalog qLibraryId verified for " + visual["qInfo"]["qId"], flush=True)

        # The visual brand block must carry real markdown, not just a title.
        brand_handle = find_child(qix, sheet, "qlikgpt_brand_header")
        if brand_handle is None:
            raise RuntimeError("Branded header object missing from Qlik sheet")
        brand_layout = qix.call(brand_handle, "GetLayout", [])["qLayout"]
        if "QlikGPT" not in str(brand_layout.get("markdown", "")):
            raise RuntimeError("QlikGPT brand markup was not saved in the header")
        print("Brand header: native text-image with QlikGPT wordmark saved.", flush=True)

        # Validate native chart Engine data, not merely object persistence.
        # A sheet can contain a chart title while the visualization is blank.
        for chart_id in ("qlikgpt_chart_month", "qlikgpt_chart_market"):
            chart_handle = find_child(qix, sheet, chart_id)
            if chart_handle is None:
                raise RuntimeError("Native chart not addressable: " + chart_id)
            layout = qix.call(chart_handle, "GetLayout", [])["qLayout"]
            cube = layout.get("qHyperCube", {})
            size = cube.get("qSize", {})
            pages = cube.get("qDataPages", [])
            sample = (pages[0].get("qMatrix", [])[:2] if pages else [])
            print(
                "QIX chart diagnostic %s: size=%s dim=%s measures=%s "
                "pages=%s sample=%s" % (
                    chart_id, size, cube.get("qDimensionInfo"),
                    cube.get("qMeasureInfo"), len(pages), sample,
                ), flush=True
            )
            if size.get("qcy", 0) == 0:
                raise RuntimeError("Chart hypercube contains zero data rows: " + chart_id)

        # Verify the live Engine hierarchy, not only JSON exported by Qlik CLI.
        for props in target.get("qChildren", []):
            if find_child(qix, sheet, props["qInfo"]["qId"]) is None:
                raise RuntimeError(f"Sheet child missing: {props['qInfo']['qId']}")
        for item in definitions:
            if find_child(qix, pane, item["id"]) is None:
                raise RuntimeError(f"Filter child missing: {item['id']}")
        # Return the pilot app to a built-in Qlik theme; the Executive
        # native UI must not depend on an uploaded custom theme package.
        # Preserve any unrelated user-selected theme.
        app_list = qix.call(doc, "CreateSessionObject", {"qProp": {
            "qInfo": {"qType": "qlikgpt-theme-list"},
            "qAppObjectListDef": {"qType": "appprops", "qData": {"theme": "/theme"}}
        }})["qReturn"]["qHandle"]
        list_items = qix.call(app_list, "GetLayout", [])["qLayout"].get(
            "qAppObjectList", {}).get("qItems", [])
        if len(list_items) == 1:
            app_props_id = list_items[0].get("qInfo", {}).get("qId")
            if app_props_id:
                ap_handle = qix.call(doc, "GetObject", {"qId":app_props_id})["qReturn"]["qHandle"]
                ap = qix.call(ap_handle,"GetProperties",[])["qProp"]
                if ap.get("theme") == "qlikgpt-executive-v1":
                    rebuilt=dict(ap)
                    rebuilt["theme"]="horizon"
                    rebuilt["sheetTitleBgColor"]="#142840"
                    rebuilt["sheetTitleGradientColor"]="#3365D5"
                    rebuilt["sheetTitleColor"]="#FFFFFF"
                    qix.call(ap_handle,"SetProperties",[rebuilt])
                    verify_theme=qix.call(ap_handle,"GetProperties",[])["qProp"]
                    if verify_theme.get("theme")!="horizon":
                        raise RuntimeError("Built-in Qlik theme restore failed")
                    print("Custom theme detached; built-in horizon + native brand header assigned.",flush=True)

        qix.call(doc, "DoSave", [])
        print(
            f"QIX hierarchy verified: {len(target['qChildren'])} sheet children, "
            f"{len(definitions)} nested listboxes; app saved.",
            flush=True,
        )
    finally:
        qix.close()


if __name__ == "__main__":
    main()
