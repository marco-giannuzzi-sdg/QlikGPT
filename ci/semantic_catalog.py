#!/usr/bin/env python3
"""Git-governed Qlik master measures for multiple Presentation apps.

The catalog and app manifests are source-of-truth. Engine QIX APIs create,
update, read back, and evaluate shared measures. No local workstation.
No implicit deletion of existing master items.
"""
from __future__ import annotations

from copy import deepcopy
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Callable

from deploy_visuals import Qix, find_child

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "catalog" / "measures.json"
FORMATTING = ROOT / "catalog" / "formatting.json"
# Additional apps are onboarded by adding apps/presentation3.json,
# apps/presentation3-objects.json, etc. No Python routing table to edit.
MANIFESTS = {
    ("presentation" if p.stem == "presentation1" else p.stem): p
    for p in sorted((ROOT / "apps").glob("presentation*.json"))
    if re.fullmatch(r"presentation[0-9]+\.json", p.name)
}
ALLOWED_FIELDS = {"Revenue", "Margin", "Cost", "OrderID", "Quantity", "Market",
                  "OrderDate", "Channel", "CustomerID", "SalesYear"}


def read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must be a JSON object")
    return data


def formatting_contract() -> dict:
    """Return versioned Italian number-format and semantic-color presets."""
    config = read_json(FORMATTING)
    if config.get("schemaVersion") != 1 or config.get("locale") != "it-IT":
        raise ValueError("Unsupported semantic formatting contract")
    presets, palette = config.get("presets"), config.get("palette")
    if not isinstance(presets, dict) or not presets or not isinstance(palette, dict):
        raise ValueError("Formatting contract requires presets and palette")
    for name, fmt in presets.items():
        if not isinstance(fmt, dict) or set(fmt) != {
            "qType", "qnDec", "qUseThou", "qFmt", "qDec", "qThou"
        }:
            raise ValueError(f"Malformed QIX format preset: {name}")
        if fmt["qType"] not in ("M", "I", "F") or not isinstance(fmt["qnDec"], int) or not 0 <= fmt["qnDec"] <= 15:
            raise ValueError(f"Invalid QIX type/decimals: {name}")
        if fmt["qUseThou"] not in (0, 1) or not fmt["qFmt"]:
            raise ValueError(f"Invalid grouping or pattern: {name}")
        if fmt["qDec"] != "," or fmt["qThou"] != ".":
            raise ValueError(f"Preset {name} must use Italian decimal and thousands separators")
        if fmt["qUseThou"] and "." not in fmt["qFmt"]:
            raise ValueError(f"Preset {name} must show thousands grouping in qFmt")
        if fmt["qnDec"] and fmt["qFmt"].count(",") != 1:
            raise ValueError(f"Preset {name} needs an Italian decimal point in qFmt")
        if not fmt["qnDec"] and "," in fmt["qFmt"]:
            raise ValueError(f"Integer preset {name} must not have decimals")
        if fmt["qType"] == "M" and "€" not in fmt["qFmt"]:
            raise ValueError(f"EUR preset {name} must contain a currency symbol")
    for role, color in palette.items():
        if not isinstance(color, str) or not re.fullmatch(r"#[0-9A-Fa-f]{6}", color):
            raise ValueError(f"Invalid semantic color {role}: {color!r}")
    for key, cfg in config.get("compactPresets", {}).items():
        if (not isinstance(cfg, dict) or not isinstance(cfg.get("scale"), (int, float))
                or cfg["scale"] <= 0 or not isinstance(cfg.get("decimals"), int)
                or not 0 <= cfg["decimals"] <= 4
                or not isinstance(cfg.get("prefix"), str)
                or not isinstance(cfg.get("suffix"), str)):
            raise ValueError(f"Invalid optional compact format preset: {key}")
    return config


def metric_style(item: dict) -> dict:
    """Resolve authoritative full-precision QIX format and semantic color."""
    settings = formatting_contract()
    return {
        "format": deepcopy(settings["presets"][item["formatPreset"]]),
        "color": settings["palette"][item["colorRole"]],
    }


