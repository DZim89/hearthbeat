"""Vertex canary: proves the exact model IDs + thinking config work in this
project before anything else is built on them. Run any time:

    python -m infra.canary
"""

from __future__ import annotations

import os
import sys

from google import genai
from google.genai import types

PROJECT = os.environ.get("GOOGLE_CLOUD_PROJECT", "new-prompt-490003")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]


def probe(client: genai.Client, model: str) -> tuple[bool, str]:
    for cfg_name, cfg in [
        (
            "thinking_budget",
            types.GenerateContentConfig(
                max_output_tokens=2048,
                thinking_config=types.ThinkingConfig(thinking_budget=256),
            ),
        ),
        (
            "no_thinking_config",
            types.GenerateContentConfig(max_output_tokens=2048),
        ),
    ]:
        try:
            resp = client.models.generate_content(
                model=model,
                contents="Reply with exactly: HEARTHBEAT-CANARY-OK",
                config=cfg,
            )
            text = (resp.text or "").strip()
            um = resp.usage_metadata
            usage = (
                f"prompt={um.prompt_token_count} out={um.candidates_token_count} "
                f"thoughts={getattr(um, 'thoughts_token_count', None)}"
            )
            if text:
                return True, f"{cfg_name}: {text[:40]!r} ({usage})"
            return False, f"{cfg_name}: EMPTY TEXT ({usage})"
        except Exception as e:  # noqa: BLE001 — canary reports everything
            msg = str(e)[:160]
            if "thinking" in msg.lower() or "INVALID_ARGUMENT" in msg:
                continue  # try next config shape
            return False, f"{cfg_name}: {msg}"
    return False, "no config shape worked"


def main() -> int:
    client = genai.Client(vertexai=True, project=PROJECT, location=LOCATION)
    failures = 0
    for model in MODELS:
        ok, detail = probe(client, model)
        print(f"{'PASS' if ok else 'FAIL'}  {model:24s} {detail}")
        failures += 0 if ok else 1
    return failures


if __name__ == "__main__":
    sys.exit(main())
