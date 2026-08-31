"""Run lifecycle: date-keyed idempotency, heartbeat, stage checkpoints, resume.

    runs/{YYYY-MM-DD}                       claim doc (create() precondition)
    runs/{YYYY-MM-DD}/checkpoints/{stage}   state slice per completed stage

A re-fired run: done -> 200 noop · running w/ fresh heartbeat -> 409 ·
stale/failed -> takeover, rebuild the pipeline from the UNfinished stages only,
seed session state from the checkpoints. Actions are content-hash create()'d,
so even a full re-dispatch cannot duplicate them.
"""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

from google.adk.apps import App
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.api_core import exceptions as gexc
from google.cloud import firestore
from google.genai import types as genai_types

from app import ledger
from app.agent import STAGE_AGENTS, STAGE_ORDER, build_pipeline
from app.ledger import LedgerPlugin
from app.policy import load_policy
from app.stores import RUNS, db

HEARTBEAT_STALE_SECONDS = int(os.environ.get("HEARTBEAT_STALE_SECONDS", "600"))

STAGE_STATE_KEYS = {
    "gathered": ["home_state", "calendar", "school_mail", "energy"],
    "planned": ["day_plan"],
    "reviewed": ["day_plan", "critique", "plan_hash", "policy_findings", "policy_approved"],
    "dispatched": ["dispatched"],
}
_AGENT_TO_STAGE = {v: k for k, v in STAGE_AGENTS.items()}


def today_run_id() -> str:
    tz = load_policy(os.environ.get("POLICY_FILE", "config/policy.yaml")).tz
    return datetime.now(tz).strftime("%Y-%m-%d")


def _run_ref(run_id: str):
    return db().collection(RUNS).document(run_id)


def claim_run(run_id: str, trigger_source: str, triggered_by: str) -> dict[str, Any]:
    ref = _run_ref(run_id)
    try:
        ref.create(
            {
                "status": "running",
                "trigger_source": trigger_source,
                "triggered_by": triggered_by,
                "attempt": 1,
                "heartbeat_at": firestore.SERVER_TIMESTAMP,
                "started_at": firestore.SERVER_TIMESTAMP,
                "stage_status": {},
                "denials": [],
            }
        )
        return {"claimed": True, "attempt": 1}
    except gexc.AlreadyExists:
        data = ref.get().to_dict() or {}
        if data.get("status") == "done":
            return {"claimed": False, "noop": "already_completed"}
        hb = data.get("heartbeat_at")
        fresh = (
            hb is not None
            and (datetime.now(timezone.utc) - hb).total_seconds() < HEARTBEAT_STALE_SECONDS
        )
        if data.get("status") == "running" and fresh:
            return {"claimed": False, "noop": "in_progress"}
        ref.update(
            {
                "status": "running",
                "attempt": firestore.Increment(1),
                "heartbeat_at": firestore.SERVER_TIMESTAMP,
                "resume_trigger_source": trigger_source,
            }
        )
        return {"claimed": True, "attempt": int(data.get("attempt", 1)) + 1, "resumed": True}


def load_checkpoints(run_id: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for snap in _run_ref(run_id).collection("checkpoints").get():
        out[snap.id] = (snap.to_dict() or {}).get("state", {})
    return out


def on_agent_complete(run_id: str, agent_name: str, callback_context) -> None:
    """Ledger-plugin hook: checkpoint after each top-level stage + heartbeat."""
    stage = _AGENT_TO_STAGE.get(agent_name)
    if stage is None:
        _run_ref(run_id).update({"heartbeat_at": firestore.SERVER_TIMESTAMP})
        return
    state = callback_context.state
    payload = {k: state.get(k) for k in STAGE_STATE_KEYS[stage] if state.get(k) is not None}
    _run_ref(run_id).collection("checkpoints").document(stage).set(
        {"state": payload, "at": firestore.SERVER_TIMESTAMP}
    )
    _run_ref(run_id).update(
        {
            f"stage_status.{stage}": "done",
            "heartbeat_at": firestore.SERVER_TIMESTAMP,
        }
    )


def add_denials(run_id: str, rows: list[dict[str, Any]]) -> None:
    stamped = [{**r, "at": datetime.now(timezone.utc).isoformat()} for r in rows]
    _run_ref(run_id).update({"denials": firestore.ArrayUnion(stamped)})


def record_plan(run_id: str, plan: dict[str, Any], dispatched: list[str]) -> None:
    _run_ref(run_id).update(
        {
            "summary": str(plan.get("summary", ""))[:2000],
            "briefing_md": str(plan.get("briefing_md", ""))[:8000],
            "actions_planned": len(plan.get("actions", [])),
            "actions_dispatched": dispatched,
        }
    )


async def execute_run(
    run_id: str | None = None,
    *,
    trigger_source: str,
    triggered_by: str = "",
    red_team: bool = False,
) -> dict[str, Any]:
    run_id = run_id or today_run_id()
    claim = claim_run(run_id, trigger_source, triggered_by)
    if not claim.get("claimed"):
        return {"run_id": run_id, **claim}

    checkpoints = load_checkpoints(run_id)
    done_stages = set(checkpoints)
    plugin = LedgerPlugin(run_id, trigger_source)
    ledger.ACTIVE = plugin
    try:
        root = build_pipeline(done_stages)
        adk_app = App(name="app", root_agent=root, plugins=[plugin])
        sessions = InMemorySessionService()
        seed: dict[str, Any] = {
            "run_id": run_id,
            "trigger_source": trigger_source,
            "red_team": red_team,
        }
        for stage in STAGE_ORDER:
            seed.update(checkpoints.get(stage, {}))
        await sessions.create_session(
            app_name="app", user_id="house", session_id=run_id, state=seed
        )
        runner = Runner(app=adk_app, session_service=sessions)
        message = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=f"Execute the household morning run {run_id}.")],
        )
        async for _event in runner.run_async(
            user_id="house", session_id=run_id, new_message=message
        ):
            pass

        cost = ledger.RUN_COST_MICROCENTS.get(run_id, 0)
        _run_ref(run_id).update(
            {
                "status": "done",
                "finished_at": firestore.SERVER_TIMESTAMP,
                "heartbeat_at": firestore.SERVER_TIMESTAMP,
                "cost_microcents": cost,
                "egress": {
                    "checks": plugin.egress_checks,
                    "matches": plugin.egress_matches,
                },
            }
        )
        return {
            "run_id": run_id,
            "status": "done",
            "attempt": claim.get("attempt", 1),
            "resumed_from": sorted(done_stages) or None,
            "cost_cents": round(cost / 1_000_000, 4),
            "trigger_source": trigger_source,
        }
    except Exception as e:
        plugin.emit_public("run_failed", error=str(e)[:300])
        plugin.sink.flush()
        try:
            _run_ref(run_id).update({"status": "failed", "error": str(e)[:500]})
        except Exception:  # noqa: BLE001
            pass
        raise
    finally:
        if ledger.ACTIVE is plugin:
            ledger.ACTIVE = None
