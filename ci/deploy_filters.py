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

    qix = Qix(sys.argv[1])
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": sys.argv[1]})["qReturn"]["qHandle"]
        sheet = qix.call(doc, "GetObject", {"qId": "qlikgpt_sales_overview"})["qReturn"]["qHandle"]
        pane = qix.call(sheet, "GetChild", {"qId": "qlikgpt_filter_panel"})["qReturn"]["qHandle"]
        print("QIX handles: doc=%s sheet=%s pane=%s" % (doc, sheet, pane), flush=True)
        for handle_name, handle in (("sheet", sheet), ("pane", pane)):
            try:
                info = qix.call(handle, "GetInfo")
                print("QIX %s info: %s" % (handle_name, info.get("qInfo")), flush=True)
            except RuntimeError as exc:
                print("QIX %s GetInfo diagnostic: %s" % (handle_name, exc), flush=True)

        for item in definitions:
            item_id, field, label = item["id"], item["field"], item["label"]
            if not item_id.startswith("qlikgpt_list_"):
                raise ValueError(f"Unexpected listbox ID: {item_id}")
            if find_child(qix, pane, item_id) is not None:
                print(f"Filter already exists: {label} ({item_id})")
                continue
            # Qlik documents CreateChild with positional JSON-RPC params.
            # Keep properties minimal to mirror the native Engine example.
            properties = {
                "qInfo": {"qId": item_id, "qType": "listbox"},
                "qExtendsId": "",
                "visualization": "listbox",
                "title": label,
                "qListObjectDef": {
                    "qStateName": "$",
                    "qLibraryId": "",
                    "qDef": {
                        "qFieldDefs": [field],
                        "qFieldLabels": [label],
                        "qSortCriterias": [{"qSortByLoadOrder": 1}],
                    },
                    "qInitialDataFetch": [
                        {"qTop": 0, "qHeight": 100, "qLeft": 0, "qWidth": 1}
                    ],
                },
            }
            # Test the minimal CreateChild request first; apply listbox config
            # separately using SetProperties after the handle exists.
            qix.call(pane, "CreateChild", [{"qInfo": properties["qInfo"], "qExtendsId": ""}])
            child_handle = find_child(qix, pane, item_id)
            if child_handle is None:
                raise RuntimeError("Minimal CreateChild did not return a child handle")
            qix.call(child_handle, "SetProperties", {"qProp": properties})
            if find_child(qix, pane, item_id) is None:
                raise RuntimeError(f"QIX did not register created child: {item_id}")
            print(f"Created native Qlik filter: {label} ({item_id})")

        needed = {d["id"] for d in definitions}
        missing = [child_id for child_id in needed if find_child(qix, pane, child_id) is None]
        if missing:
            raise RuntimeError("Missing filterpane children: " + ", ".join(missing))
        qix.call(doc, "DoSave")
        print(f"QIX filterpane verified: {len(needed)} native listboxes saved.")
    finally:
        qix.close()


if __name__ == "__main__":
    main()
