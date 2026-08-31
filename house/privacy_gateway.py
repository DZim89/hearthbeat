"""The privacy gateway — where local Gemma earns its keep.

deep_scrub() is the ONLY path by which free text (email bodies, calendar
titles) leaves the house:

    deterministic map PRE-pass  ->  local Gemma PII detection  ->  span redact
    ->  deterministic map POST-pass  ->  assert_clean  ->  Firestore

THE ENFORCEMENT PATH IS DIRECT LOCAL HTTP: deep_scrub calls the Gemma
(ollama) or Qwen (OpenAI-compatible) endpoint itself, deterministically —
no model ever decides whether scrubbing happens. An ADK agent/AgentTool
factory is also exported below as an OPTIONAL integration surface for
model-initiated scrubbing; it is not the enforcement path.

Gemma scans for PII the map cannot know: a teacher's name, a phone number in
a school email. The map deterministically tokenizes the KNOWN family aliases.
FAIL-CLOSED PARSING: a detector response that is prose, malformed/truncated
JSON, a non-list, or contains unusable entries raises SpanParseError — it is
never treated as "no PII found". Gemma-invalid triggers ONE Qwen fallback;
if Qwen's output is also invalid, deep_scrub raises and the caller must
retain the item for retry — nothing is written outbound. The ledger records
which tier did each pass — the demo stays honest.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from house import config, scrub

DETECT_PROMPT = """You are a privacy scanner. List every span of PERSONAL
INFORMATION in the text below: person names, phone numbers, email addresses,
street addresses, school names, ID numbers. Ignore [[TOKENS]] — already handled.

Reply with ONLY a JSON array, no prose, e.g.:
[{"text": "Jane Doe", "kind": "name"}, {"text": "555-0100", "kind": "phone"}]
Reply [] if there is nothing.

