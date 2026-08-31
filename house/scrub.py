"""Deterministic token-map scrubbing — pure stdlib, zero LLM dependencies.

This module is the privacy floor of hearthbeat. It is applied BEFORE and AFTER
the local-model (Gemma) PII pass, so the guarantee never rests on a model:

    raw text -> apply_map -> [local Gemma span detection] -> redact_spans
             -> apply_map (again) -> assert_clean -> cloud

The REAL token map (config/token_map.local.json) exists only on the house
machine and is gitignored. The repo ships a fixture map with invented names
(fixtures/token_map.fixture.json) so judge mode exercises identical code.

Rehydration (token -> real value) happens exclusively inside the house, in
house/action_poller.py. The cloud never holds the map — it holds only salted
hashes of the aliases (see salted_alias_hashes) so it can *prove* nothing
leaked without being able to reverse anything.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

TOKEN_RE = re.compile(r"\[\[[A-Z0-9_]+\]\]")
REDACTED_RE = re.compile(r"\[\[REDACTED_\d+\]\]")

# Person aliases of this length or more are ALSO scrubbed as bare substrings
# (no word boundary): entity ids and identifiers glue names to suffixes
# ('donnys_pixel', 'person.donnyz') and a boundary regex sails right past
# them. Over-firing inside a rare English word is the safe direction.
SUBSTRING_MIN_LEN = 5


class ScrubLeakError(RuntimeError):
    """Raised when text that must be clean still contains a mapped alias."""


@dataclass
class MapEntry:
    token: str                      # e.g. "[[P_KID1]]"
    kind: str                       # person | room | place | other
    aliases: list[str]              # names/spellings that must never leave the house
    entity_ids: dict[str, str] = field(default_factory=dict)  # real HA id -> pseudonym id


@dataclass
class TokenMap:
    version: int
    salt: str
    entries: list[MapEntry]

    def aliases(self) -> list[tuple[str, str]]:
        """(alias, token) pairs, longest alias first so 'Pat Miller' wins over 'Pat'."""
        pairs = [(a, e.token) for e in self.entries for a in e.aliases if a.strip()]
        return sorted(pairs, key=lambda p: len(p[0]), reverse=True)

    def entity_pairs(self) -> list[tuple[str, str]]:
        pairs = [(real, pseudo) for e in self.entries for real, pseudo in e.entity_ids.items()]
        return sorted(pairs, key=lambda p: len(p[0]), reverse=True)

    def substring_aliases(self) -> list[tuple[str, str]]:
        """(alias, token) pairs scrubbed WITHOUT word boundaries — single-word
        person names long enough to be identifying inside identifiers."""
        pairs = [
            (a, e.token)
            for e in self.entries
            if e.kind == "person"
            for a in e.aliases
            if len(a) >= SUBSTRING_MIN_LEN and " " not in a
        ]
        return sorted(pairs, key=lambda p: len(p[0]), reverse=True)

    def tokens(self) -> frozenset[str]:
        return frozenset(e.token for e in self.entries)


def load_map(path: str | Path) -> TokenMap:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    entries = [
        MapEntry(
            token=e["token"],
            kind=e.get("kind", "other"),
            aliases=list(e.get("aliases", [])),
            entity_ids=dict(e.get("entity_ids", {})),
        )
        for e in data["entries"]
    ]
    tmap = TokenMap(version=int(data["version"]), salt=data["salt"], entries=entries)
    for entry in entries:
        if not TOKEN_RE.fullmatch(entry.token):
            raise ValueError(f"map token {entry.token!r} must look like [[NAME]]")
        for alias in entry.aliases:
            if TOKEN_RE.search(alias):
                raise ValueError(f"alias {alias!r} may not contain a token")
    return tmap


def _alias_regex(alias: str) -> re.Pattern:
    # Word-boundary, case-insensitive. Handles multi-word aliases and possessives
    # ("Donny's" still matches the alias "Donny").
    return re.compile(rf"(?<![A-Za-z0-9]){re.escape(alias)}(?![A-Za-z0-9])", re.IGNORECASE)


def _outside_tokens(text: str, transform) -> str:
    """Apply transform only to the segments of text that are not [[TOKEN]]s —
    an alias like 'Dad' must never match inside its own token [[P_DAD]]."""
    parts: list[str] = []
    last = 0
    for m in TOKEN_RE.finditer(text):
        parts.append(transform(text[last : m.start()]))
        parts.append(m.group(0))
        last = m.end()
    parts.append(transform(text[last:]))
    return "".join(parts)


def apply_map(text: str, tmap: TokenMap) -> tuple[str, int]:
    """Replace every alias/entity-id with its token. Idempotent. Returns (text, hits)."""
    hits = 0
    for real, pseudo in tmap.entity_pairs():
        if real in text:
            hits += text.count(real)
            text = text.replace(real, pseudo)
    for alias, token in tmap.aliases():
        rx = _alias_regex(alias)

        def _sub(segment: str) -> str:
            nonlocal hits
            segment, n = rx.subn(token, segment)  # noqa: B023 — consumed immediately
            hits += n
            return segment

        text = _outside_tokens(text, _sub)
    # Second pass: bare-substring scrub for identifying person names, so
    # 'donnys_pixel' / 'person.donnyz' style concatenations cannot slip through.
    for alias, token in tmap.substring_aliases():
        rx = re.compile(re.escape(alias), re.IGNORECASE)

        def _sub2(segment: str) -> str:
            nonlocal hits
            segment, n = rx.subn(token, segment)  # noqa: B023 — consumed immediately
            hits += n
            return segment

        text = _outside_tokens(text, _sub2)
    return text, hits


def rehydrate(text: str, tmap: TokenMap) -> str:
    """Inverse of apply_map — house-side only. Token -> first alias; pseudo id ->
    real id. Longest-first so a pseudo id that prefixes another can't corrupt it."""
    subs: list[tuple[str, str]] = []
    for entry in tmap.entries:
        if entry.aliases:
            subs.append((entry.token, entry.aliases[0]))
        subs.extend((pseudo, real) for real, pseudo in entry.entity_ids.items())
    for old, new in sorted(subs, key=lambda p: len(p[0]), reverse=True):
        text = text.replace(old, new)
    return text


