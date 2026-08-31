"""In-process judge-mode pipeline test. Requires the Firestore emulator
(FIRESTORE_EMULATOR_HOST) — auto-skips without it; the compose stack is the
canonical way to run this environment (SIMULATED_HOME=1 docker compose up)."""

import json
import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.skipif(
    not os.environ.get("FIRESTORE_EMULATOR_HOST"),
    reason="needs the Firestore emulator (run inside judge-mode compose)",
)


@pytest.fixture(autouse=True)
def judge_env(monkeypatch):
    monkeypatch.setenv("SIMULATED_HOME", "1")
    monkeypatch.setenv("JUDGE_LLM", "fixture")
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "demo-hearthbeat")
    monkeypatch.setenv("LEDGER_SINK", "file")
    monkeypatch.setenv("LEDGER_FILE", "data/test_ledger.jsonl")


@pytest.mark.asyncio
async def test_full_pipeline_on_fixtures(tmp_path):
    from app.stores import HOME_DOC, MAIL, db

    # Seed the emulator the way house/run_all does.
    snap = json.loads(Path("fixtures/ha_snapshot.json").read_text())
    entities = {
        s["entity_id"]: {"state": s["state"], **s.get("attributes", {})} for s in snap
    }
    db().document(HOME_DOC).set(
        {
            "entities": entities,
            "presence": {},
            "energy": {},
            "calendar": json.loads(Path("fixtures/calendar.json").read_text()),
        }
    )
    db().collection(MAIL).document("t1").set(
        {"subject": "field trip", "body": "slip due tomorrow for [[P_KID1]]",
         "received_at": None, "scrub_meta": {}}
    )

    from app.runcontrol import execute_run

    result = await execute_run(
        "judge-test", trigger_source="manual", triggered_by="pytest", red_team=True
    )
    assert result["status"] == "done"

    run = db().collection("runs").document("judge-test").get().to_dict()
    assert run["stage_status"].get("dispatched") == "done"
    # The planted forbidden action must be refused:
    assert any("unlisted_action_type" in d.get("rule", "") for d in run.get("denials", []))

    # Idempotency: firing the same run again must no-op.
    again = await execute_run(
        "judge-test", trigger_source="manual", triggered_by="pytest"
    )
    assert again.get("noop") == "already_completed"


@pytest.mark.asyncio
async def test_retry_after_failure_reuses_checkpoints_no_duplicate_actions():
    """The tested retry path: a completed-then-failed run re-fires, resumes
    from surviving checkpoints, and produces the SAME action/slip documents —
    ids and counts unchanged."""
    from app.runcontrol import execute_run
    from app.stores import ACTIONS, SLIPS, db

    rid = "judge-retry"
    first = await execute_run(rid, trigger_source="manual", triggered_by="pytest",
                              red_team=True)
    assert first["status"] == "done"

    def _ids(coll):
        return {d.id for d in db().collection(coll).where("run_id", "==", rid).get()}

    actions_before, slips_before = _ids(ACTIONS), _ids(SLIPS)
    assert actions_before  # the fixture plan must dispatch something

    # Simulate a crash inside the dispatch window: run marked failed, the
    # dispatched checkpoint lost, earlier checkpoints intact.
    ref = db().collection("runs").document(rid)
    ref.update({"status": "failed"})
    ref.collection("checkpoints").document("dispatched").delete()

    second = await execute_run(rid, trigger_source="manual", triggered_by="pytest",
                               red_team=True)
    assert second["status"] == "done"
    assert second["attempt"] == 2
    assert set(second.get("resumed_from") or []) >= {"gathered", "planned", "reviewed"}

    assert _ids(ACTIONS) == actions_before
    assert _ids(SLIPS) == slips_before

    # And the completed run still no-ops on a third fire.
    third = await execute_run(rid, trigger_source="manual", triggered_by="pytest")
    assert third.get("noop") == "already_completed"


@pytest.mark.asyncio
async def test_scheduled_then_manual_resume_records_mixed_provenance(monkeypatch):
    """A stale scheduled attempt taken over via manual resume keeps its
    immutable initial provenance and records the resume separately."""
    from app import runcontrol
    from app.stores import db

    rid = "judge-prov"
    first = runcontrol.claim_run(rid, "scheduled", "sa-home@example.iam")
    assert first["claimed"]
    # Seed a finished_at to simulate a previous terminal attempt state
    db().collection("runs").document(rid).update({"finished_at": firestore.SERVER_TIMESTAMP, "error": "prior error"})
    monkeypatch.setattr(runcontrol, "HEARTBEAT_STALE_SECONDS", 0)
    import time as _t
    _t.sleep(1.5)  # let the heartbeat age past the (zeroed) staleness window
    second = runcontrol.claim_run(rid, "manual", "operator-token")
    assert second["claimed"] and second["attempt"] == 2 and second.get("resumed")

    doc = db().collection("runs").document(rid).get().to_dict() or {}
    assert doc["trigger_source"] == "scheduled"          # immutable initial
    assert doc["triggered_by"] == "sa-home@example.iam"  # immutable principal
    assert doc["current_trigger_source"] == "manual"
    assert doc["current_triggered_by"] == "operator-token"
    assert doc["attempt"] == 2
    assert [a["source"] for a in doc["attempt_history"]] == ["scheduled", "manual"]
    assert "error" not in doc                             # stale error cleared
    assert "finished_at" not in doc                      # stale finished_at cleared

    from app.server import _provenance_badge
    label, cls, _ = _provenance_badge(doc)
    assert "scheduled initial" in label and "manual resume" in label and cls == "manual"


