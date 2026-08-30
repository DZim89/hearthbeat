"""The privacy floor gets the hardest tests in the repo."""

import json
from pathlib import Path

import pytest

from house import scrub

FIXTURE_MAP = Path(__file__).parent.parent / "fixtures" / "token_map.fixture.json"


@pytest.fixture()
def tmap():
    return scrub.load_map(FIXTURE_MAP)


def test_every_alias_is_scrubbed(tmap):
    text = " ".join(a for e in tmap.entries for a in e.aliases)
    out, hits = scrub.apply_map(text, tmap)
    assert hits >= len([a for e in tmap.entries for a in e.aliases])
    scrub.assert_clean(out, tmap)  # must not raise


def test_case_and_possessive_variants(tmap):
    alias = tmap.entries[0].aliases[0]
    text = f"{alias.upper()} left {alias.lower()}'s bag at school with {alias.title()}"
    out, hits = scrub.apply_map(text, tmap)
    assert hits == 3
    scrub.assert_clean(out, tmap)


def test_idempotent(tmap):
    text = "Pick up " + tmap.entries[0].aliases[0] + " at 3pm"
    once, _ = scrub.apply_map(text, tmap)
    twice, hits2 = scrub.apply_map(once, tmap)
    assert once == twice
    assert hits2 == 0


def test_roundtrip_rehydrates(tmap):
    entry = next(e for e in tmap.entries if e.aliases)
    text = f"Tell {entry.aliases[0]} that dinner moved"
    scrubbed, _ = scrub.apply_map(text, tmap)
    assert entry.token in scrubbed
    restored = scrub.rehydrate(scrubbed, tmap)
    assert entry.aliases[0] in restored


def test_entity_ids_rewritten_both_ways(tmap):
    pairs = tmap.entity_pairs()
    assert pairs, "fixture map must exercise entity id mapping"
    real, pseudo = pairs[0]
    scrubbed, _ = scrub.apply_map(f"pause {real} now", tmap)
    assert pseudo in scrubbed and real not in scrubbed
    assert real in scrub.rehydrate(scrubbed, tmap)


def test_assert_clean_raises_on_leak(tmap):
    alias = tmap.entries[0].aliases[0]
    with pytest.raises(scrub.ScrubLeakError):
        scrub.assert_clean(f"an email mentioning {alias} verbatim", tmap)


def test_substring_names_do_not_overfire(tmap):
    # An alias must not match inside an unrelated word.
    alias = tmap.entries[0].aliases[0]
    out, hits = scrub.apply_map(f"the {alias}ish weather", tmap)
    assert hits == 0


def test_redact_spans():
    out = scrub.redact_spans("call Mrs. Alvarez at 555-0142", ["Mrs. Alvarez", "555-0142"])
    assert "Alvarez" not in out and "555-0142" not in out
    assert "[[REDACTED_0]]" in out and "[[REDACTED_1]]" in out


def test_hashed_scan_detects_leak_without_plaintext(tmap):
    hashes = set(scrub.salted_alias_hashes(tmap))
    alias = tmap.entries[0].aliases[0]
    assert scrub.scan_hashed(f"planning around {alias} today", tmap.salt, hashes) > 0
    assert scrub.scan_hashed("a perfectly clean sentence", tmap.salt, hashes) == 0
    # the hash list itself reveals nothing:
    for h in hashes:
        assert alias.lower() not in h


def test_multiword_alias_single_word_leak_detected(tmap):
    multi = next((a for e in tmap.entries for a in e.aliases if " " in a), None)
    assert multi, "fixture map should include a multi-word alias"
    surname = multi.split()[-1]
    hashes = set(scrub.salted_alias_hashes(tmap))
    assert scrub.scan_hashed(f"the {surname} family", tmap.salt, hashes) > 0


def test_map_file_shape_validated(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"version": 1, "salt": "s", "entries": [
        {"token": "not-a-token", "kind": "person", "aliases": ["X"]}
    ]}))
    with pytest.raises(ValueError):
        scrub.load_map(bad)
