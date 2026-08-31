"""HA -> Firestore mirror. Every 15 minutes the house pushes a TOKEN-SPACE
snapshot of itself to `homes/main`. The cloud only ever reads this mirror —
it has no path into the house."""

from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from google.cloud import firestore

from app.stores import HOME_DOC, db
from house import config, events, ha, scrub


def _interesting(entity_id: str, tmap: scrub.TokenMap) -> bool:
    if any(entity_id.startswith(p) for p in config.SNAPSHOT_PREFIXES):
        return True
    if any(entity_id == real for real, _ in tmap.entity_pairs()):
        return True
    return any(k in entity_id for k in config.ENERGY_KEYWORDS)


def build_snapshot() -> dict[str, Any]:
    tmap = scrub.load_map(config.TOKEN_MAP_PATH)
    states = ha.get_states()

    entities: dict[str, Any] = {}
    presence: dict[str, str] = {}
    energy: dict[str, Any] = {}
    for s in states:
        eid = s.get("entity_id", "")
        if not _interesting(eid, tmap):
            continue
        attrs = s.get("attributes", {}) or {}
        slim = {
            "state": s.get("state"),
            "friendly_name": attrs.get("friendly_name", ""),
        }
        for extra in ("media_title", "media_content_type", "source"):
            if attrs.get(extra):
                slim[extra] = attrs[extra]
        if eid.startswith("person."):
            presence[eid] = str(s.get("state"))
        elif any(k in eid for k in config.ENERGY_KEYWORDS):
            energy[eid] = s.get("state")
        else:
            entities[eid] = slim

    # Free-text CONTENT (calendar text, media titles) is exactly the class of
    # data that can carry PII the family map cannot know — it goes through the
    # full deep_scrub (map -> local Gemma -> map), same as school email.
    from house.privacy_gateway import deep_scrub

    def _free_text(s: str) -> str:
        s = (s or "").strip()
        return deep_scrub(s).text if s else ""

    for slim in entities.values():
        if slim.get("media_title"):
            slim["media_title"] = _free_text(str(slim["media_title"]))

    now = datetime.now(timezone.utc)
    calendar = [
        {
            "summary": _free_text(ev.get("summary", "")),
            "start": str((ev.get("start") or {}).get("dateTime") or (ev.get("start") or {}).get("date", "")),
            "end": str((ev.get("end") or {}).get("dateTime") or (ev.get("end") or {}).get("date", "")),
            "description": _free_text((ev.get("description") or "")[:200]),
        }
        for ev in ha.get_calendar_events(
            config.CALENDAR_ENTITY, now.isoformat(), (now + timedelta(hours=48)).isoformat()
        )
    ]

    snapshot = {
        "entities": entities,
        "presence": presence,
        "energy": energy,
        "calendar": calendar,
    }
    # Scrub the WHOLE serialized snapshot (names hide in friendly_names and
    # entity ids too), then hard-verify before it may leave the house.
    # ensure_ascii=False: an escaped non-ASCII name must not dodge the regexes.
    dumped = json.dumps(snapshot, ensure_ascii=False)
    scrubbed, hits = scrub.apply_map(dumped, tmap)
    scrub.assert_clean(scrubbed, tmap)
    clean = json.loads(scrubbed)
    clean["map_hits"] = hits
    return clean


def mirror_once() -> None:
    snap = build_snapshot()
    snap["updated_at"] = firestore.SERVER_TIMESTAMP
    db().document(HOME_DOC).set(snap)
    events.emit(
        "snapshot_mirrored",
        entities=len(snap.get("entities", {})),
        calendar_events=len(snap.get("calendar", [])),
        map_hits=snap.get("map_hits", 0),
    )
    print(
        f"[mirror] {len(snap.get('entities', {}))} entities, "
        f"{len(snap.get('calendar', []))} calendar events, map_hits={snap.get('map_hits')}"
    )


def main() -> None:
    while True:
        try:
            mirror_once()
        except Exception as e:  # noqa: BLE001
            print(f"[mirror] cycle failed: {e}")
        time.sleep(config.MIRROR_SECONDS)


if __name__ == "__main__":
    main()