@pytest.mark.asyncio
async def test_sensitive_action_slip_repaired_on_retry():
    """Fault injection: action doc exists (awaiting_approval, sensitive) but
    its slip is missing — a dispatch retry ensures exactly one slip and no
    duplicate action; retries do not inflate action_dispatched evidence."""
    from types import SimpleNamespace

    from app import ledger
    from app.dispatcher import Dispatcher, _action_id
    from app.stores import ACTIONS, SLIPS, db
    from google.cloud import firestore

    rid = "judge-slipfix"
    action = {
        "action_type": "notify_family_member", "entity": "[[P_GRANDMA]]",
        "when": "12:00", "why": "test", "sensitive": True, "message": "hello",
    }
    aid = _action_id(rid, action)
    db().collection(ACTIONS).document(aid).create({
        "run_id": rid, "action": action, "ha_domain": "notify", "ha_service": "send",
        "status": "awaiting_approval", "sensitive": True,
        "created_at": firestore.SERVER_TIMESTAMP, "attempts": 0,
    })
    assert not db().collection(SLIPS).document(aid).get().exists  # injected fault

    emitted_events = []
    class _MockActive:
        def emit_public(self, event_type, **kwargs):
            emitted_events.append((event_type, kwargs))

    monkeypatch_active = _MockActive()
    ledger.ACTIVE[rid] = monkeypatch_active

    async def _dispatch_once():
        ctx = SimpleNamespace(session=SimpleNamespace(state={
            "run_id": rid,
            "day_plan": {"summary": "s", "briefing_md": "b", "actions": [action]},
        }))
        async for _ in Dispatcher(name="hearth_dispatcher")._run_async_impl(ctx):
            pass

    try:
        # First retry: repairs missing slip
        await _dispatch_once()
        acts = list(db().collection(ACTIONS).where("run_id", "==", rid).get())
        slips = list(db().collection(SLIPS).where("run_id", "==", rid).get())
        assert [d.id for d in acts] == [aid]
        assert [d.id for d in slips] == [aid]
        assert emitted_events[-1][0] == "permission_slip_repaired"

        # Second retry: fully reused, no repair needed
        await _dispatch_once()
        acts = list(db().collection(ACTIONS).where("run_id", "==", rid).get())
        slips = list(db().collection(SLIPS).where("run_id", "==", rid).get())
        assert [d.id for d in acts] == [aid]
        assert [d.id for d in slips] == [aid]
        assert emitted_events[-1][0] == "action_reused"

        # Verify action_dispatched was NEVER emitted on retries (no ledger inflation)
        assert not any(ev[0] == "action_dispatched" for ev in emitted_events)
    finally:
        ledger.ACTIVE.pop(rid, None)


@pytest.mark.asyncio
async def test_invalid_preclaim_config_creates_no_run_doc(monkeypatch):
    """Config validation happens BEFORE the claim: a busted production config
    must not strand a status=running date-keyed doc."""
    from app.runcontrol import execute_run
    from app.stores import db

    monkeypatch.setenv("K_SERVICE", "svc")  # strict mode
    monkeypatch.delenv("SIMULATED_HOME", raising=False)
    for k in ("EGRESS_SALT", "EGRESS_ALIAS_HASHES", "EGRESS_KNOWN_TOKENS"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError, match="egress guard config invalid"):
        await execute_run("judge-badcfg", trigger_source="manual", triggered_by="pytest")
    assert not db().collection("runs").document("judge-badcfg").get().exists


@pytest.mark.asyncio
async def test_constructor_failure_after_claim_marks_run_failed(monkeypatch):
    """Defense in depth: if plugin construction raises AFTER the claim, the
    run doc must end status=failed — never stranded status=running."""
    from app import runcontrol
    from app.stores import db

    def _boom(*a, **k):
        raise RuntimeError("constructor exploded")

    monkeypatch.setattr(runcontrol, "LedgerPlugin", _boom)
    with pytest.raises(RuntimeError, match="constructor exploded"):
        await runcontrol.execute_run("judge-ctorfail", trigger_source="manual",
                                     triggered_by="pytest")
    doc = db().collection("runs").document("judge-ctorfail").get().to_dict() or {}
    assert doc.get("status") == "failed"
