"""Pre-money-shot cleanup: remove artifacts of the OIDC dry-fire that consumed
today's date-keyed run doc, so the FILMED scheduled run claims runs/{today}
fresh on camera. Deletes ONLY docs belonging to the given run id.

    python -m infra.preshot_cleanup 2026-08-30
"""

from __future__ import annotations

import sys

from app.stores import ACTIONS, RUNS, SLIPS, db


def main(run_id: str) -> None:
    ref = db().collection(RUNS).document(run_id)
    n = 0
    for cp in ref.collection("checkpoints").get():
        cp.reference.delete()
        n += 1
    if ref.get().exists:
        ref.delete()
        n += 1
    for coll in (ACTIONS, SLIPS):
        for d in db().collection(coll).where("run_id", "==", run_id).get():
            d.reference.delete()
            n += 1
    print(f"[cleanup] removed {n} docs for run {run_id} — the filmed run will claim it fresh")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python -m infra.preshot_cleanup <run_id>")
    main(sys.argv[1])
