"""Pre-push PII scan — the repo-public gate.

Loads the LOCAL token map (never shipped) and scans every git-tracked file
plus the shipped fixtures for any real alias or real entity id. Exit 1 on any
hit. Run before every push and before flipping the repo public:

    python -m infra.pii_scan
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from house import config, scrub

# Not identifying on their own — placeholder aliases like "Grandma" may appear
# in public copy without revealing anyone.
GENERIC = {"grandma", "grandpa", "nana", "papa", "dad", "mom", "mama"}
# The maintainer ships this repo under their own public identity (GitHub,
# Devpost, git author). Kid/spouse/grandma REAL names remain hard-fail.
AUTHOR_PUBLIC = {"donny", "donny zimmerman", "zimmerman", "zimmermans"}


def _scan_map(tmap: scrub.TokenMap) -> scrub.TokenMap:
    entries = []
    for e in tmap.entries:
        aliases = [
            a for a in e.aliases
            if a.lower() not in GENERIC and a.lower() not in AUTHOR_PUBLIC
        ]
        entries.append(
            scrub.MapEntry(token=e.token, kind=e.kind, aliases=aliases,
                           entity_ids=e.entity_ids)
        )
    return scrub.TokenMap(version=tmap.version, salt=tmap.salt, entries=entries)


def main() -> int:
    tmap = _scan_map(
        scrub.load_map(config.REPO_ROOT / "config" / "token_map.local.json")
    )
    tracked = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=config.REPO_ROOT
    ).stdout.splitlines()
    hits = 0
    for rel in tracked:
        p = config.REPO_ROOT / rel
        if not p.is_file() or p.suffix in (".png", ".mp4", ".srt"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except Exception:  # noqa: BLE001
            continue
        try:
            scrub.assert_clean(text, tmap)
        except scrub.ScrubLeakError as e:
            print(f"LEAK {rel}: {e}")
            hits += 1
    if hits:
        print(f"\nFAIL: {hits} file(s) contain protected content — do NOT push/public.")
        return 1
    print(f"CLEAN: {len(tracked)} tracked files, zero protected-alias hits.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
