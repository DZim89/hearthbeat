"""Firestore access — lazy clients, emulator-aware, judge-mode guarded."""

from __future__ import annotations

import os
from functools import lru_cache

from google.cloud import firestore

RUNS = "runs"
ACTIONS = "pending_actions"
SLIPS = "permission_slips"
MAIL = "school_mail"
HOME_DOC = "homes/main"


def is_simulated() -> bool:
    return os.environ.get("SIMULATED_HOME") == "1"


@lru_cache(maxsize=1)
def db() -> firestore.Client:
    emulator = os.environ.get("FIRESTORE_EMULATOR_HOST")
    if emulator and not is_simulated():
        raise RuntimeError(
            "FIRESTORE_EMULATOR_HOST is set but SIMULATED_HOME!=1 — refusing to "
            "run production mode against an emulator."
        )
    if is_simulated() and not emulator:
        raise RuntimeError(
            "SIMULATED_HOME=1 requires FIRESTORE_EMULATOR_HOST (judge mode never "
            "touches real Google Cloud)."
        )
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "demo-hearthbeat")
    return firestore.Client(project=project)