QIX_FORMAT_KEYS = ("qType", "qnDec", "qUseThou", "qFmt", "qDec", "qThou")


def comparison_fields(measure_props: dict) -> dict:
    """Read back the complete effective Qlik master-item formatting contract."""
    m = measure_props.get("qMeasure", {})
    meta = measure_props.get("qMetaDef", {})
    fmt = m.get("qNumFormat", {})
    coloring = m.get("coloring", {})
    return {
        "expression": m.get("qDef"), "title": m.get("qLabel"),
        "format": {key: fmt.get(key) for key in QIX_FORMAT_KEYS},
        "color": coloring.get("baseColor", {}).get("color"),
        "description": meta.get("description"),
        "tags": meta.get("tags", []),
    }


def expected_fields(item: dict) -> dict:
    resolved = metric_style(item)
    return {
        "expression": item["expression"], "title": item["title"],
        "format": resolved["format"], "color": resolved["color"],
        "description": item["description"], "tags": item["tags"],
    }


def format_differences(actual: dict, item: dict) -> list[str]:
    expected = expected_fields(item)
    found = comparison_fields(actual)
    return [key for key in expected if found[key] != expected[key]]


def validate_catalog(catalog: dict, manifests: dict) -> dict:
    if catalog.get("schemaVersion") != 1:
        raise ValueError("Unsupported semantic catalog schemaVersion")
    definitions = catalog.get("measures")
    if not isinstance(definitions, list) or not definitions:
        raise ValueError("Catalog requires a nonempty measures array")
    by_id = {}
    formatting = formatting_contract()
    for item in definitions:
        if not isinstance(item, dict):
            raise ValueError("Catalog measure must be an object")
        measure_id = item.get("id", "")
        if not isinstance(measure_id, str) or not re.fullmatch(r"qlikgpt_shared_[a-z0-9_]+", measure_id):
            raise ValueError(f"Invalid or non-namespaced shared metric ID: {measure_id}")
        if measure_id in by_id:
            raise ValueError(f"Duplicate shared metric ID: {measure_id}")
        for field in ("title", "expression", "description", "version"):
            if not isinstance(item.get(field), str) or not item[field].strip():
                raise ValueError(f"{measure_id}: {field} must be a nonempty string")
        expr = item["expression"]
        if len(expr) > 1200 or ";" in expr or "\n" in expr or "\r" in expr:
            raise ValueError(f"{measure_id}: invalid/multiline expression")
        fields = item.get("requiredFields")
        if not isinstance(fields, list) or not fields or any(
            not isinstance(f, str) or f not in ALLOWED_FIELDS for f in fields
        ):
            raise ValueError(f"{measure_id}: unsupported or empty requiredFields")
        if item.get("formatPreset") not in formatting["presets"]:
            raise ValueError(f"{measure_id}: unknown formatPreset")
        if item.get("colorRole") not in formatting["palette"]:
            raise ValueError(f"{measure_id}: unknown semantic colorRole")
        if "compactFormatPreset" in item and item["compactFormatPreset"] not in formatting.get("compactPresets", {}):
            raise ValueError(f"{measure_id}: unknown compactFormatPreset")
        if "format" in item:
            raise ValueError(f"{measure_id}: inline number format forbidden; use formatPreset")
        if not isinstance(item.get("tags"), list):
            raise ValueError(f"{measure_id}: tags must be an array")
        by_id[measure_id] = item

    for app_key, manifest in manifests.items():
        if manifest.get("appKey") != app_key:
            raise ValueError(f"Manifest appKey must equal {app_key}")
        refs = manifest.get("catalogMeasures")
        if not isinstance(refs, list) or len(refs) != len(set(refs)):
            raise ValueError(f"{app_key}: duplicate or invalid subscriptions")
        missing = set(refs) - set(by_id)
        if missing:
            raise ValueError(f"{app_key}: unknown subscribed measures: {sorted(missing)}")
        if not manifest.get("loadScript") == "scripts/presentation.qvs":
            raise ValueError(f"{app_key}: unapproved loadScript")
        suffix = "1" if app_key == "presentation" else app_key.removeprefix("presentation")
        expected_dashboard = f"apps/presentation{suffix}-objects.json"
        if manifest.get("dashboardSource") != expected_dashboard:
            raise ValueError(f"{app_key}: dashboardSource must be {expected_dashboard}")
        if not isinstance(manifest.get("appName"), str) or not manifest["appName"]:
            raise ValueError(f"{app_key}: missing appName")
        if "filterSource" in manifest and not (ROOT / manifest["filterSource"]).exists():
            raise ValueError(f"{app_key}: missing filterSource")
        if "dimensionSource" in manifest and not (ROOT / manifest["dimensionSource"]).exists():
            raise ValueError(f"{app_key}: missing dimensionSource")
    # Every KPI/chart measure must be an approved catalog subscription. This
    # forbids private JSON/inline master-measure definitions in both apps.
    for app_key, manifest in manifests.items():
        visuals = json.loads((ROOT / manifest["dashboardSource"]).read_text())
        for sheet in visuals:
            for child in sheet.get("qChildren", []):
                if child.get("qInfo", {}).get("qType") == "measure":
                    raise ValueError(f"{app_key}: master measures belong in catalog")
                for item in child.get("qHyperCubeDef", {}).get("qMeasures", []):
                    mid = item.get("qLibraryId")
                    if not mid or mid not in manifest["catalogMeasures"]:
                        raise ValueError(
                            f"{app_key}: visual {child.get('qInfo',{}).get('qId')} "
                            "has inline measure or missing catalog subscription"
                        )
    return by_id


