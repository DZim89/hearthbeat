"""Table tests for the deterministic policy engine — the default-deny authority."""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.policy import load_policy, plan_hash

POLICY = Path(__file__).parent.parent / "config" / "policy.yaml"
TZ = ZoneInfo("America/Los_Angeles")

MIDDAY = datetime(2026, 8, 31, 12, 0, tzinfo=TZ)
LATE_NIGHT = datetime(2026, 8, 30, 23, 15, tzinfo=TZ)   # inside quiet hours
EARLY = datetime(2026, 8, 31, 6, 45, tzinfo=TZ)          # cron time — outside


@pytest.fixture()
def policy():
    return load_policy(POLICY)


def _action(**kw):
    return {
        "action_type": "media_pause",
        "entity": "media_player.family_tv",
        "when": "now",
        "why": "test",
        "sensitive": False,
        **kw,
    }


def test_whitelisted_action_passes(policy):
    assert policy.check_action(_action(), now=MIDDAY) == []


def test_unlisted_action_type_denied(policy):
    v = policy.check_action(_action(action_type="front_door_unlock"), now=MIDDAY)
    assert v and v[0].startswith("unlisted_action_type")


def test_wrong_entity_denied(policy):
    v = policy.check_action(_action(entity="media_player.parents_tv"), now=MIDDAY)
    assert any(r.startswith("entity_not_whitelisted") for r in v)


def test_missing_required_arg_denied(policy):
    v = policy.check_action(
        _action(action_type="calendar_create_event", entity="calendar.hearthbeat_family",
                title="x", start_iso="", end_iso="2026-08-31T17:00:00"),
        now=MIDDAY,
    )
    assert any(r == "missing_required_arg:start_iso" for r in v)


def test_quiet_hours_blocks_noisy_action(policy):
    v = policy.check_action(
        _action(action_type="notify_family_member", entity="[[P_DAD]]", message="hi"),
        now=LATE_NIGHT,
    )
    assert "quiet_hours" in v


def test_quiet_hours_allows_quiet_ok_action(policy):
    assert policy.check_action(_action(), now=LATE_NIGHT) == []  # media_pause is quiet_ok


def test_quiet_hours_window_crosses_midnight(policy):
    assert policy.in_quiet_hours(LATE_NIGHT) is True
    assert policy.in_quiet_hours(datetime(2026, 8, 31, 2, 0, tzinfo=TZ)) is True
    assert policy.in_quiet_hours(EARLY) is False
    assert policy.in_quiet_hours(MIDDAY) is False


def test_sensitive_action_is_quiet_hours_exempt_at_plan_time(policy):
    # It stops at a permission slip regardless — the tap is the consent gate.
    v = policy.check_action(
        _action(action_type="notify_family_member", entity="[[P_GRANDMA]]",
                message="hi", sensitive=True),
        now=LATE_NIGHT,
    )
    assert "quiet_hours" not in v


def test_human_approval_bypasses_quiet_hours(policy):
    v = policy.check_action(
        _action(action_type="notify_family_member", entity="[[P_GRANDMA]]",
                message="hi", sensitive=True),
        now=LATE_NIGHT,
        human_approved=True,
    )
    assert "quiet_hours" not in v


def test_sensitive_target_requires_slip_flag(policy):
    v = policy.check_action(
        _action(action_type="notify_family_member", entity="[[P_GRANDMA]]",
                message="hi", sensitive=False),
        now=MIDDAY,
    )
    assert "sensitive_target_requires_permission_slip" in v


def test_plan_level_budget_and_count(policy):
    plan = {"actions": [_action() for _ in range(7)]}
    findings = policy.check(plan, now=MIDDAY, spent_microcents=0)
    assert any(f.rule == "too_many_actions" for f in findings)
    findings = policy.check({"actions": []}, now=MIDDAY,
                            spent_microcents=policy.daily_budget_microcents)
    assert any(f.rule == "budget_exhausted" for f in findings)


def test_malformed_action_is_a_finding_not_a_crash(policy):
    findings = policy.check({"actions": ["rm -rf /"]}, now=MIDDAY)
    assert any(f.rule == "malformed_action" for f in findings)


def test_plan_hash_stable_and_sensitive_to_change():
    p1 = {"actions": [_action()], "summary": "s"}
    p2 = {"summary": "s", "actions": [_action()]}
    assert plan_hash(p1) == plan_hash(p2)  # key order irrelevant
    p3 = {"actions": [_action(entity="media_player.other")], "summary": "s"}
    assert plan_hash(p1) != plan_hash(p3)
