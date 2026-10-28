#!/usr/bin/env python3
"""Governed master dimensions and app variables across Presentation apps.

The managed catalog is authoritative for subscribed objects only. Unassigned
objects are retained centrally. Existing unrelated native objects are untouched.
"""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
import subprocess

from model_registry import active_model

ROOT = Path(__file__).resolve().parents[1]
MODEL = active_model()
DIMENSIONS = MODEL.catalog("dimensions")
VARIABLES = MODEL.catalog("variables")


def definitions(path: Path, key: str) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schemaVersion") != 1:
        raise ValueError(f"{path}: expected versioned semantic catalog")
    items = data.get(key)
    if not isinstance(items, list):
        raise ValueError(f"{path}: missing {key}")
    result = {}
    for item in items:
        ident = item.get("id")
        if not isinstance(ident, str) or not re.fullmatch(r"qlikgpt_(d_|v_)[a-z0-9_]+", ident):
            raise ValueError(f"Bad dimension/variable ID {ident!r}")
        if ident in result:
            raise ValueError(f"Duplicate {key} ID {ident}")
        if not isinstance(item.get("version"), str) or not item["version"]:
            raise ValueError(f"{ident}: missing version")
        if key == "dimensions":
            if not item["id"].startswith("qlikgpt_d_"):
                raise ValueError(f"Non dimension identifier {ident}")
            fields = item.get("fields")
            if not isinstance(fields, list) or not fields or any(not isinstance(f, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", f) for f in fields):
                raise ValueError(f"{ident}: invalid fields")
            if not isinstance(item.get("labels"), list) or len(item["labels"]) != len(fields):
                raise ValueError(f"{ident}: labels must match fields")
            if not isinstance(item.get("title"), str) or not item["title"]:
                raise ValueError(f"{ident}: title required")
        else:
            if not item["id"].startswith("qlikgpt_v_"):
                raise ValueError(f"Non variable identifier {ident}")
            if not isinstance(item.get("name"), str) or not re.fullmatch(r"vQlikGPT[A-Za-z0-9_]+", item["name"]):
                raise ValueError(f"{ident}: variable name must use vQlikGPT namespace")
            if not isinstance(item.get("definition"), str) or len(item["definition"]) > 2000 or "\n" in item["definition"]:
                raise ValueError(f"{ident}: invalid definition")
        if not isinstance(item.get("description"), str):
            raise ValueError(f"{ident}: description required")
        result[ident] = item
    if key == "variables":
        names = [item["name"] for item in items]
        if len(names) != len(set(names)):
            raise ValueError("Duplicate Qlik variable names")
    return result


def catalogs() -> tuple[dict, dict]:
    return definitions(DIMENSIONS, "dimensions"), definitions(VARIABLES, "variables")


def validate_subscriptions(manifests: dict, dimensions: dict, variables: dict) -> None:
    for app_key, manifest in manifests.items():
        for prop, values in (("catalogDimensions", dimensions), ("catalogVariables", variables)):
            refs = manifest.get(prop)
            if not isinstance(refs, list) or any(not isinstance(x, str) for x in refs):
                raise ValueError(f"{app_key}: {prop} must be array of IDs")
            if len(refs) != len(set(refs)):
                raise ValueError(f"{app_key}: duplicate {prop}")
            if set(refs) - set(values):
                raise ValueError(f"{app_key}: unknown {prop}: {sorted(set(refs)-set(values))}")


def dimension_properties(item: dict) -> dict:
    return {
        "qInfo": {"qId": item["id"], "qType": "dimension"},
        "qDim": {
            "qGrouping": "N", "qFieldDefs": list(item["fields"]),
            "qFieldLabels": list(item["labels"]),
        },
        "qMetaDef": {
            "title": item["title"],
            "description": item["description"],
            "tags": ["Semantic Catalog", "Governed"],
        },
    }


def variable_properties(item: dict) -> dict:
    return {
        "qInfo": {"qId": item["id"], "qType": "variable"},
        "qName": item["name"],
        "qComment": item["description"],
        "qDefinition": item["definition"],
    }


def current(qix, doc: int, kind: str, ident: str):
    method = "GetDimension" if kind == "dimensions" else "GetVariableById"
    response = qix.call(doc, method, {"qId": ident})
    handle = response.get("qReturn", {}).get("qHandle")
    return (handle, qix.call(handle, "GetProperties", [])["qProp"]) if handle is not None else (None, None)


def mismatch(props: dict | None, expected: dict, kind: str) -> list[str]:
    if props is None:
        return ["missing"]
    if kind == "dimensions":
        keys = {
            "qDim.qGrouping": (props.get("qDim", {}).get("qGrouping"), expected["qDim"]["qGrouping"]),
            "qDim.qFieldDefs": (props.get("qDim", {}).get("qFieldDefs"), expected["qDim"]["qFieldDefs"]),
            "qDim.qFieldLabels": (props.get("qDim", {}).get("qFieldLabels"), expected["qDim"]["qFieldLabels"]),
            "title": (props.get("qMetaDef", {}).get("title"), expected["qMetaDef"]["title"]),
            "description": (props.get("qMetaDef", {}).get("description"), expected["qMetaDef"]["description"]),
        }
    else:
        keys = {key:(props.get(key), expected[key])
                for key in ("qName", "qComment", "qDefinition")}
    return [key for key, (a, b) in keys.items() if a != b]


def apply(qix, doc: int, app_key: str, kind: str, items: dict,
          subscribed: list, changes: list) -> None:
    for ident in subscribed:
        item = items[ident]
        desired = dimension_properties(item) if kind == "dimensions" else variable_properties(item)
        if kind == "dimensions":
            for field in item["fields"]:
                found = qix.call(doc, "GetField", {"qFieldName": field})
                if found.get("qReturn", {}).get("qHandle") is None:
                    raise RuntimeError(f"{app_key}: missing field {field} for {ident}")
        handle, prior = current(qix, doc, kind, ident)
        differences = mismatch(prior, desired, kind)
        if differences:
            if handle is None:
                method = "CreateDimension" if kind == "dimensions" else "CreateVariableEx"
                created = qix.call(doc, method, {"qProp": desired})
                handle = created.get("qReturn", {}).get("qHandle")
                if handle is None:
                    raise RuntimeError(f"{app_key}: unable to create {kind}/{ident}")
                changes.append((qix, doc, kind, ident, None))
                print(f"ASSET [{app_key}] CREATED {kind}/{ident}", flush=True)
            else:
                changed = deepcopy(prior)
                if kind == "dimensions":
                    changed["qDim"].update(desired["qDim"])
                    changed["qMetaDef"] = desired["qMetaDef"]
                else:
                    changed.update({k:v for k,v in desired.items() if k != "qInfo"})
                changes.append((qix, doc, kind, ident, deepcopy(prior)))
                qix.call(handle, "SetProperties", [changed])
                print(f"ASSET [{app_key}] UPDATED {kind}/{ident}: {differences}", flush=True)
        _, readback = current(qix, doc, kind, ident)
        if mismatch(readback, desired, kind):
            raise RuntimeError(f"{app_key}: readback differs: {kind}/{ident}")
        print(f"ASSET [{app_key}] VERIFIED {kind}/{ident}", flush=True)


def drift(qix, doc: int, manifest: dict, dims: dict, variables: dict) -> list[str]:
    result = []
    for kind, items, field in (("dimensions",dims,"catalogDimensions"),
                               ("variables",variables,"catalogVariables")):
        for ident in manifest[field]:
            _, props = current(qix, doc, kind, ident)
            goal = dimension_properties(items[ident]) if kind == "dimensions" else variable_properties(items[ident])
            if mismatch(props, goal, kind):
                result.append(f"{kind}/{ident}")
    return result


def changed_definitions(path: str, kind: str, current_defs: dict) -> set[str]:
    try:
        raw = subprocess.check_output(["git", "show", "HEAD^:" + path], cwd=ROOT,
                                      stderr=subprocess.DEVNULL, text=True)
        old = {m["id"]:m for m in json.loads(raw)[kind]}
        return {ident for ident,item in current_defs.items() if old.get(ident) != item}
    except (OSError, subprocess.CalledProcessError, KeyError, ValueError, TypeError):
        return set(current_defs)


def impacted(manifests: dict, paths: set[str], dims: dict, variables: dict) -> set[str]:
    # Only changed catalog definitions affect subscribed apps. Adding an unused
    # dimension or variable does not force unrelated apps to deploy.
    affected = set()
    for path,kind,field,values in (
        (DIMENSIONS.relative_to(ROOT).as_posix(), "dimensions", "catalogDimensions", dims),
        (VARIABLES.relative_to(ROOT).as_posix(), "variables", "catalogVariables", variables),
    ):
        if path in paths:
            diff = changed_definitions(path, kind, values)
            for app,manifest in manifests.items():
                if diff.intersection(manifest[field]):
                    affected.add(app)
    return affected


def rollback(changes: list) -> None:
    for qix,doc,kind,ident,old in reversed(changes):
        try:
            handle,_=current(qix,doc,kind,ident)
            if old is None:
                method = "DestroyDimension" if kind == "dimensions" else "DestroyVariableById"
                qix.call(doc, method, {"qId":ident})
            elif handle is not None:
                qix.call(handle,"SetProperties",[old])
            qix.call(doc,"DoSave",[])
        except Exception as exc:
            print(f"WARNING: asset rollback manual intervention {ident}: {exc}", flush=True)
