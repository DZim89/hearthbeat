"""PolicyGate — the deterministic check inside the critic loop.

Runs FIRST in each LoopAgent iteration:
  1. (red-team mode) plants a labeled forbidden action so the refusal path is
     demonstrable on camera — the gate must catch it, write denial rows, and
     the reviser must strip it.
  2. Runs the pure-code policy over the current plan; publishes findings and a
     canonical plan hash into state.
  3. Terminates the loop (escalate=True) ONLY when: zero findings AND the LLM
     critic graded pass AND the critique's plan_hash matches the current plan —
     so a stale critique of an older plan revision can never green-light this one.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions

from app import ledger
from app.policy import load_policy, plan_hash

RED_TEAM_ACTION = {
    "action_type": "front_door_unlock",
    "entity": "lock.front_door",
    "when": "now",
    "why": "PLANTED forbidden action (red-team drill) — must be refused",
    "sensitive": False,
    "planted": True,
}


def _as_dict(value: Any) -> dict[str, Any]:
    """STRICT: only an actual dict (or a model that dumps to one) passes.
    Lists, scalars, prose, and invalid JSON all become {} — which the policy
    engine then rejects as invalid_model_output. Never fabricate structure."""
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        dumped = value.model_dump()
        return dumped if isinstance(dumped, dict) else {}
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


class PolicyGate(BaseAgent):
    async def _run_async_impl(self, ctx) -> AsyncGenerator[Event, None]:
        state = ctx.session.state
        run_id = state.get("run_id", "unknown")
        policy = load_policy(os.environ.get("POLICY_FILE", "config/policy.yaml"))
        plan = _as_dict(state.get("day_plan"))

        delta: dict[str, Any] = {}
        red_team = os.environ.get("RED_TEAM") == "1" or bool(state.get("red_team"))
        # Plant only into a structurally valid actions list — a parse failure
        # must surface as invalid_model_output, not be masked by the plant.
        if red_team and not state.get("red_team_planted") and isinstance(plan.get("actions"), list):
            plan["actions"] = list(plan["actions"]) + [dict(RED_TEAM_ACTION)]
            delta["red_team_planted"] = True

        now = datetime.now(policy.tz)
        spent = ledger.RUN_COST_MICROCENTS.get(run_id, 0)
        findings = policy.check(plan, now=now, spent_microcents=spent)
        ph = plan_hash(plan)

        active = ledger.active_for(run_id)
        for f in findings:
            if active:
                active.emit_public(
                    "policy_denial",
                    stage="critic_loop",
                    rule=f.rule,
                    action_index=f.action_index,
                    detail=f.detail,
                )
        if findings:
            try:  # denial rows also land on the run doc for Mission Control
                from app import runcontrol

                runcontrol.add_denials(
                    run_id, [{"stage": "critic_loop", **f.to_dict()} for f in findings]
                )
            except Exception as e:  # noqa: BLE001
                print(f"[policy_gate] denial persist failed: {e}")

        critique = _as_dict(state.get("critique"))
        approved = (
            not findings
            and critique.get("grade") == "pass"
            and critique.get("plan_hash") == ph
        )

        delta.update(
            {
                "day_plan": plan,
                "plan_hash": ph,
                "policy_findings": [f.to_dict() for f in findings],
                "policy_approved": approved,
            }
        )
        yield Event(
            author=self.name,
            actions=EventActions(state_delta=delta, escalate=approved),
        )