TEXT:
"""


@dataclass
class ScrubResult:
    text: str
    map_hits: int
    model_spans: int
    tier: str


class SpanParseError(RuntimeError):
    """Detector output could not be parsed into a findings list. NEVER
    equivalent to 'no PII found' — the caller must fall back or fail."""


def _parse_spans(raw: str) -> list[str]:
    """FAIL-CLOSED parse. A 4B model may wrap JSON in prose/fences — that is
    tolerated — but an output with no JSON array, invalid/truncated JSON, a
    non-list top level, or unusable entries RAISES. A valid explicit [] is the
    only way to assert 'nothing found'."""
    if not isinstance(raw, str) or not raw.strip():
        raise SpanParseError("empty detector response")
    stripped = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:  # whole response is JSON: authoritative — a top-level object/scalar fails
        whole = json.loads(stripped)
        if not isinstance(whole, list):
            raise SpanParseError("detector JSON top level is not a list")
        arr = whole
    except json.JSONDecodeError:
        # Prose-wrapped output: only a top-level ARRAY may be extracted. If the
        # first structural character is '{', the model answered with an object —
        # never mine an inner array out of it.
        first_bracket = stripped.find("[")
        first_brace = stripped.find("{")
        if first_bracket == -1:
            raise SpanParseError("no JSON array in detector response") from None
        if first_brace != -1 and first_brace < first_bracket:
            raise SpanParseError("detector JSON top level is not a list") from None
        m = re.search(r"\[.*\]", stripped, re.DOTALL)
        if not m:
            raise SpanParseError("no JSON array in detector response") from None
        try:
            arr = json.loads(m.group(0))
        except json.JSONDecodeError as e:
            raise SpanParseError(f"invalid JSON in detector response: {e.msg}") from e
        if not isinstance(arr, list):
            raise SpanParseError("detector JSON is not a list")
    out: list[str] = []
    for i, item in enumerate(arr):
        if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
            out.append(item["text"])
        elif isinstance(item, str) and item.strip():
            out.append(item)
        else:
            raise SpanParseError(f"malformed detector entry at index {i}")
    return out


def _detect_via_ollama(text: str) -> list[str]:
    import httpx

    r = httpx.post(
        f"{config.OLLAMA_BASE}/api/generate",
        json={
            "model": config.GEMMA_MODEL,
            "prompt": DETECT_PROMPT + text,
            "stream": False,
            # Stay resident between the 15-min mirror cycles — a cold reload
            # under GPU contention can blow the timeout (observed live).
            "keep_alive": "2h",
            "options": {"num_predict": 512, "temperature": 0},
        },
        timeout=config.GATEWAY_TIMEOUT_S,
    )
    r.raise_for_status()
    return _parse_spans(r.json().get("response", ""))


def _detect_via_qwen(text: str) -> list[str]:
    import httpx

    r = httpx.post(
        f"{config.QWEN_BASE}/chat/completions",
        json={
            "model": config.QWEN_MODEL,
            "messages": [{"role": "user", "content": DETECT_PROMPT + text}],
            "max_tokens": 512,
            "temperature": 0,
        },
        timeout=config.GATEWAY_TIMEOUT_S,
    )
    r.raise_for_status()
    return _parse_spans(r.json()["choices"][0]["message"]["content"])


def _detect_fixture(_text: str) -> list[str]:
    path = config.REPO_ROOT / "fixtures" / "pii_findings.fixture.json"
    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
    except Exception as e:
        raise SpanParseError(f"failed to read/parse fixture JSON: {e}") from e

    if not isinstance(data, dict):
        raise SpanParseError("fixture JSON root is not an object")
    if "spans" not in data:
        raise SpanParseError("fixture JSON missing 'spans' key")
    spans = data["spans"]
    if not isinstance(spans, list):
        raise SpanParseError("fixture 'spans' is not a list")

    out: list[str] = []
    for i, item in enumerate(spans):
        if isinstance(item, dict) and isinstance(item.get("text"), str) and item["text"].strip():
            out.append(item["text"])
        else:
            raise SpanParseError(f"malformed fixture span entry at index {i}")
    return out


def detect_pii(text: str) -> tuple[list[str], str]:
    """Returns (spans, tier_used). FAIL-CLOSED: an unreachable detector or
    unparseable output triggers exactly one fallback to the other local tier;
    if that is also unusable, this RAISES — callers must not write the item."""
    if config.SIMULATED:
        return _detect_fixture(text), "fixture"
    if config.PRIVACY_TIER == "gemma":
        try:
            return _detect_via_ollama(text), "gemma"
        except Exception as e:  # noqa: BLE001 — one fallback, then fail closed
            print(f"[privacy_gateway] gemma unusable ({e}); one qwen fallback")
    return _detect_via_qwen(text), "qwen"


def deep_scrub(text: str) -> ScrubResult:
    tmap = scrub.load_map(config.TOKEN_MAP_PATH)
    t1, hits1 = scrub.apply_map(text, tmap)          # deterministic PRE
    spans, tier = detect_pii(t1)                      # local model, in-house
    t2 = scrub.redact_spans(t1, spans)                # model catches
    t3, hits2 = scrub.apply_map(t2, tmap)             # deterministic POST
    scrub.assert_clean(t3, tmap)                      # hard guarantee
    return ScrubResult(text=t3, map_hits=hits1 + hits2, model_spans=len(spans), tier=tier)


def make_pii_detector_agent():
    """The same detector as an ADK agent — exported for agent-as-a-tool use
    (model-initiated scrubbing) and for the architecture story. The guarantee
    path above calls the model deterministically instead."""
    from google.adk.agents import Agent
    from google.adk.models.lite_llm import LiteLlm

    if config.PRIVACY_TIER == "gemma":
        model = LiteLlm(model=f"ollama_chat/{config.GEMMA_MODEL}", api_base=config.OLLAMA_BASE)
    else:
        model = LiteLlm(model=f"openai/{config.QWEN_MODEL}", api_base=config.QWEN_BASE, api_key="local")
    return Agent(name="pii_detector", model=model, instruction=DETECT_PROMPT)


def pii_detector_tool():
    from google.adk.tools import AgentTool

    return AgentTool(make_pii_detector_agent())
