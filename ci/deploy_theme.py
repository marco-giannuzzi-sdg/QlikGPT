#!/usr/bin/env python3
"""Publish the versioned QlikGPT theme using qlik-cli and bind it via QIX.

The existing GitHub Actions runner holds QLIK_API_KEY in a secret. This script
does not need a reload or touch any ETL, measures, dimensions or sheet objects.
Only the registered Presentation is bound by default.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import zipfile

from model_registry import ROOT, active_model

THEME_DIR = ROOT / "ui" / "themes" / "qlikgpt-executive-v1"
THEME_FILE = THEME_DIR / "theme.json"
QEXT_FILE = THEME_DIR / "qlikgpt-executive-v1.qext"
TOKENS_FILE = ROOT / "ui" / "design-tokens.json"
MODEL = active_model()


def contract() -> tuple[str, str]:
    tokens = json.loads(TOKENS_FILE.read_text(encoding="utf-8"))
    qext = json.loads(QEXT_FILE.read_text(encoding="utf-8"))
    theme = json.loads(THEME_FILE.read_text(encoding="utf-8"))
    slug = tokens["templateId"]
    if qext.get("type") != "theme" or qext.get("name") != slug:
        raise ValueError("QEXT theme identity does not match UI design tokens")
    if qext.get("version") != tokens.get("version"):
        raise ValueError("QEXT version does not match UI design tokens")
    for var, role in (
        ("@qlikgpt-navy", "navy"),
        ("@qlikgpt-teal", "teal"),
        ("@qlikgpt-blue", "blue"),
    ):
        if theme["_variables"].get(var) != tokens["colors"][role]:
            raise ValueError(f"Theme color is not synchronized: {var}")
    return slug, qext["version"]


def build_archive(target: Path) -> None:
    """Only QEXT + theme.json, both at the ZIP root, no extra files."""
    with zipfile.ZipFile(target, mode="w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(QEXT_FILE, arcname=QEXT_FILE.name)
        archive.write(THEME_FILE, arcname="theme.json")
    with zipfile.ZipFile(target) as archive:
        assert set(archive.namelist()) == {QEXT_FILE.name, "theme.json"}
        assert archive.testzip() is None


def qlik(*args: str) -> str:
    result = subprocess.run(
        ["qlik", *args], capture_output=True, text=True, check=False
    )
    if result.returncode:
        # Do not print environment or access tokens to Actions logs.
        raise RuntimeError(f"qlik {' '.join(args[:3])} failed with exit code {result.returncode}")
    return result.stdout.strip()


def list_themes(output: str) -> list[dict]:
    value = json.loads(output)
    if isinstance(value, list):
        values = value
    elif isinstance(value, dict) and isinstance(value.get("data"), list):
        values = value["data"]
    else:
        raise ValueError("Unexpected Qlik CLI theme list response")
    if not all(isinstance(v, dict) for v in values):
        raise ValueError("Unexpected theme record in Qlik response")
    return values


def find_theme(themes: list[dict], slug: str) -> dict | None:
    # Never update by human-readable display name; the QEXT identity is stable.
    matches = [
        theme for theme in themes
        if theme.get("qextFilename", "").removesuffix(".qext") == slug
    ]
    if len(matches) > 1:
        raise RuntimeError("Multiple themes with the same QEXT identity; refusing to patch")
    return matches[0] if matches else None


def publish_theme(slug: str, version: str, archive: Path) -> str:
    remote = find_theme(list_themes(qlik("theme", "ls", "--json")), slug)
    if remote is None:
        print(f"Theme not installed: creating {slug} version {version}", flush=True)
        qlik("theme", "create", "--file", str(archive), "--json")
    elif remote.get("qextVersion") != version:
        tid = remote.get("id")
        if not tid:
            raise RuntimeError("Existing Qlik theme has no stable ID")
        print(f"Updating theme {slug} to version {version}", flush=True)
        qlik("theme", "patch", tid, "--file", str(archive), "--json")
    else:
        print(f"Theme already installed with QEXT version {version}; no update needed", flush=True)

    installed = find_theme(list_themes(qlik("theme", "ls", "--json")), slug)
    if not installed or installed.get("qextVersion") != version:
        raise RuntimeError("Theme upload failed server-side version readback")
    if not installed.get("id"):
        raise RuntimeError("Theme upload has no server ID")
    print(f"THEME VERIFIED: {slug} / QEXT {version}", flush=True)
    return slug


def appprops_id(qix, doc: int) -> str:
    # Official Qlik Sense client object type: appprops, theme property = '/theme'.
    definition = {
        "qInfo": {"qType": "qlikgpt-theme-inspection"},
        "qAppObjectListDef": {"qType": "appprops", "qData": {"theme": "/theme"}},
    }
    response = qix.call(doc, "CreateSessionObject", {"qProp": definition})
    handle = response["qReturn"]["qHandle"]
    layout = qix.call(handle, "GetLayout", [])["qLayout"]
    items = layout.get("qAppObjectList", {}).get("qItems", [])
    if len(items) != 1:
        raise RuntimeError(
            "Qlik app must expose exactly one existing appprops object; "
            "will not invent or replace app properties"
        )
    obj_id = items[0].get("qInfo", {}).get("qId")
    if not obj_id:
        raise RuntimeError("App properties object has no ID")
    return obj_id


def apply_theme(app_id: str, slug: str) -> None:
    from deploy_visuals import Qix
    qix = Qix(app_id)
    try:
        doc = qix.call(-1, "OpenDoc", {"qDocName": app_id})["qReturn"]["qHandle"]
        obj_id = appprops_id(qix, doc)
        obj = qix.call(doc, "GetObject", {"qId": obj_id})["qReturn"]["qHandle"]
        before = qix.call(obj, "GetProperties", [])["qProp"]
        if before.get("theme") == slug:
            print(f"APP THEME ALREADY APPLIED: {app_id} => {slug}", flush=True)
            return
        updated = deepcopy(before)
        updated["theme"] = slug
        qix.call(obj, "SetProperties", [updated])
        qix.call(doc, "DoSave", [])
        persisted = qix.call(obj, "GetProperties", [])["qProp"]
        if persisted.get("theme") != slug:
            raise RuntimeError("QIX appprops.theme did not persist after DoSave")
        print(f"APP THEME APPLIED AND VERIFIED: {app_id} => {slug}", flush=True)
    finally:
        qix.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish/apply QlikGPT global theme without data reload")
    parser.add_argument("--apply-app", default="presentation",
                        help="One registered Presentation app key (default: presentation)")
    parser.add_argument("--package-only", action="store_true",
                        help="Validate and package local theme; no CLI, no Qlik writes")
    args = parser.parse_args()
    slug, version = contract()
    with tempfile.TemporaryDirectory(prefix="qlikgpt-theme-") as directory:
        archive = Path(directory) / f"{slug}.zip"
        build_archive(archive)
        print(f"Theme archive validated: {slug} v{version}", flush=True)
        if args.package_only:
            return
        state = json.loads(MODEL.state_path.read_text(encoding="utf-8"))
        if args.apply_app not in {"presentation", "presentation2"}:
            raise ValueError("Only the two registered demo Presentation apps are supported")
        if not state.get(args.apply_app):
            raise RuntimeError("Target app not registered in app-ids.json")
        publish_theme(slug, version, archive)
        apply_theme(state[args.apply_app], slug)


if __name__ == "__main__":
    main()
