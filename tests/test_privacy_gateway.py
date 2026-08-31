"""P0: the house privacy parser must FAIL CLOSED — unparseable detector
output is never 'no PII found', and both-tiers-invalid means no write."""

import json

import pytest

from house import email_ingest, privacy_gateway as pg


# ---- _parse_spans ----------------------------------------------------------

def test_valid_empty_array_is_valid_nothing_found():
    assert pg._parse_spans("[]") == []


def test_valid_findings_parse():
    raw = 'Here you go: [{"text": "Jane Doe", "kind": "name"}, "555-0100"]'
    assert pg._parse_spans(raw) == ["Jane Doe", "555-0100"]


@pytest.mark.parametrize("raw,label", [
    ("I could not find any personal information in this text.", "prose"),
    ('[{"text": "Jane', "truncated JSON"),
    ('{"spans": []}', "object not list"),
    ('[{"kind": "name"}]', "entry without text"),
    ('[42]', "non-string entry"),
    ('[""]', "blank entry"),
    ("", "empty"),
])
def test_invalid_output_raises(raw, label):
    with pytest.raises(pg.SpanParseError):
        pg._parse_spans(raw)


# ---- detect_pii fallback chain ---------------------------------------------

def test_gemma_invalid_falls_back_to_valid_qwen(monkeypatch):
    monkeypatch.setattr(pg.config, "SIMULATED", False)
    monkeypatch.setattr(pg.config, "PRIVACY_TIER", "gemma")
    monkeypatch.setattr(pg, "_detect_via_ollama",
                        lambda t: (_ for _ in ()).throw(pg.SpanParseError("prose")))
    monkeypatch.setattr(pg, "_detect_via_qwen", lambda t: ["Jane Doe"])
    spans, tier = pg.detect_pii("some text")
    assert spans == ["Jane Doe"] and tier == "qwen"


def test_both_tiers_invalid_raises(monkeypatch):
    monkeypatch.setattr(pg.config, "SIMULATED", False)
    monkeypatch.setattr(pg.config, "PRIVACY_TIER", "gemma")
    monkeypatch.setattr(pg, "_detect_via_ollama",
                        lambda t: (_ for _ in ()).throw(pg.SpanParseError("prose")))
    monkeypatch.setattr(pg, "_detect_via_qwen",
                        lambda t: (_ for _ in ()).throw(pg.SpanParseError("also prose")))
    with pytest.raises(pg.SpanParseError):
        pg.detect_pii("some text")


# ---- both-invalid means NO ingest write ------------------------------------

class _RecorderDB:
    def __init__(self):
        self.writes = 0

    def collection(self, *_):
        return self

    def document(self, *_):
        return self

    def set(self, *_ , **__):
        self.writes += 1


def test_both_invalid_blocks_ingest_write(monkeypatch, tmp_path):
    eml = tmp_path / "mail.eml"
    eml.write_bytes(b"From: a@b.c\nSubject: hi\n\nbody text\n")
    recorder = _RecorderDB()
    monkeypatch.setattr(email_ingest, "db", lambda: recorder)
    monkeypatch.setattr(
        email_ingest, "deep_scrub",
        lambda t: (_ for _ in ()).throw(pg.SpanParseError("both tiers invalid")),
    )
    with pytest.raises(pg.SpanParseError):
        email_ingest.ingest_file(eml)
    assert recorder.writes == 0          # nothing reached Firestore
    assert eml.exists()                  # file retained for retry — not moved
