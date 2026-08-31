"""Gatherer function tools — read the house's token-space mirror from Firestore.

Everything these tools return is ALREADY scrubbed: the house-side mirror
(house/snapshot_mirror.py, house/email_ingest.py) applies the deterministic
token map (and, for free text, the local Gemma pass) before anything is
written to Firestore. Known family aliases are tokenized house-side on the
intended runtime path; the cloud pipeline receives token-space data.
"""

from __future__ import annotations

from typing import Any

from app.stores import HOME_DOC, MAIL, db


def read_home_snapshot() -> dict[str, Any]:
    """Read the current token-space snapshot of the home: media players, lights
    summary, and when it was last mirrored.

    Returns:
        dict with keys: entities (map of entity id -> state), updated_at.
    """
    doc = db().document(HOME_DOC).get()
    if not doc.exists:
        return {"entities": {}, "updated_at": None, "note": "no snapshot mirrored yet"}
    data = doc.to_dict() or {}
    return {
        "entities": data.get("entities", {}),
        "updated_at": str(data.get("updated_at")),
    }


def read_family_calendar() -> dict[str, Any]:
    """Read the family calendar events for the next 48 hours (token space).

    Returns:
        dict with key: events (list of {summary, start, end, calendar}).
    """
    doc = db().document(HOME_DOC).get()
    data = (doc.to_dict() or {}) if doc.exists else {}
    return {"events": data.get("calendar", [])}


def read_school_mail() -> dict[str, Any]:
    """Read recent school emails (subjects and scrubbed bodies).

    Returns:
        dict with key: messages (list of {id, subject, body, received_at,
        scrub_meta}) — scrub_meta shows how many PII items the deterministic
        map and the local Gemma pass each caught before this text left the house.
    """
    docs = (
        db()
        .collection(MAIL)
        .order_by("received_at", direction="DESCENDING")
        .limit(5)
        .get()
    )
    return {
        "messages": [{"id": d.id, **(d.to_dict() or {})} for d in docs]
    }


def read_energy_presence() -> dict[str, Any]:
    """Read presence (who is home, token space) and energy summary sensors.

    Returns:
        dict with keys: presence, energy.
    """
    doc = db().document(HOME_DOC).get()
    data = (doc.to_dict() or {}) if doc.exists else {}
    return {
        "presence": data.get("presence", {}),
        "energy": data.get("energy", {}),
    }
