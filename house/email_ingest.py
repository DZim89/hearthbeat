"""Watched-folder school-email ingest. Drop a real .eml into data/school_inbox/
and it goes: parse -> deep_scrub (map + local Gemma + map) -> Firestore.
This is the beat where Gemma is load-bearing: it catches the PII the family
map cannot know (a teacher's name, a phone number)."""

from __future__ import annotations

import hashlib
import time
from email import policy as email_policy
from email.parser import BytesParser
from pathlib import Path

from google.cloud import firestore

from app.stores import MAIL, db
from house import config, events
from house.privacy_gateway import deep_scrub


def _body_text(msg) -> str:
    body = msg.get_body(preferencelist=("plain", "html"))
    if body is None:
        return ""
    content = body.get_content()
    return content if isinstance(content, str) else str(content)


def ingest_file(path: Path) -> None:
    raw = path.read_bytes()
    msg = BytesParser(policy=email_policy.default).parsebytes(raw)
    subject = str(msg.get("subject", ""))
    body = _body_text(msg)[:6000]

    scrub_subject = deep_scrub(subject)
    scrub_body = deep_scrub(body)

    doc_id = hashlib.sha256(raw).hexdigest()[:16]
    db().collection(MAIL).document(doc_id).set(
        {
            "subject": scrub_subject.text,
            "body": scrub_body.text,
            "received_at": firestore.SERVER_TIMESTAMP,
            "scrub_meta": {
                "map_hits": scrub_subject.map_hits + scrub_body.map_hits,
                "model_spans": scrub_subject.model_spans + scrub_body.model_spans,
                "tier": scrub_body.tier,
            },
        }
    )
    events.emit(
        "school_mail_ingested",
        doc_id=doc_id,
        map_hits=scrub_subject.map_hits + scrub_body.map_hits,
        model_spans=scrub_subject.model_spans + scrub_body.model_spans,
        privacy_tier=scrub_body.tier,
    )
    processed = path.parent / "processed"
    processed.mkdir(exist_ok=True)
    path.rename(processed / path.name)
    print(
        f"[ingest] {path.name}: map_hits={scrub_body.map_hits + scrub_subject.map_hits} "
        f"gemma_spans={scrub_body.model_spans + scrub_subject.model_spans} tier={scrub_body.tier}"
    )


def main() -> None:
    config.WATCH_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[ingest] watching {config.WATCH_DIR}")
    while True:
        for path in sorted(config.WATCH_DIR.glob("*.eml")):
            try:
                ingest_file(path)
            except Exception as e:  # noqa: BLE001
                print(f"[ingest] {path.name} failed: {e}")
                path.rename(path.with_suffix(".eml.failed"))
        time.sleep(10)


if __name__ == "__main__":
    main()
