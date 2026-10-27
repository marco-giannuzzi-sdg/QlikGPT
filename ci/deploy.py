#!/usr/bin/env python3
"""Qlik Cloud GitHub Actions deployment. Never runs on the user's PC."""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
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


def ensure_app(state: dict, kind: str, name: str) -> str:
    previous_id = state.get(kind, "")
    if previous_id:
        if not valid_uuid(previous_id):
            raise ValueError(f"Invalid saved App ID for {kind}")
        # Never silently create duplicates if access/tenant changed.
        run("app", "get", previous_id)
        print(f"Reusing {name}: {previous_id}", flush=True)
        return previous_id

    command = [
        "app", "create", "--attributes-name", name,
        "--attributes-usage", "ANALYTICS",
        "--attributes-description", "QlikGPT GitHub CI/CD - " + kind,
        "--quiet",
    ]
    if SPACE_ID:
        command.extend(["--attributes-spaceId", SPACE_ID])
    output = run(*command)
    matches = re.findall(
        r"\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b",
        output,
    )
    if not matches:
        raise RuntimeError("Creation command did not return a UUID for " + name)
    app_id = matches[-1]
    run("app", "get", app_id)
    state[kind] = app_id
    persist(state)  # record each successful create immediately
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


def deploy_frontend(app_id: str) -> None:
    # The frontend lives as versioned JSON, and is applied ONLY to Presentation.
    # Empty [] means "not designed yet", rather than deleting user objects.
    types = (
        ("dimensions", "frontend/dimensions.json"),
        ("measures", "frontend/measures.json"),
        ("objects", "frontend/objects.json"),
    )
    options = []
    for flag, path in types:
        if nonempty_json_array(path):
            options.extend([f"--{flag}", path])
    if not options:
        print("No frontend definitions yet. Skipping sheet/chart deployment.")
        return
    run("app", "build", "--app", app_id, "--no-reload", *options)
    print("Frontend JSON applied to the Presentation app.")


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
    if saved_space and saved_space != SPACE_ID:
        raise RuntimeError("Saved apps belong to a different space")
    state["spaceId"] = SPACE_ID

    for kind, name, _script in APPS:
        ensure_app(state, kind, name)
    persist(state)

    # Do not switch app ownership or silently target a production app.
    for kind, name, script in APPS:
        print(f"=== Deploying {name} ===", flush=True)
        run("app", "build", "--app", state[kind], "--script", script)

    deploy_frontend(state["presentation"])
    print("=== Presentation Count(OrderID) ===", flush=True)
    run("app", "eval", "Count(OrderID)", "--app", state["presentation"])
    print(f"Presentation app: {TENANT}/sense/app/{state['presentation']}", flush=True)


if __name__ == "__main__":
    main()
