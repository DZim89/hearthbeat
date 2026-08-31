"""Judge-mode kickoff: wait for the agent AND the seeded house state, then fire
the pipeline once through /trigger (trigger_source=manual — judge mode cannot
and does not impersonate a scheduled run).

Readiness is polled, not slept: the pipeline only makes sense after the house
container has mirrored the fixture home into the emulator and ingested the
fixture school email. A timeout names exactly what was still missing."""

from __future__ import annotations

import os
import sys
import time

import httpx

AGENT = os.environ.get("AGENT_URL", "http://agent:8080")
READY_TIMEOUT_S = int(os.environ.get("KICKOFF_READY_TIMEOUT_S", "120"))
POLL_S = 3


def wait_health(deadline: float) -> None:
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{AGENT}/health", timeout=3).status_code == 200:
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    raise SystemExit(f"KICKOFF TIMEOUT: {AGENT}/health never returned 200 — is the agent container up?")


def _readiness() -> tuple[bool, bool]:
    """(home_ready, mail_ready) against the emulator the compose stack shares."""
    from app.stores import HOME_DOC, MAIL, db

    home = db().document(HOME_DOC).get().to_dict() or {}
    home_ready = bool(
        home.get("updated_at") is not None
        and home.get("entities")
        and isinstance(home.get("calendar"), list)
    )
    mail_ready = any(
        (d.to_dict() or {}).get("received_at") is not None
        for d in db().collection(MAIL).limit(5).get()
    )
    return home_ready, mail_ready


def wait_seeded(deadline: float) -> None:
    home_ready = mail_ready = False
    while time.monotonic() < deadline:
        try:
            home_ready, mail_ready = _readiness()
        except Exception as e:  # noqa: BLE001 — emulator may still be booting
            print(f"[kickoff] readiness probe error (retrying): {e}")
        if home_ready and mail_ready:
            print("[kickoff] house seeded: snapshot mirrored + school email ingested")
            return
        time.sleep(POLL_S)
    missing = []
    if not home_ready:
        missing.append("homes/main snapshot (mirror has not written updated_at/entities/calendar)")
    if not mail_ready:
        missing.append("school_mail doc with received_at (email ingest has not completed)")
    raise SystemExit(
        "KICKOFF TIMEOUT after "
        f"{READY_TIMEOUT_S}s waiting for: {'; '.join(missing)} — check the "
        "`house` container logs (docker compose logs house)."
    )


def fire() -> None:
    r = httpx.post(f"{AGENT}/trigger", params={"red_team": 1}, timeout=600)
    print(f"[kickoff] /trigger -> {r.status_code}: {r.text[:400]}")
    if not (200 <= r.status_code < 300):
        raise SystemExit(f"KICKOFF FAILED: /trigger returned {r.status_code} — see agent logs above.")
    print("[kickoff] open http://localhost:8080/missioncontrol — the run (incl. the")
    print("[kickoff] red-team refusal and the permission slip) is now visible.")


def main() -> None:
    deadline = time.monotonic() + READY_TIMEOUT_S
    wait_health(deadline)
    wait_seeded(deadline)
    fire()


if __name__ == "__main__":
    main()
