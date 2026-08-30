"""One entrypoint for all three house processes (real house AND judge mode):

    python -m house.run_all

Threads: snapshot mirror (15 min) · school-email ingest (watched folder) ·
action poller (20 s). Judge mode seeds the watched folder with the fixture
school email first so the whole story plays out unattended."""

from __future__ import annotations

import shutil
import threading
import time

from house import config


def main() -> None:
    config.WATCH_DIR.mkdir(parents=True, exist_ok=True)
    if config.SIMULATED:
        src = config.REPO_ROOT / "fixtures" / "school_email.eml"
        dst = config.WATCH_DIR / "school_email.eml"
        if src.exists() and not dst.exists():
            shutil.copy(src, dst)
            print("[run_all] judge mode: seeded fixture school email")

    from house import action_poller, email_ingest, snapshot_mirror

    for name, target in [
        ("mirror", snapshot_mirror.main),
        ("ingest", email_ingest.main),
        ("poller", action_poller.main),
    ]:
        threading.Thread(target=target, name=name, daemon=True).start()
        print(f"[run_all] started {name}")

    while True:
        time.sleep(60)


if __name__ == "__main__":
    main()
