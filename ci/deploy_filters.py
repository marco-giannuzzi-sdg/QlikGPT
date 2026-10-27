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

    def call(self, handle: int, method: str, params: dict | None = None) -> dict:
        self.request_id += 1
        wanted_id = self.request_id
        message = {
            "jsonrpc": "2.0", "id": wanted_id,
            "handle": handle, "method": method, "params": params or {},
        }
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


def child_ids(qix: Qix, handle: int) -> set[str]:
    result = qix.call(handle, "GetChildInfos")
    return {info["qId"] for info in result.get("qInfos", [])}


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
        existing = child_ids(qix, pane)

        for item in definitions:
            item_id, field, label = item["id"], item["field"], item["label"]
            if not item_id.startswith("qlikgpt_list_"):
                raise ValueError(f"Unexpected listbox ID: {item_id}")
            if item_id in existing:
                print(f"Filter already exists: {label} ({item_id})")
                continue
            properties = {
                "qInfo": {"qId": item_id, "qType": "listbox"},
                "qExtendsId": "",
                "visualization": "listbox",
                "title": label,
                "qListObjectDef": {
                    "qStateName": "$",
                    "qDef": {"qGrouping": "N", "qFieldDefs": [field], "qFieldLabels": [label]},
                    "qShowAlternatives": True,
                    "qInitialDataFetch": [{"qLeft": 0, "qTop": 0, "qWidth": 1, "qHeight": 100}],
                },
            }
            created = qix.call(pane, "CreateChild", {"qProp": properties})
            returned_id = created.get("qInfo", {}).get("qId", item_id)
            if returned_id != item_id:
                raise RuntimeError(f"Filter created with unexpected ID: {returned_id}")
            existing.add(item_id)
            print(f"Created native Qlik filter: {label} ({item_id})")

        after = child_ids(qix, pane)
        needed = {d["id"] for d in definitions}
        if not needed.issubset(after):
            raise RuntimeError("One or more listboxes were not persisted in filterpane")
        qix.call(doc, "DoSave")
        print(f"QIX filterpane verified: {len(needed)} native listboxes saved.")
    finally:
        qix.close()


if __name__ == "__main__":
    main()
