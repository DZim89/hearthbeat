"""Dispatcher — pure code between "approved plan" and Firestore. No model here.

Re-runs the SAME policy check the loop used (belt and suspenders: if the loop
exhausted its iterations without converging, only individually-clean actions
get through). Writes:

  pending_actions/{run_id}:{sha8}   status=approved            (normal path)
  pending_actions/{run_id}:{sha8}   status=awaiting_approval   (sensitive path)
  permission_slips/{run_id}:{sha8}  status=pending             (sensitive path)

The house's action poller is the only thing that executes anything, and it
re-validates against the same policy file a third time. Doc ids are content
hashes created with Firestore create() — a resumed or re-fired run can never
duplicate an action.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator

from google.api_core import exceptions as gexc
from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.cloud import firestore

from app import ledger
from app.policy import load_policy
from app.policy_gate import _as_dict
from app.stores import ACTIONS, SLIPS, db


def _action_id(run_id: str, action: dict[str, Any]) -> str:
    canon = json.dumps(action, sort_keys=True, separators=(",", ":"), default=str)
    return f"{run_id}:{hashlib.sha256(canon.encode()).hexdigest()[:8]}"


class Dispatcher(BaseAgent):
    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        run_id = state.get("run_id", "unknown")
        policy = load_policy(os.environ.get("POLICY_FILE", "config/policy.yaml"))
        plan = _as_dict(state.get("day_plan"))
        actions = [a for a in plan.get("actions", []) if isinstance(a, dict)]
        now = datetime.now(policy.tz)
        active = ledger.ACTIVE

        dispatched: list[str] = []
        denials: list[dict[str, Any]] = []
        for i, action in enumerate(actions):
            violations = policy.check_action(action, now=now)
            if violations:
                for rule in violations:
                    denials.append(
                        {
                            "stage": "dispatch",
                            "action_index": i,
                            "rule": rule,
                            "detail": f"{action.get('action_type')} -> {action.get('entity')}",
                        }
                    )
                    if active:
                        active.emit_public(
                            "policy_denial",
                            stage="dispatch",
                            rule=rule,
                            action_index=i,
                            detail=str(action.get("action_type")),
                        )
                continue

            spec = policy.action_spec(str(action["action_type"])) or {}
            sensitive = bool(action.get("sensitive")) or (
                action.get("entity") in spec.get("sensitive_targets", [])
            )
            aid = _action_id(run_id, action)
            doc = {
                "run_id": run_id,
                "action": action,
                "ha_domain": spec.get("ha_domain", ""),
                "ha_service": spec.get("ha_service", ""),
                "status": "awaiting_approval" if sensitive else "approved",
                "sensitive": sensitive,
                "created_at": firestore.SERVER_TIMESTAMP,
                "attempts": 0,
            }
            try:
                db().collection(ACTIONS).document(aid).create(doc)
            except gexc.AlreadyExists:
                dispatched.append(aid)  # resume: already written, never duplicated
                continue
            if sensitive:
                try:
                    db().collection(SLIPS).document(aid).create(
                        {
                            "run_id": run_id,
                            "action_id": aid,
                            "action_type": action.get("action_type"),
                            "target": action.get("entity"),
                            "message": action.get("message", ""),
                            "why": action.get("why", ""),
                            "status": "pending",
                            "created_at": firestore.SERVER_TIMESTAMP,
                        }
                    )
                except gexc.AlreadyExists:
                    pass
            dispatched.append(aid)
            if active:
                active.emit_public(
                    "action_dispatched",
                    action_id=aid,
                    action_type=str(action.get("action_type")),
                    sensitive=sensitive,
                    status=doc["status"],
                )

        try:
            from app import runcontrol

            runcontrol.record_plan(run_id, plan, dispatched)
            if denials:
                runcontrol.add_denials(run_id, denials)
        except Exception as e:  # noqa: BLE001
            print(f"[dispatcher] run doc update failed: {e}")

        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"dispatched": dispatched}),
        )
