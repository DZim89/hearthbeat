"""Deterministic policy engine — the only authority on what hearthbeat may do.

Pure code, no LLM anywhere. Enforced three times:
  1. inside the LoopAgent by PolicyGate (drives the critic/reviser loop),
  2. by the Dispatcher before anything is written to Firestore (degraded-mode belt),
  3. by the house-side action poller before anything touches Home Assistant.

Default-deny: an action type or entity not named in config/policy.yaml is a
violation. Findings are data, not exceptions — every violation becomes a
denial row in the ledger.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


@dataclass(frozen=True)
class Finding:
    action_index: int          # -1 for plan-level findings
    rule: str
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Policy:
    raw: dict[str, Any]

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.raw.get("timezone", "America/Los_Angeles"))

    @property
    def daily_budget_microcents(self) -> int:
        return int(self.raw.get("daily_budget_cents", 50)) * 1_000_000

    def action_spec(self, action_type: str) -> dict[str, Any] | None:
        return self.raw.get("actions", {}).get(action_type)

    # ---- rules -------------------------------------------------------------

    def in_quiet_hours(self, now: datetime) -> bool:
        qh = self.raw.get("quiet_hours") or {}
        if not qh:
            return False
        start = _parse_hhmm(qh["start"])
        end = _parse_hhmm(qh["end"])
        t = now.astimezone(self.tz).time()
        if start <= end:
            return start <= t < end
        return t >= start or t < end  # window crosses midnight

    def check_action(
        self,
        action: dict[str, Any],
        *,
        now: datetime,
        human_approved: bool = False,
    ) -> list[str]:
        """Violation rule names for one action (empty list == allowed)."""
        violations: list[str] = []
        atype = str(action.get("action_type", ""))
        spec = self.action_spec(atype)
        if spec is None:
            return [f"unlisted_action_type:{atype or '<empty>'}"]

        entity = str(action.get("entity", ""))
        allowed = spec.get("allowed_entities", [])
        if entity not in allowed:
            violations.append(f"entity_not_whitelisted:{entity or '<empty>'}")

        for arg in spec.get("required_args", []):
            if not str(action.get(arg, "")).strip():
                violations.append(f"missing_required_arg:{arg}")

        sensitive_targets = spec.get("sensitive_targets", [])
        if entity in sensitive_targets and not bool(action.get("sensitive")):
            violations.append("sensitive_target_requires_permission_slip")

        quiet_ok = bool(spec.get("quiet_ok", False))
        # A sensitive action can NEVER auto-execute — it always stops at a
        # permission slip, and the human tap is itself the quiet-hours consent.
        # So it is exempt at plan time; the poller re-checks with
        # human_approved=True only after a real tap.
        bypass = (human_approved or bool(action.get("sensitive"))) and bool(
            self.raw.get("human_approval_bypasses_quiet_hours", True)
        )
        if self.in_quiet_hours(now) and not quiet_ok and not bypass:
            violations.append("quiet_hours")

        return violations

    def structural_findings(self, plan: dict[str, Any]) -> list[Finding]:
        """Default-deny on model-output SHAPE: an empty/prose/malformed plan
        must never pass as a valid no-op. Explicit actions=[] with real
        summary/briefing IS valid."""
        bad: list[str] = []
        for key in ("summary", "briefing_md"):
            v = plan.get(key)
            if not isinstance(v, str) or not v.strip():
                bad.append(key)
        actions = plan.get("actions")
        if not isinstance(actions, list):
            bad.append("actions")
        else:
            for i, a in enumerate(actions):
                if not isinstance(a, dict):
                    bad.append(f"action[{i}]")
                    continue
                for field_name in ("action_type", "entity", "why"):
                    v = a.get(field_name)
                    if not isinstance(v, str) or not v.strip():
                        bad.append(f"action[{i}].{field_name}")
                if "sensitive" in a and not isinstance(a["sensitive"], bool):
                    bad.append(f"action[{i}].sensitive")
        if bad:
            return [Finding(-1, "invalid_model_output", "missing/invalid: " + ", ".join(bad[:12]))]
        return []

    def check(
        self,
        plan: dict[str, Any],
        *,
        now: datetime,
        spent_microcents: int = 0,
    ) -> list[Finding]:
        findings: list[Finding] = list(self.structural_findings(plan))
        actions = plan.get("actions") if isinstance(plan.get("actions"), list) else []
        max_actions = int(self.raw.get("max_actions_per_run", 6))
        if len(actions) > max_actions:
            findings.append(
                Finding(-1, "too_many_actions", f"{len(actions)} > max {max_actions}")
            )
        if spent_microcents >= self.daily_budget_microcents:
            findings.append(
                Finding(
                    -1,
                    "budget_exhausted",
                    f"spent {spent_microcents}µ¢ >= budget {self.daily_budget_microcents}µ¢",
                )
            )
        for i, action in enumerate(actions):
            if not isinstance(action, dict):
                findings.append(Finding(i, "malformed_action", str(type(action))))
                continue
            for rule in self.check_action(action, now=now):
                findings.append(Finding(i, rule, _describe(action)))
        return findings


def _describe(action: dict[str, Any]) -> str:
    return f"{action.get('action_type')} -> {action.get('entity')}"


def _parse_hhmm(s: str) -> time:
    h, m = str(s).split(":")
    return time(int(h), int(m))


def load_policy(path: str | Path) -> Policy:
    return Policy(raw=yaml.safe_load(Path(path).read_text(encoding="utf-8")))


def plan_hash(plan: dict[str, Any]) -> str:
    """Canonical hash binding a critique to the exact plan it graded."""
    return hashlib.sha256(
        json.dumps(plan, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()[:16]
