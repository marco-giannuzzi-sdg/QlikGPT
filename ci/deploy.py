#!/usr/bin/env python3
"""Qlik Cloud GitHub Actions deployment. Never runs on the user's PC."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import time
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest
import sys
import uuid

from model_registry import active_model

ROOT = Path(__file__).resolve().parents[1]
MODEL = active_model()
STATE_PATH = MODEL.state_path
TENANT = os.environ.get("QLIK_TENANT", "").rstrip("/")
SPACE_ID = os.environ.get("QLIK_SPACE_ID", "").strip()

APPS = MODEL.etl_apps() + tuple(
    (key, json.loads(path.read_text(encoding="utf-8"))["appName"], MODEL.presentation_script)
    for key, path in MODEL.presentation_manifests().items() if key == "presentation"
)


def run(*arguments: str) -> str:
    # shell=False avoids shell expansion and quoting issues.
    cmd = ["qlik", *arguments]
    print("+", " ".join(cmd), flush=True)
    result = subprocess.run(
        cmd, cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.stdout:
        print(result.stdout, flush=True)
    if result.stderr:
        print(result.stderr, file=sys.stderr, flush=True)
    if result.returncode != 0:
        raise RuntimeError("Qlik command failed (exit %s): %s" % (result.returncode, cmd[:3]))
    return result.stdout.strip()


def persist(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")


def valid_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False


def qlik_rest(method: str, resource: str, payload: dict | None = None) -> dict:
    """Call official Qlik REST API; the token never appears in logs or command args."""
    token = os.environ.get("QLIK_API_KEY", "")
    if not token:
        raise RuntimeError("QLIK_API_KEY GitHub secret is missing")
    if not resource.startswith("/api/v1/"):
        raise ValueError("Only Qlik API paths are permitted")
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urlrequest.Request(
        TENANT + resource,
        data=data,
        method=method,
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
    )
    try:
        with urlrequest.urlopen(request, timeout=35) as response:
            raw = response.read()
            return json.loads(raw) if raw.strip() else {}
    except urlerror.HTTPError as exc:
        response_body = exc.read().decode("utf-8", errors="replace")[:1500]
        raise RuntimeError(
            f"Qlik REST {method} {resource.split('?')[0]} returned HTTP "
            f"{exc.code}: {response_body}"
        ) from None


def find_existing_owned_app(name: str) -> str | None:
    """Reuse only an exact-name app owned by this identity in the target space."""
    me = qlik_rest("GET", "/api/v1/users/me")
    user_id = me.get("id")
    if not user_id:
        raise RuntimeError("Cannot resolve owner ID via Qlik users/me")

    search = urlparse.urlencode({
        "resourceType": "app",
        "name": name,
        "ownerId": user_id,
        "spaceId": SPACE_ID or "personal",
        "limit": 100,
        "noActions": "true",
    })
    response = qlik_rest("GET", "/api/v1/items?" + search)
    apps = [
        item for item in response.get("data", [])
        if item.get("name") == name
        and item.get("resourceType") == "app"
        and item.get("ownerId") == user_id
    ]
    if len(apps) > 1:
        raise RuntimeError(
            f"More than one owned app named {name!r} found in the target space; "
            "refusing to choose or create another"
        )
    if not apps:
        return None
    app_id = apps[0].get("resourceId")
    if not valid_uuid(app_id):
        raise RuntimeError(f"Existing app {name!r} has an invalid resourceId")
    return app_id


def ensure_app(state: dict, kind: str, name: str) -> str:
    app_id = state.get(kind, "")
    if app_id:
        if not valid_uuid(app_id):
            raise ValueError(f"Invalid saved App ID for {kind}")
        run("app", "get", app_id)
        print(f"Reusing {name}: {app_id}", flush=True)
        return app_id

    # This lookup prevents duplicates if Qlik CLI previously failed while
    # parsing a response after the server created the app.
    existing = find_existing_owned_app(name)
    if existing:
        run("app", "get", existing)
        state[kind] = existing
        persist(state)
        print(f"Recovered existing {name}: {existing}", flush=True)
        return existing

    attributes = {
        "name": name,
        "usage": "ANALYTICS",
        "description": "QlikGPT GitHub CI/CD - " + kind,
    }
    if SPACE_ID:
        attributes["spaceId"] = SPACE_ID

    print(f"Creating {name} via official Qlik REST API...", flush=True)
    result = qlik_rest("POST", "/api/v1/apps", {"attributes": attributes})
    app_id = result.get("attributes", {}).get("id") or result.get("id")

    # Defensive recovery: if Qlik accepted the request but did not return
    # a usable JSON ID, DO NOT send another create request.
    if not valid_uuid(app_id):
        for pause in (1, 2, 3):
            time.sleep(pause)
            app_id = find_existing_owned_app(name)
            if app_id:
                break
    if not valid_uuid(app_id):
        raise RuntimeError(
            f"Qlik create request for {name!r} did not return an App ID; "
            "do not retry without checking Qlik Cloud"
        )

    run("app", "get", app_id)
    state[kind] = app_id
    persist(state)
    print(f"Created {name}: {app_id}", flush=True)
    return app_id


def nonempty_json_array(relative: str) -> bool:
    file = ROOT / relative
    if not file.exists():
        return False
    parsed = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(parsed, list):
        raise ValueError(f"{relative} must contain a JSON array")
    return bool(parsed)


def validate_frontend(app_id: str) -> None:
    """Round-trip the Presentation app through Qlik CLI to confirm persisted objects."""
    # Dynamic: expected catalog measures + all native objects and dimensions
    # declared in the app manifest. No fixed list of legacy master items.
    manifest = json.loads((MODEL.presentation_manifests()["presentation"]).read_text())
    sheets = json.loads((ROOT / manifest["dashboardSource"]).read_text())
    filters = json.loads((ROOT / manifest["filterSource"]).read_text())
    expected_ids = set(manifest["catalogMeasures"])
    expected_ids.update(manifest["catalogDimensions"])
    for sheet in sheets:
        expected_ids.add(sheet["qInfo"]["qId"])
        expected_ids.update(child["qInfo"]["qId"]
                            for child in sheet.get("qChildren", []))
    expected_ids.update(f["id"] for f in filters)


    ids: set[str] = set()
    with tempfile.TemporaryDirectory(prefix="qlikgpt-audit-") as directory:
        output = Path(directory) / "extracted"
        run("app", "unbuild", "--app", app_id, "--dir", str(output))

        def scan(value: object) -> None:
            if isinstance(value, dict):
                info = value.get("qInfo", {})
                if isinstance(info, dict) and isinstance(info.get("qId"), str):
                    ids.add(info["qId"])
                for child in value.values():
                    scan(child)
            elif isinstance(value, list):
                for child in value:
                    scan(child)

        json_files = list(output.rglob("*.json"))
        if not json_files:
            raise RuntimeError("Qlik unbuild returned no JSON objects")
        for file in json_files:
            scan(json.loads(file.read_text(encoding="utf-8")))

    missing = expected_ids - ids
    print(
        f"Frontend persistence check: found {len(ids & expected_ids)}/"
        f"{len(expected_ids)} expected object IDs", flush=True
    )
    if missing:
        raise RuntimeError(
            "Qlik app is missing these native UI objects: " + ", ".join(sorted(missing))
        )

def main() -> None:
    if not TENANT:
        raise RuntimeError("QLIK_TENANT not configured")
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
    else:
        state = {}
    if not isinstance(state, dict):
        raise TypeError("State must be a JSON object")
    state.setdefault("tenant", TENANT)
    if state["tenant"].rstrip("/") != TENANT:
        raise RuntimeError("Saved App IDs belong to another Qlik tenant")
    saved_space = state.get("spaceId", "")
    if any(state.get(kind) for kind, _, _ in APPS) and saved_space != SPACE_ID:
        raise RuntimeError("Saved apps belong to a different space")
    state["spaceId"] = SPACE_ID

    for kind, name, _script in APPS:
        ensure_app(state, kind, name)
    persist(state)

    # HARD GUARANTEE: no commit to GitHub ever implicitly reloads an
    # existing application. Manual modes must explicitly request it.
    operation = os.environ.get("QLIK_DEPLOY_OPERATION", "deploy-only")
    target_app = os.environ.get("QLIK_DEPLOY_TARGET", "").strip()
    event = os.environ.get("GITHUB_EVENT_NAME", "push")
    if event != "workflow_dispatch" and operation != "deploy-only":
        raise ValueError("Data reload requires explicit GitHub workflow_dispatch")
    if event == "push" and target_app:
        raise ValueError("A Git push cannot specify a reload/deployment target")

    from semantic_catalog import orchestrate_semantic_catalog, changed_paths
    from app_lineage import build as build_lineage, registry as app_registry
    from deployment_plan import plan as create_plan, describe as describe_plan
    from reload_chain import run_chain
    files_changed = changed_paths()

    # Master items and visuals are synchronized without a data reload.
    # The existing bootstrap of a *brand-new* Presentation is intentionally
    # handled separately in the semantic orchestrator.
    orchestrate_semantic_catalog(
        state, run=run, ensure_app=ensure_app, persist=persist, scope="frontend"
    )

    graph = build_lineage(app_registry())
    execution = create_plan(graph, files_changed, operation, target_app)
    print(describe_plan(execution), flush=True)
    for key in execution["scripts"]:
        app = graph["apps"][key]
        if not app.get("appId"):
            raise RuntimeError(f"{key}: missing registered Qlik App ID")
        path = app["script"]
        # Moving a QVS file without changing its contents must not rewrite Qlik.
        from deploy_visuals import Qix
        expected = (ROOT / path).read_text(encoding="utf-8")
        normalize = lambda value: value.replace("\r\n", "\n").strip() if isinstance(value, str) else None
        check_existing = Qix(state[key])
        try:
            current_doc = check_existing.call(-1, "OpenDoc", {"qDocName":state[key]})["qReturn"]["qHandle"]
            current_script = check_existing.call(current_doc, "GetScript", []).get("qScript")
        finally:
            check_existing.close()
        if normalize(current_script) == normalize(expected):
            print(f"SCRIPT UNCHANGED [{key}]: path relocated, Qlik write skipped", flush=True)
        else:
            print(f"DEPLOY SCRIPT ONLY [{key}] {path} (NO DATA RELOAD)", flush=True)
            run("app", "build", "--app", state[key], "--script", path, "--no-reload")

        # A separate QIX readback validates the currently persisted script.
        check = Qix(state[key])
        try:
            doc = check.call(-1, "OpenDoc", {"qDocName":state[key]})["qReturn"]["qHandle"]
            actual = check.call(doc, "GetScript", []).get("qScript")
            expected = (ROOT / path).read_text(encoding="utf-8")
            norm = lambda x: x.replace("\r\n", "\n").strip() if isinstance(x, str) else None
            if norm(actual) != norm(expected):
                raise RuntimeError(f"{key}: persisted Qlik script differs from GitHub {path}")
            print(f"SCRIPT VERIFIED [{key}]: QIX GetScript matches GitHub",flush=True)
        finally:
            check.close()
    if not execution["reloads"]:
        print("DATA RELOADS: 0 (deploy-only)", flush=True)

    # A catalog-only commit deploys ONLY to the subscribed apps.
    # Rebuild the original Sales Overview only when its own frontend or CI changes.
    refresh_p1_frontend = (
        not files_changed or
        any(path.startswith((f"{MODEL.prefix}/apps/presentation1", "ci/", ".github/", "ui/"))
            for path in files_changed)
    )
    if refresh_p1_frontend:
        # Central master dimensions and variables are provisioned by QIX.
        # Qlik CLI does not fully materialize nested sheet children.
        subprocess.run(
            [sys.executable, "ci/deploy_visuals.py", state["presentation"]],
            cwd=ROOT, check=True,
        )
        validate_frontend(state["presentation"])
        # Once every dashboard KPI/chart is QIX-linked to a catalog measure,
        # remove only the four known unused PoC master-item duplicates.
        from semantic_catalog import prune_unsubscribed_measures, read_json, CATALOG
        from deploy_visuals import Qix
        catalog = read_json(CATALOG)
        subscriptions = set(read_json(MODEL.presentation_manifests()["presentation"])["catalogMeasures"])
        qix = Qix(state["presentation"])
        try:
            doc = qix.call(-1, "OpenDoc",
                           {"qDocName": state["presentation"]})["qReturn"]["qHandle"]
            prune_unsubscribed_measures(
                qix, doc, "presentation", {m["id"] for m in catalog["measures"]},
                subscriptions, legacy=True
            )
        finally:
            qix.close()

    else:
        print("Skipping Presentation 1 frontend: catalog/manifests-only change.", flush=True)
    # Reloads are a separate, explicitly opted-in workflow operation.
    # REST status is checked before enqueueing the next dependent app.
    if execution["reloads"]:
        print(f"EXPLICIT DATA RELOAD: {operation} target={target_app}", flush=True)
        run_chain(graph["apps"], execution["reloads"], qlik_rest)

    print("=== Presentation Count(OrderID) ===", flush=True)
    run("app", "eval", "Count(OrderID)", "--app", state["presentation"])
    print(f"Presentation app: {TENANT}/sense/app/{state['presentation']}", flush=True)


if __name__ == "__main__":
    main()
