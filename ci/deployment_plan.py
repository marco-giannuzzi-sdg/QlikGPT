#!/usr/bin/env python3
"""Explicit QlikGPT deployment plan; never infer a data reload from a commit.

The script registry and dependency edges come from ci/app_lineage.py.
A script deploy is always --no-reload. Only workflow_dispatch choices
reload-app / reload-chain may request reload operations.
"""
from __future__ import annotations

from collections import deque

MODES = ("deploy-only", "reload-app", "reload-chain")


def topological_order(apps: dict, edges: list[dict], included: set[str]) -> list[str]:
    unknown = included - set(apps)
    if unknown:
        raise ValueError("Unknown application keys in execution plan: " + ", ".join(sorted(unknown)))
    incoming = {app: 0 for app in included}
    downstream = {app: set() for app in included}
    for edge in edges:
        up, down = edge["upstream"], edge["downstream"]
        if up in included and down in included and down not in downstream[up]:
            downstream[up].add(down)
            incoming[down] += 1
    ready = sorted(k for k, count in incoming.items() if count == 0)
    order = []
    while ready:
        key = ready.pop(0)
        order.append(key)
        for child in sorted(downstream[key]):
            incoming[child] -= 1
            if not incoming[child]:
                ready.append(child)
                ready.sort()
    if len(order) != len(included):
        raise ValueError("Cycle detected while ordering Qlik reload chain")
    return order


def plan(graph: dict, changed: set[str], mode: str, target: str = "") -> dict:
    if mode not in MODES:
        raise ValueError(f"Unknown Qlik deployment mode: {mode}")
    apps = graph["apps"]
    edges = graph["connections"]
    if mode == "deploy-only":
        if target:
            if target not in apps:
                raise ValueError(f"Unknown deployment target: {target}")
            selected = {target}
        else:
            # Shared QVS files, like shared model Presentation QVS, affect each
            # subscribed app. Other changes produce no script deployment.
            selected = {
                key for key, app in apps.items() if app["script"] in changed
            }
        script_keys = topological_order(apps, edges, selected)
        reload_keys: list[str] = []
    else:
        if not target or target not in apps:
            raise ValueError(
                f"{mode} requires a valid explicit target app (one of {list(apps)})"
            )
        included = {target}
        if mode == "reload-chain":
            included.update(graph["impact"][target]["transitive"])
        reload_keys = topological_order(apps, edges, included)
        # Ensure the selected scripts in GitHub are applied before any reload.
        script_keys = list(reload_keys)
    if set(reload_keys) - set(script_keys):
        raise ValueError("Reload requested without stage of its source script")
    result = {
        "operation": mode, "target": target or None,
        "scripts": script_keys, "reloads": reload_keys,
        "scriptPaths": {key: apps[key]["script"] for key in script_keys},
        "edges": edges,
    }
    return result


def describe(plan: dict) -> str:
    staged = ", ".join(plan["scripts"]) or "nessuna app"
    reloaded = " → ".join(plan["reloads"]) or "NESSUNO"
    return (
        f"QLIK DEPLOYMENT PLAN: {plan['operation']} | "
        f"scripts --no-reload: {staged} | "
        f"data reload order: {reloaded}"
    )
