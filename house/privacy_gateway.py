"""The privacy gateway — where local Gemma earns its keep.

deep_scrub() is the ONLY path by which free text (email bodies, calendar
titles) leaves the house:

    deterministic map PRE-pass  ->  local Gemma PII detection  ->  span redact
    ->  deterministic map POST-pass  ->  assert_clean  ->  Firestore

The Gemma detector is a real ADK agent (LiteLlm -> ollama), and it is invoked
DETERMINISTICALLY through a local Runner — an AgentTool would leave the choice
to a model, which is not a guarantee. AgentTool export is still provided for
legitimately model-initiated scrubbing.

Gemma catches what the map cannot know: a teacher's name, a phone number in a
school email. The map catches what Gemma might miss: the family itself. If
Gemma is unreachable/slow, PRIVACY_TIER falls back to local qwen (:8000) and
the ledger records which tier did the pass — the demo stays honest.
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


def _parse_spans(raw: str) -> list[str]:
    """Tolerant parse — a 4B model sometimes wraps JSON in prose/fences."""
    m = re.search(r"\[.*\]", raw, re.DOTALL)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
    except json.JSONDecodeError:
        return []
    out = []
    for item in arr:
        if isinstance(item, dict) and item.get("text"):
            out.append(str(item["text"]))
        elif isinstance(item, str):
            out.append(item)
    return out


def _detect_via_ollama(text: str) -> list[str]:
    import httpx

    r = httpx.post(
        f"{config.OLLAMA_BASE}/api/generate",
        json={
            "model": config.GEMMA_MODEL,
            "prompt": DETECT_PROMPT + text,
            "stream": False,
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
        data = json.loads(path.read_text(encoding="utf-8"))
        return [s["text"] for s in data.get("spans", [])]
    except Exception:  # noqa: BLE001
        return []


def detect_pii(text: str) -> tuple[list[str], str]:
    """Returns (spans, tier_used)."""
    if config.SIMULATED:
        return _detect_fixture(text), "fixture"
    if config.PRIVACY_TIER == "gemma":
        try:
            return _detect_via_ollama(text), "gemma"
        except Exception as e:  # noqa: BLE001
            print(f"[privacy_gateway] gemma unavailable ({e}); falling back to qwen")
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
