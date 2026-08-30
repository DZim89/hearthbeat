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
