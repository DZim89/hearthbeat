"""Model factory: verified Vertex wiring + judge-mode fixture replay.

Canary-verified facts this module encodes (see infra/canary.py):
  - gemini-3.5-flash and gemini-3.5-flash-lite answer ONLY at location=global
    in this project (us-central1 404s every 3.5 id).
  - Tiny max_output_tokens + default thinking config => thinking consumes the
    whole budget and .text comes back EMPTY. So: floor max_output_tokens at
    2048 and always set an explicit ThinkingConfig.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from google.adk.models import BaseLlm, Gemini
from google.adk.models.llm_response import LlmResponse
from google.genai import types as genai_types
from pydantic import PrivateAttr

MIN_OUTPUT_TOKENS = 2048

GENCFG_PLANNER = genai_types.GenerateContentConfig(
    temperature=0.3,
    max_output_tokens=8192,
    thinking_config=genai_types.ThinkingConfig(thinking_budget=1024),
)
GENCFG_TERSE = genai_types.GenerateContentConfig(
    temperature=0.1,
    max_output_tokens=MIN_OUTPUT_TOKENS,
    thinking_config=genai_types.ThinkingConfig(thinking_budget=0),
)

for _cfg in (GENCFG_PLANNER, GENCFG_TERSE):
    assert (_cfg.max_output_tokens or 0) >= MIN_OUTPUT_TOKENS, (
        "max_output_tokens below the verified floor — empty-text trap"
    )


def use_fixtures() -> bool:
    return os.environ.get("SIMULATED_HOME") == "1" and os.environ.get("JUDGE_LLM", "fixture") != "live"


def model_for(role: str, agent_name: str) -> BaseLlm | str:
    """role: PLANNER | CRITIC | GATHERER — resolved via MODEL_<role> env."""
    if use_fixtures():
        return FixtureLlm(model="fixture", agent_name=agent_name)
    model_id = os.environ.get(f"MODEL_{role.upper()}", "gemini-3.5-flash")
    return Gemini(
        model=model_id,
        retry_options=genai_types.HttpRetryOptions(attempts=3),
    )


class FixtureLlm(BaseLlm):
    """Replays recorded LlmResponses (fixtures/llm/<agent>/<idx>.json).

    Recording happens automatically during a real run with RECORD_LLM=1 (see
    LedgerPlugin.after_model_callback). Tool calls still execute for real in
    judge mode — against the Firestore emulator seeded with the same fixtures —
    so the recorded call sequence replays deterministically.
    """

    agent_name: str = "unknown"
    _call_index: int = PrivateAttr(default=0)

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"fixture.*"]

    async def generate_content_async(self, llm_request, stream: bool = False):
        base = Path(os.environ.get("LLM_FIXTURES_DIR", "fixtures/llm")) / self.agent_name
        path = base / f"{self._call_index:03d}.json"
        self._call_index += 1
        if path.exists():
            yield LlmResponse.model_validate_json(path.read_text(encoding="utf-8"))
            return
        # Graceful degradation: no recording for this call — return a plain
        # text response so the pipeline keeps moving and the gap is visible.
        yield LlmResponse(
            content=genai_types.Content(
                role="model",
                parts=[
                    genai_types.Part(
                        text=json.dumps(
                            {
                                "summary": f"[fixture missing: {path}]",
                                "briefing_md": "Fixture gap — re-record with RECORD_LLM=1.",
                                "actions": [],
                            }
                        )
                    )
                ],
            )
        )
