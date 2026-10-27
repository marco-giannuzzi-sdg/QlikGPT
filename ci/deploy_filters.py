#!/usr/bin/env python3
"""Create native Qlik filter pane listboxes using QIX WebSocket from GitHub Actions.

QLIK_API_KEY stays in a GitHub secret and is never logged. Idempotent on reruns.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import sys
import urllib.parse

import websocket

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "frontend" / "filters.json"


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


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Expected presentation app ID as argument")
    definitions = json.loads(CONFIG.read_text(encoding="utf-8"))
    if not isinstance(definitions, list):
        raise TypeError("frontend/filters.json must be an array")

    source = json.loads((ROOT / "frontend" / "objects.json").read_text(encoding="utf-8"))
    target = next(
        (obj for obj in source if obj.get("qInfo", {}).get("qId") == "qlikgpt_sales_overview"),
        None,
    )
    if target is None:
        raise RuntimeError("Missing Sales Overview in frontend/objects.json")

    qix = Qix(sys.argv[1])
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": sys.argv[1]})["qReturn"]["qHandle"]
        sheet = qix.call(doc, "GetObject", {"qId": "qlikgpt_sales_overview"})["qReturn"]["qHandle"]
        if sheet is None:
            raise RuntimeError("Qlik Sales Overview sheet not found")

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
            item_id, field, label = item["id"], item["field"], item["label"]
            if not item_id.startswith("qlikgpt_list_"):
                raise ValueError(f"Unexpected listbox ID: {item_id}")
            properties = {
                "qInfo": {"qId": item_id, "qType": "listbox"},
                "qExtendsId": "",
                "visualization": "listbox",
                "title": label,
                "qListObjectDef": {
                    "qStateName": "$",
                    "qLibraryId": "",
                    "qDef": {"qFieldDefs": [field], "qFieldLabels": [label]},
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