def changed_paths() -> set[str]:
    try:
        output = subprocess.check_output(
            ["git", "diff", "--name-only", "HEAD^", "HEAD"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        )
        return set(output.splitlines())
    except (OSError, subprocess.CalledProcessError):
        return set()  # On a shallow/manual run, use the safe full-sync fallback.


def changed_metric_ids(current: dict) -> set[str]:
    """Diff the canonical measure definitions using git history."""
    try:
        old_data = subprocess.check_output(
            ["git", "show", "HEAD^:catalog/measures.json"],
            cwd=ROOT, text=True, stderr=subprocess.DEVNULL,
        )
        previous = json.loads(old_data)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        return set(current)
    old_by_id = {m["id"]: m for m in previous.get("measures", [])}
    return {mid for mid, definition in current.items()
            if old_by_id.get(mid) != definition}


def determine_impacted(catalog: dict, manifests: dict, changed: set[str],
                       full: bool, new_app: bool) -> set[str]:
    if full or new_app or not changed:
        return set(manifests)
    affected = set()
    if "catalog/formatting.json" in changed:
        affected |= set(manifests)
    if "catalog/measures.json" in changed:
        modified = changed_metric_ids(catalog)
        affected |= {key for key, manifest in manifests.items()
                     if modified.intersection(manifest["catalogMeasures"])}
    for key, manifest in manifests.items():
        suffix = "1" if key == "presentation" else key.removeprefix("presentation")
        candidates = {
            f"apps/presentation{suffix}.json", manifest["dashboardSource"],
            manifest.get("filterSource"), manifest.get("dimensionSource"),
        }
        if any(p in changed for p in candidates if p):
            affected.add(key)
    if any(path.startswith("ci/") or path.startswith(".github/") for path in changed):
        affected |= set(manifests)
    return affected


def qix_metric_properties(item: dict) -> dict:
    style = metric_style(item)
    return {
        "qInfo": {"qId": item["id"], "qType": "measure"},
        "qMeasure": {
            "qLabel": item["title"],
            "qDef": item["expression"],
            "qGrouping": "N",
            "qNumFormat": style["format"],
            "coloring": {"baseColor": {"color": style["color"], "index": -1}},
            "isCustomFormatted": True,
            "numFormatFromTemplate": False,
        },
        "qMetaDef": {
            "title": item["title"],
            "description": item["description"],
            "tags": list(item["tags"]),
        },
    }


def actual_measure(qix: Qix, doc: int, measure_id: str) -> tuple[int | None, dict | None]:
    response = qix.call(doc, "GetMeasure", {"qId": measure_id})
    handle = response.get("qReturn", {}).get("qHandle")
    if handle is None:
        return None, None
    return handle, qix.call(handle, "GetProperties", [])["qProp"]


LEGACY_APP1_IDS = {
    "qlikgpt_m_revenue",
    "qlikgpt_m_orders",
    "qlikgpt_m_margin",
    "qlikgpt_m_margin_pct",
}


def prune_unsubscribed_measures(qix: Qix, doc: int, app_key: str,
                                all_catalog_ids: set[str],
                                subscriptions: set[str],
                                *, legacy: bool = False) -> None:
    """Conservative removal: only catalog-owned or four known PoC legacy IDs.

    Never remove a measure that QIX reports as linked to any native object.
    A future unassigned metric stays in Git and is provisioned on subscription.
    """
    candidates = all_catalog_ids - subscriptions
    if legacy:
        candidates |= LEGACY_APP1_IDS
    deleted = []
    for mid in sorted(candidates):
        handle, _props = actual_measure(qix, doc, mid)
        if handle is None:
            continue
        links = qix.call(handle, "GetLinkedObjects", [])
        if links.get("qItems", []):
            raise RuntimeError(
                f"[{app_key}] REFUSING deletion of referenced measure {mid}: "
                f"{len(links['qItems'])} Qlik-linked objects"
            )
        result = qix.call(doc, "DestroyMeasure", {"qId": mid})
        if not result.get("qSuccess", False):
            raise RuntimeError(f"[{app_key}] failed to delete inactive measure {mid}")
        check, _ = actual_measure(qix, doc, mid)
        if check is not None:
            raise RuntimeError(f"[{app_key}] inactive measure still exists after deletion: {mid}")
        deleted.append(mid)
    if deleted:
        qix.call(doc, "DoSave", [])
    print(f"[{app_key}] catalog reconciliation: removed {len(deleted)} inactive/legacy measures: {deleted}", flush=True)


def detect_catalog_drift(state: dict, manifests: dict,
                         definitions: dict) -> set[str]:
    """Read-only reconciliation. Catch changes missed by a previous failed CI run.

    Git diff is an optimization, not proof that Qlik is already synchronized.
    """
    drift = set()
    for app_key, manifest in manifests.items():
        qix = Qix(state[app_key])
        try:
            doc = qix.call(-1, "OpenDoc",
                           {"qDocName": state[app_key]})["qReturn"]["qHandle"]
            subscribed = set(manifest["catalogMeasures"])
            for mid in sorted(subscribed):
                _handle, props = actual_measure(qix, doc, mid)
                definition = definitions[mid]
                if props is None:
                    drift.add(app_key)
                    print(f"DRIFT [{app_key}]: missing {mid}", flush=True)
                    break
                mismatches = format_differences(props, definition)
                if mismatches:
                    drift.add(app_key)
                    print(f"DRIFT [{app_key}]: {mid} differs in {mismatches}", flush=True)
                    break
            if app_key not in drift:
                for mid in definitions.keys() - subscribed:
                    handle, _ = actual_measure(qix, doc, mid)
                    if handle is not None:
                        drift.add(app_key)
                        print(f"DRIFT [{app_key}]: unsubscribed metric {mid} still installed", flush=True)
                        break
        finally:
            qix.close()
    return drift


def validate_required_fields(qix: Qix, doc: int, item: dict) -> None:
    for field in item["requiredFields"]:
        lookup = qix.call(doc, "GetField", {"qFieldName": field})
        if lookup.get("qReturn", {}).get("qHandle") is None:
            raise RuntimeError(
                f"Data contract mismatch: field {field!r} absent for {item['id']}"
            )


def sync_one(qix: Qix, doc: int, appkey: str, item: dict, changes: list) -> None:
    wanted = qix_metric_properties(item)
    mid = item["id"]
    validate_required_fields(qix, doc, item)
    handle, previous = actual_measure(qix, doc, mid)
    if handle is None:
        result = qix.call(doc, "CreateMeasure", {"qProp": wanted})
        handle = result.get("qReturn", {}).get("qHandle")
        if handle is None:
            raise RuntimeError(f"CreateMeasure failed for {mid}")
        changes.append((qix, doc, mid, None))
        print(f"[{appkey}] CREATED {mid}", flush=True)
    else:
        if not format_differences(previous, item):
            print(f"[{appkey}] unchanged {mid}", flush=True)
        else:
            changes.append((qix, doc, mid, deepcopy(previous)))
            updated = deepcopy(previous)
            updated["qMeasure"].update(wanted["qMeasure"])
            updated["qMetaDef"] = wanted["qMetaDef"]
            qix.call(handle, "SetProperties", [updated])
            print(f"[{appkey}] UPDATED {mid}: {item['expression']}", flush=True)

    # Read-back is mandatory. A successful write call alone is not sufficient.
    check_handle, check_props = actual_measure(qix, doc, mid)
    if check_handle is None:
        raise RuntimeError(f"[{appkey}] {mid} missing after sync")
    differences = format_differences(check_props, item)
    if differences:
        raise RuntimeError(f"[{appkey}] {mid} failed QIX properties read-back: {differences}")
    style = metric_style(item)
    print(
        f"[{appkey}] VERIFIED {mid}: expression={item['expression']}, "
        f"format={style['format']['qFmt']}, decimal={style['format']['qDec']}, "
        f"thousands={style['format']['qThou']}, color={style['color']}",
        flush=True
    )


def rollback(changes: list) -> None:
    # Best-effort multi-app compensation; Qlik has no global transaction here.
    for qix, doc, mid, old_props in reversed(changes):
        try:
            handle, _ = actual_measure(qix, doc, mid)
            if old_props is None:
                qix.call(doc, "DestroyMeasure", {"qId": mid})
            elif handle is not None:
                qix.call(handle, "SetProperties", [old_props])
            qix.call(doc, "DoSave", [])
            print(f"ROLLBACK compensated {mid}", flush=True)
        except Exception as exc:
            print(f"WARNING: manual rollback required for {mid}: {exc}", flush=True)


def deploy_governed_sheets(qix: Qix, doc: int, manifest: dict) -> None:
    definitions = json.loads(
        (ROOT / manifest["dashboardSource"]).read_text(encoding="utf-8")
    )
    if len(definitions) != 1:
        raise ValueError("One governed sheet per demo Presentation is supported")
    props = definitions[0]
    sheet_id = props["qInfo"]["qId"]
    opened = qix.call(doc, "GetObject", {"qId": sheet_id})
    sheet = opened.get("qReturn", {}).get("qHandle")
    if sheet is None:
        created = qix.call(doc, "CreateObject", {"qProp": {k:v for k,v in props.items() if k != "qChildren"}})
        sheet = created.get("qReturn", {}).get("qHandle")
        if sheet is None:
            raise RuntimeError("Unable to create native Qlik sheet")
    else:
        # Update sheet grid and header without discarding existing native children.
        old = qix.call(sheet, "GetProperties", [])["qProp"]
        changed = deepcopy(old)
        changed.update({k:v for k,v in props.items() if k not in {"qChildren", "qInfo"}})
        qix.call(sheet, "SetProperties", [changed])

    for child in props["qChildren"]:
        cid = child["qInfo"]["qId"]
        h = find_child(qix, sheet, cid)
        if h is None:
            created = qix.call(sheet, "CreateChild", [child])
            h = created.get("qReturn", {}).get("qHandle")
            if h is None:
                raise RuntimeError(f"Unable to create native linked KPI {cid}")
        else:
            qix.call(h, "SetProperties", [child])
        layout = qix.call(h, "GetLayout", [])["qLayout"]
        cube = layout.get("qHyperCube", {})
        measure_id = child["qHyperCubeDef"]["qMeasures"][0]["qLibraryId"]
        props_read = qix.call(h, "GetProperties", [])["qProp"]
        ref = props_read["qHyperCubeDef"]["qMeasures"][0].get("qLibraryId")
        if ref != measure_id or cube.get("qSize", {}).get("qcy", 0) < 1:
            raise RuntimeError(f"Native KPI {cid} did not bind to master measure {measure_id}")
        print(f"[{manifest['appKey']}] KPI {cid} linked to qLibraryId={measure_id}", flush=True)


def orchestrate_semantic_catalog(state: dict, *, run: Callable,
                                 ensure_app: Callable, persist: Callable,
                                 scope: str) -> None:
    catalog = read_json(CATALOG)
    manifests = {key: read_json(path) for key, path in MANIFESTS.items()}
    definitions = validate_catalog(catalog, manifests)  # no side effects
    changed = changed_paths()

    new_apps = set()
    # First Presentation is already created/reloaded by the ETL orchestrator.
    # Discover and provision every additional manifest-driven Presentation.
    for key, manifest in sorted(manifests.items()):
        if key == "presentation":
            continue
        if not state.get(key):
            new_apps.add(key)
        app_id = ensure_app(state, key, manifest["appName"])
        persist(state)
        if key in new_apps or scope == "full":
            print(f"=== Deploying {key} model from transformed QVD ===", flush=True)
            run("app", "build", "--app", app_id, "--script",
                manifest["loadScript"])

    impacted = determine_impacted(
        definitions, manifests, changed, full=(scope == "full"),
        new_app=bool(new_apps)
    )
    # Recover pending changes even when the last commit only changes tests
    # or documentation following a failed deployment.
    if scope != "full":
        impacted |= detect_catalog_drift(state, manifests, definitions)
    print(f"SEMANTIC-CATALOG impacted={sorted(impacted)} "
          f"changed={sorted(changed)}", flush=True)
    if not impacted:
        return

    connections: list[tuple[Qix, int]] = []
    changes: list = []
    try:
        for key in sorted(impacted):
            qix = Qix(state[key])
            doc = qix.call(-1, "OpenDoc", {"qDocName": state[key]})["qReturn"]["qHandle"]
            connections.append((qix, doc))
            for mid in manifests[key]["catalogMeasures"]:
                sync_one(qix, doc, key, definitions[mid], changes)
            if key != "presentation":
                deploy_governed_sheets(qix, doc, manifests[key])
        for qix, doc in connections:
            qix.call(doc, "DoSave", [])
        # Validate all subscribed expressions from independent Engine sessions.
        for key in sorted(impacted):
            audit = Qix(state[key])
            try:
                doc = audit.call(-1, "OpenDoc", {"qDocName": state[key]})["qReturn"]["qHandle"]
                for mid in manifests[key]["catalogMeasures"]:
                    _, props = actual_measure(audit, doc, mid)
                    if not props:
                        raise RuntimeError(f"{key}: missing persisted measure {mid}")
                    differences = format_differences(props, definitions[mid])
                    if differences:
                        raise RuntimeError(f"{key}: persisted measure {mid} differs from catalog: {differences}")
                    # Engine evaluation confirms the formula is calculable in each app.
                    run("app", "eval", definitions[mid]["expression"], "--app", state[key])
                prune_unsubscribed_measures(
                    audit, doc, key, set(definitions),
                    set(manifests[key]["catalogMeasures"])
                )
            finally:
                audit.close()
        print("SEMANTIC-CATALOG SUCCESS: impacted apps synchronized and audited", flush=True)
    except Exception:
        rollback(changes)
        raise
    finally:
        for qix, _doc in connections:
            qix.close()
