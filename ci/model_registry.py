"""Discover the QlikGPT semantic models and their versioned asset roots.

All paths in model.json are relative to that model directory. Presentation
manifest paths remain repo-relative for compatibility with Qlik CLI.
This is a schema registry, not a second source of truth for Qlik App IDs.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "semantic-models"


class Model:
    def __init__(self, path: Path):
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", path.name):
            raise ValueError(f"Invalid semantic model directory {path}")
        self.root = path
        self.prefix = path.relative_to(ROOT).as_posix()
        self.data = json.loads((path / "model.json").read_text(encoding="utf-8"))
        if self.data.get("schemaVersion") != 1 or self.data.get("modelId") != path.name:
            raise ValueError(f"Invalid model identity at {path}")
        self.id = path.name
        self.name = self.data.get("name", path.name)
        self.state_path = self.resolve(self.data["appIds"])
        self.presentation_script_path = self.resolve(self.data["presentationScript"])
        self.presentation_script = self.repo_path(self.presentation_script_path)
        if not isinstance(self.data.get("etlApplications"), list):
            raise ValueError(f"{self.id}: etlApplications must be a list")
        for record in self.data["etlApplications"]:
            if not record.get("appKey") or not record.get("appName"):
                raise ValueError(f"{self.id}: invalid ETL application")
            self.resolve(record["loadScript"])
        for filename in ("measures", "dimensions", "variables", "formatting"):
            self.catalog(filename)
        if not self.presentation_manifests():
            raise ValueError(f"{self.id}: at least one Presentation manifest required")

    def resolve(self, value: str) -> Path:
        if not isinstance(value, str) or not value or value.startswith("/"):
            raise ValueError(f"{self.id}: invalid relative path: {value!r}")
        target = (self.root / value).resolve()
        if self.root.resolve() not in target.parents:
            raise ValueError(f"{self.id}: path escapes semantic model: {value}")
        if not target.is_file():
            raise ValueError(f"{self.id}: missing asset: {value}")
        return target

    @staticmethod
    def repo_path(path: Path) -> str:
        return path.relative_to(ROOT).as_posix()

    def catalog(self, kind: str) -> Path:
        return self.resolve(self.data["catalog"][kind])

    def presentation_manifests(self) -> dict[str, Path]:
        out = {}
        for name in self.data["presentations"]:
            if not re.fullmatch(r"presentation[0-9]+", name):
                raise ValueError(f"{self.id}: unexpected presentation name {name}")
            path = self.resolve("apps/" + name + ".json")
            manifest = json.loads(path.read_text(encoding="utf-8"))
            key = manifest.get("appKey")
            if not isinstance(key, str) or key in out:
                raise ValueError(f"{self.id}: duplicate/invalid appKey in {path}")
            out[key] = path
        return out

    def etl_apps(self) -> tuple[tuple[str, str, str], ...]:
        return tuple(
            (item["appKey"], item["appName"],
             self.repo_path(self.resolve(item["loadScript"])))
            for item in self.data["etlApplications"]
        )


def discover_models() -> dict[str, Model]:
    if not MODELS_DIR.is_dir():
        raise RuntimeError("semantic-models directory not present")
    items = {p.name: Model(p) for p in sorted(MODELS_DIR.iterdir())
             if p.is_dir() and (p / "model.json").is_file()}
    if not items:
        raise RuntimeError("No semantic models registered")
    all_keys = [
        key for model in items.values()
        for key in [x[0] for x in model.etl_apps()] + list(model.presentation_manifests())
    ]
    if len(all_keys) != len(set(all_keys)):
        raise ValueError("Duplicate application keys across semantic models")
    return items


def active_model() -> Model:
    # The existing deployment contract targets a single model per run.
    # A future multi-model workflow can dispatch one model ID per job.
    model_id = os.environ.get("QLIK_MODEL_ID", "sales")
    models = discover_models()
    if model_id not in models:
        raise ValueError(f"Unknown semantic model {model_id!r}; available: {sorted(models)}")
    return models[model_id]