def redact_spans(text: str, spans: list[str]) -> str:
    """Replace model-flagged spans with numbered redaction markers."""
    for i, span in enumerate(s for s in spans if s and s.strip()):
        text = text.replace(span, f"[[REDACTED_{i}]]")
    return text


def _neutralize_tokens(text: str, known_tokens: frozenset[str]) -> str:
    """Remove KNOWN tokens (they are the safe form) but UNWRAP unknown ones:
    a smuggled [[P_DONNY]] becomes ' P DONNY ' and gets scanned as plain text."""

    def repl(m: re.Match) -> str:
        tok = m.group(0)
        if tok in known_tokens or REDACTED_RE.fullmatch(tok):
            return " "
        return " " + tok[2:-2].replace("_", " ") + " "

    return TOKEN_RE.sub(repl, text)


def assert_clean(text: str, tmap: TokenMap) -> None:
    """Hard-fail if any alias or real entity id survives. The final deterministic gate."""
    for real, _pseudo in tmap.entity_pairs():
        if real in text:
            raise ScrubLeakError(f"real entity id survived scrub: {real!r}")
    stripped = _neutralize_tokens(text, tmap.tokens())
    for alias, _token in tmap.aliases():
        if _alias_regex(alias).search(stripped):
            raise ScrubLeakError(f"alias survived scrub (len={len(alias)})")
    lowered = stripped.lower()
    for alias, _token in tmap.substring_aliases():
        if alias.lower() in lowered:
            raise ScrubLeakError(f"person name survived scrub as substring (len={len(alias)})")


def _hash(salt: str, phrase: str) -> str:
    return hashlib.sha256((salt + phrase.strip().lower()).encode("utf-8")).hexdigest()


# Generic words that may appear inside a person alias ("Grandma Pat") but are
# not identifying on their own — hashing them would false-positive everywhere.
_PER_WORD_STOPWORDS = {
    "the", "dad", "mom", "mama", "papa", "grandma", "grandpa", "nana", "aunt",
    "uncle", "mrs", "mr", "miss", "coach", "baby", "kiddo",
}


def salted_alias_hashes(tmap: TokenMap) -> list[str]:
    """Hashes the cloud egress guard compares against. One per full alias; for
    PERSON aliases additionally one per name-word (>=4 chars, minus generic
    family words) so a leaked bare surname still trips the wire without turning
    common English words into alarms."""
    out: set[str] = set()
    for entry in tmap.entries:
        for alias in entry.aliases:
            if not alias.strip():
                continue
            # A generic family word used as a placeholder alias ("Grandma",
            # "Dad") stays in the map for REHYDRATION but must never arm a
            # hash: models legitimately write those words in prose, and the
            # guard would block every mention. (Live incident: the planner
            # writing the English word for [[P_GRANDMA]] tripped 2 matches.)
            if alias.strip().lower() in _PER_WORD_STOPWORDS:
                continue
            out.add(_hash(tmap.salt, alias))
            words = alias.split()
            if entry.kind == "person" and len(words) > 1:
                for w in words:
                    if len(w) >= 4 and w.lower() not in _PER_WORD_STOPWORDS:
                        out.add(_hash(tmap.salt, w))
    return sorted(out)


def scan_hashed(
    text: str,
    salt: str,
    alias_hashes: set[str],
    max_ngram: int = 3,
    known_tokens: frozenset[str] = frozenset(),
) -> int:
    """Cloud-side: count words/ngrams of text whose salted hash is a known alias hash.

    The cloud holds only hashes — it can detect a leak without learning the alias.
    KNOWN tokens are the safe form and are skipped; an UNKNOWN [[...]] (e.g. a
    model-invented [[P_DONNY]]) is unwrapped and scanned as plain text. The word
    regex is unicode-aware so non-ASCII names are not invisible.
    Returns the number of matches (0 == provably clean w.r.t. the map).
    """
    text = _neutralize_tokens(text, known_tokens)
    words = re.findall(r"[^\W\d_]+(?:['’-][^\W\d_]+)*", text, re.UNICODE)
    lowered = [w.lower() for w in words]
    matches = 0
    for n in range(1, max_ngram + 1):
        for i in range(len(lowered) - n + 1):
            phrase = " ".join(lowered[i : i + n])
            if _hash(salt, phrase) in alias_hashes:
                matches += 1
    return matches
