"""Judge-mode kickoff: wait for the agent + a mirrored snapshot, then fire the
pipeline once through /trigger (trigger_source=manual — judge mode cannot and
does not impersonate a scheduled run)."""

from __future__ import annotations

import os
import time

import httpx

AGENT = os.environ.get("AGENT_URL", "http://agent:8080")


def wait(url: str, tries: int = 60) -> None:
    for _ in range(tries):
        try:
            if httpx.get(url, timeout=3).status_code == 200:
                return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(2)
    raise SystemExit(f"gave up waiting for {url}")


def main() -> None:
    wait(f"{AGENT}/healthz")
    print("[kickoff] agent healthy; giving the house 25s to mirror + ingest fixtures")
    time.sleep(25)
    r = httpx.post(f"{AGENT}/trigger", params={"red_team": 1}, timeout=600)
    print(f"[kickoff] /trigger -> {r.status_code}: {r.text[:400]}")
    print("[kickoff] open http://localhost:8080/missioncontrol — the run (incl. the")
    print("[kickoff] red-team refusal and the permission slip) is now visible.")


if __name__ == "__main__":
    main()
