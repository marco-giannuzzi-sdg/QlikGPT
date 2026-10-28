#!/usr/bin/env python3
"""Deploy one namespaced extension and an additive pilot sheet. No model writes/reload."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
import urllib.request
import uuid
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SLUG = "qlikgpt-premium-overview"
SHEET = "qlikgpt_sales_premium"
CHILD = "qlikgpt_sales_premium_canvas"
APP = "07dfa926-4895-4fb2-af4c-eac90e9eb2cb"
MEASURES = ["qlikgpt_shared_revenue", "qlikgpt_shared_orders",
            "qlikgpt_shared_margin", "qlikgpt_shared_margin_pct"]
DIMENSIONS = ["qlikgpt_d_year", "qlikgpt_d_market", "qlikgpt_d_channel", "qlikgpt_d_yearmonth"]


def cube(measures, dimension=None):
    return {"qStateName": "$",
            "qDimensions": [{"qLibraryId": dimension, "qNullSuppression": True}] if dimension else [],
            "qMeasures": [{"qLibraryId": mid} for mid in measures],
            "qSuppressMissing": True, "qSuppressZero": False,
            "qInitialDataFetch": [{"qTop": 0, "qLeft": 0, "qWidth": len(measures) + bool(dimension),
                                   "qHeight": 100 if dimension else 1}]}


def archive_extension(directory: Path, output: Path):
    qext = json.loads((directory / (SLUG + ".qext")).read_text())
    if qext.get("supernova") is not True or qext.get("type") != "visualization":
        raise ValueError("Expected a packaged nebula supernova")
    if not (directory / (SLUG + ".js")).is_file():
        raise ValueError("Missing matching extension entry point")
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(directory.rglob("*")):
            if file.is_file():
                archive.write(file, file.relative_to(directory).as_posix())
    return qext


def rest(method, resource, archive=None):
    tenant = os.environ["QLIK_TENANT"].rstrip("/")
    if tenant != "https://sdggroup-it.eu.qlikcloud.com" or not resource.startswith("/api/v1/extensions"):
        raise ValueError("Unexpected extension deployment destination")
    headers = {"Authorization": "Bearer " + os.environ["QLIK_API_KEY"], "Accept": "application/json"}
    body = None
    if archive:
        boundary = "qlikgpt-" + uuid.uuid4().hex
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary
        body = (("--" + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' +
                 SLUG + '.zip"\r\nContent-Type: application/zip\r\n\r\n').encode() +
                archive.read_bytes() + ("\r\n--" + boundary + "--\r\n").encode())
    request = urllib.request.Request(tenant + resource, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=60) as response:
        data = response.read()
        return json.loads(data) if data.strip() else {}


def publish(archive, qext):
    records = rest("GET", "/api/v1/extensions").get("data", [])
    matches = [item for item in records if item.get("qextFilename", "").removesuffix(".qext") == SLUG]
    if len(matches) > 1:
        raise RuntimeError("Ambiguous extension identity")
    if matches:
        ident = matches[0]["id"]
        rest("PATCH", "/api/v1/extensions/" + ident, archive)
    else:
        rest("POST", "/api/v1/extensions", archive)
    installed = rest("GET", "/api/v1/extensions/" + SLUG)
    if installed.get("qextVersion") != qext["version"] or not installed.get("supernova"):
        raise RuntimeError("Extension metadata readback failed")
    print("EXTENSION VERIFIED:", SLUG, qext["version"], flush=True)


def protected_snapshot(qix, doc):
    result = {"script": qix.call(doc, "GetScript", []).get("qScript")}
    for method, ids, kind in (("GetMeasure", MEASURES, "measures"), ("GetDimension", DIMENSIONS, "dimensions")):
        result[kind] = {}
        for ident in ids:
            handle = qix.call(doc, method, {"qId": ident})["qReturn"]["qHandle"]
            if not isinstance(handle, int) or handle <= 0:
                raise RuntimeError("Required master item missing: " + ident)
            result[kind][ident] = qix.call(handle, "GetProperties", [])["qProp"]
    return result


def deploy(qix, doc):
    from deploy_visuals import find_child
    before = protected_snapshot(qix, doc)
    # Create/update only the additive pilot; the original Overview is untouched.
    listing = qix.call(doc, "CreateSessionObject", {"qProp": {
        "qInfo": {"qType": "qlikgpt-premium-sheet-list"},
        "qAppObjectListDef": {"qType": "sheet", "qData": {}}}})["qReturn"]["qHandle"]
    infos = qix.call(listing, "GetLayout", [])["qLayout"]["qAppObjectList"]["qItems"]
    exists = any(item["qInfo"]["qId"] == SHEET for item in infos)
    props = {"qInfo": {"qId": SHEET, "qType": "sheet"},
        "qMetaDef": {"title": "Sales Intelligence | Premium", "description": "Premium pilot, deployed from GitHub"},
        "title": "Sales Intelligence | Premium", "description": "QlikGPT code-managed nebula dashboard",
        "rank": -1, "columns": 24, "rows": 16, "gridMode": "edit",
        "qChildListDef": {"qData": {"id": "/qInfo/qId", "type": "/qInfo/qType", "title": "/title"}},
        "cells": [{"name": CHILD, "type": SLUG, "col": 0, "row": 0, "colspan": 24, "rowspan": 16,
                   "bounds": {"x": 0, "y": 0, "width": 100, "height": 100}}]}
    if exists:
        sheet = qix.call(doc, "GetObject", {"qId": SHEET})["qReturn"]["qHandle"]
        original = qix.call(sheet, "GetProperties", [])["qProp"]
        if original.get("description") != props["description"]:
            raise RuntimeError("Pilot sheet identity is not managed by this deployer")
        original.update({k: v for k, v in props.items() if k != "qInfo"})
        qix.call(sheet, "SetProperties", [original])
    else:
        sheet = qix.call(doc, "CreateObject", {"qProp": props})["qReturn"]["qHandle"]
    visual = {"qInfo": {"qId": CHILD, "qType": SLUG}, "qExtendsId": "",
              "visualization": SLUG, "showTitles": False, "title": "Sales Intelligence",
              "qHyperCubeDef": cube(MEASURES)}
    handle = find_child(qix, sheet, CHILD)
    if handle is None:
        handle = qix.call(sheet, "CreateChild", {"qProp": visual})["qReturn"]["qHandle"]
    else:
        qix.call(handle, "SetProperties", [visual])
    live = qix.call(handle, "GetProperties", [])["qProp"]
    if live["qHyperCubeDef"]["qMeasures"] != visual["qHyperCubeDef"]["qMeasures"]:
        raise RuntimeError("KPI master bindings did not persist")
    layout = qix.call(handle, "GetLayout", [])["qLayout"]
    values = layout.get("qHyperCube", {}).get("qDataPages", [{}])[0].get("qMatrix", [])
    if not values or len(values[0]) != 4 or any(cell.get("qIsNull") for cell in values[0]):
        raise RuntimeError("Four non-null governed KPI values required")
    # Query the same master-bound chart/filter definitions used by the renderer.
    for dimension in ("qlikgpt_d_yearmonth", "qlikgpt_d_market"):
        model = qix.call(doc, "CreateSessionObject", {"qProp": {
            "qInfo": {"qType": "qlikgpt-premium-audit"}, "qHyperCubeDef": cube([MEASURES[0]], dimension)}})["qReturn"]["qHandle"]
        chart = qix.call(model, "GetLayout", [])["qLayout"]["qHyperCube"]
        if chart.get("qError") or chart["qSize"]["qcy"] < 1:
            raise RuntimeError("Chart master binding returned no data")
        print("CHART MASTER VERIFIED:", dimension, "rows=", chart["qSize"]["qcy"], flush=True)
    if protected_snapshot(qix, doc) != before:
        raise RuntimeError("Protected semantic assets changed during presentation deploy")
    qix.call(doc, "DoSave", [])
    print("SEMANTIC SNAPSHOT UNCHANGED: script, 4 measures, 4 dimensions", flush=True)
    print("DATA RELOADS: 0. Original sheet preserved.", flush=True)


def main():
    from deploy_visuals import Qix
    registry = json.loads((ROOT / "semantic-models/sales/deployment/app-ids.json").read_text())
    if registry.get("presentation") != APP:
        raise RuntimeError("Pilot app registry changed; refusing an alternate app")
    directory = ROOT / "ui/premium/extension"
    archive = ROOT / "ui/premium/premium.zip"
    qext = archive_extension(directory, archive)
    publish(archive, qext)
    qix = Qix(APP)
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": APP})["qReturn"]["qHandle"]
        deploy(qix, doc)
    finally:
        qix.close()
    print("PILOT: " + registry["tenant"].rstrip("/") + "/sense/app/" + APP + "/sheet/" + SHEET + "/state/analysis")


if __name__ == "__main__":
    main()
