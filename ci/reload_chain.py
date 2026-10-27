#!/usr/bin/env python3
"""Run only explicitly requested Qlik Cloud reloads, in app-lineage order.

REST /api/v1/reloads jobs are asynchronous: do NOT enqueue a dependent
reload until the previous job is SUCCEEDED. Stop on all other terminal states.
No app reload is ever started by this module on a Git push (deploy-only).
"""
from __future__ import annotations

import json
import os
import time
from urllib.parse import quote

SUCCESS = "SUCCEEDED"
ACTIVE = {"QUEUED", "RELOADING", "CANCELING", "CREATED"}
FAILURE = {"FAILED", "CANCELED", "EXCEEDED_LIMIT"}
MAX_WAIT_SECONDS = 840


def reload_one(app_key: str, app_id: str, rest, *,
               sleep=time.sleep, clock=time.monotonic,
               max_wait: float=MAX_WAIT_SECONDS, poll_seconds: float=5) -> dict:
    if not app_id:
        raise ValueError(f"{app_key}: missing Qlik application ID")
    response = rest("POST", "/api/v1/reloads", {"appId": app_id, "partial": False})
    reload_id = response.get("id")
    if not reload_id or not isinstance(reload_id, str):
        raise RuntimeError(f"{app_key}: reload API returned no job ID; will not queue downstream")
    print(f"RELOAD STARTED [{app_key}] job={reload_id} app={app_id}", flush=True)
    deadline=clock()+max_wait
    while True:
        status = rest("GET", "/api/v1/reloads/" + quote(reload_id, safe=""))
        result = status.get("status")
        if result == SUCCESS:
            print(f"RELOAD VERIFIED [{app_key}] SUCCEEDED job={reload_id}", flush=True)
            return {"app":app_key,"appId":app_id,"reloadId":reload_id,"status":SUCCESS}
        if result in FAILURE:
            detail = status.get("errorMessage") or status.get("errorCode") or ""
            raise RuntimeError(f"{app_key}: reload {reload_id} ended {result}: {str(detail)[:500]}")
        if result not in ACTIVE:
            raise RuntimeError(f"{app_key}: reload {reload_id} returned unknown state {result!r}")
        if clock()>=deadline:
            raise TimeoutError(
                f"{app_key}: reload {reload_id} not completed after {max_wait}s; "
                "downstream apps NOT reloaded. Check Qlik reload history."
            )
        sleep(poll_seconds)


def run_chain(apps: dict, keys: list[str], rest, *,
              execute_reload=reload_one) -> list[dict]:
    if len(keys)!=len(set(keys)):
        raise ValueError("Duplicate application in reload plan")
    result=[]
    for key in keys:
        if key not in apps:
            raise ValueError(f"App not part of approved graph: {key}")
        # On the first failure, do not enqueue any downstream reload.
        item=execute_reload(key, apps[key]["appId"], rest)
        result.append(item)
    print("RELOAD CHAIN SUCCESS: " + " -> ".join(keys),flush=True)
    return result
