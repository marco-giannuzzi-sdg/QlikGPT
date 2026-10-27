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

ROOT = Path(__file__).resolve().parents[1]
STATE_PATH = ROOT / "deployment" / "app-ids.json"
TENANT = os.environ.get("QLIK_TENANT", "").rstrip("/")
SPACE_ID = os.environ.get("QLIK_SPACE_ID", "").strip()

APPS = (
    ("etl1", "QlikGPT - 01 ETL RAW", "scripts/etl1.qvs"),
    ("etl2", "QlikGPT - 02 ETL TRANSFORM", "scripts/etl2.qvs"),
    ("presentation", "QlikGPT - 03 PRESENTATION", "scripts/presentation.qvs"),
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


def deploy_dimensions(app_id: str) -> None:
    # Master measures are never imported from local JSON: the Semantic Catalog
    # and QIX synchronize them for each app independently.
    path = "apps/presentation1-dimensions.json"
    if nonempty_json_array(path):
        run("app", "build", "--app", app_id, "--no-reload",
            "--dimensions", path)
        print("Presentation 1 dimensions synchronized.", flush=True)


def validate_frontend(app_id: str) -> None:
    """Round-trip the Presentation app through Qlik CLI to confirm persisted objects."""
    # Dynamic: expected catalog measures + all native objects and dimensions
    # declared in the app manifest. No fixed list of legacy master items.
    manifest = json.loads((ROOT / "apps/presentation1.json").read_text())
    sheets = json.loads((ROOT / manifest["dashboardSource"]).read_text())
    filters = json.loads((ROOT / manifest["filterSource"]).read_text())
    dimensions = json.loads((ROOT / manifest["dimensionSource"]).read_text())
    expected_ids = set(manifest["catalogMeasures"])
    expected_ids.update(d["qInfo"]["qId"] for d in dimensions)
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

    # Frontend-only commits must not regenerate synthetic orders.
    # This keeps sales KPI numbers stable while styling the Qlik dashboard.
    scope = os.environ.get("QLIK_DEPLOY_SCOPE", "full")
    if scope not in {"full", "frontend"}:
        raise ValueError("Unknown QLIK_DEPLOY_SCOPE: " + scope)
    if scope == "full":
        for kind, name, script in APPS:
            print(f"=== Deploying {name} ===", flush=True)
            run("app", "build", "--app", state[kind], "--script", script)
    else:
        print("Frontend-only deployment: retaining ETL1, ETL2 and Presentation data.", flush=True)

    # Multi-app governed master measures; creates second Presentation on first run.
    from semantic_catalog import orchestrate_semantic_catalog, changed_paths
    files_changed = changed_paths()
    orchestrate_semantic_catalog(
        state, run=run, ensure_app=ensure_app, persist=persist, scope=scope
    )

    # A catalog-only commit deploys ONLY to the subscribed apps.
    # Rebuild the original Sales Overview only when its own frontend or CI changes.
    refresh_p1_frontend = (
        scope == "full" or not files_changed or
        any(path.startswith(("apps/presentation1", "ci/", ".github/"))
            for path in files_changed)
    )
    if refresh_p1_frontend:
        deploy_dimensions(state["presentation"])
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
        subscriptions = set(read_json(ROOT / "apps/presentation1.json")["catalogMeasures"])
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
    print("=== Presentation Count(OrderID) ===", flush=True)
    run("app", "eval", "Count(OrderID)", "--app", state["presentation"])
    print(f"Presentation app: {TENANT}/sense/app/{state['presentation']}", flush=True)


if __name__ == "__main__":
    main()
