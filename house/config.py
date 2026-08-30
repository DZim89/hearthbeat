"""Shared config for the house-side processes (DadsPC WSL / judge container).

Secrets come from house/.env (gitignored) or, on the real house machine, fall
back to the operator's local agent vault. NOTHING here ever reaches the repo
or the cloud: HA tokens and the real token map stay on this side of the wall.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / "house" / ".env")
load_dotenv(REPO_ROOT / ".env")

SIMULATED = os.environ.get("SIMULATED_HOME") == "1"
HOSTNAME = socket.gethostname()


def _from_vault(key: str) -> str:
    """Operator-machine fallback: the local agent vault (never in the repo)."""
    path = Path(
        os.environ.get(
            "AGENT_VAULT_PATH", Path.home() / ".config" / "agent-memory" / "vault.json"
        )
    )
    try:
        return str(json.loads(path.read_text(encoding="utf-8")).get(key, ""))
    except Exception:  # noqa: BLE001
        return ""


HA_URL = os.environ.get("HA_URL") or (
    "http://ha-sim:8123" if SIMULATED else _from_vault("HASS_URL")
)
HA_TOKEN = os.environ.get("HA_TOKEN") or ("judge" if SIMULATED else _from_vault("HASS_TOKEN"))

TOKEN_MAP_PATH = Path(
    os.environ.get("TOKEN_MAP_PATH")
    or (
        REPO_ROOT / "fixtures" / "token_map.fixture.json"
        if SIMULATED
        else REPO_ROOT / "config" / "token_map.local.json"
    )
)

# HA notify service that reaches the household lead's phone (companion app),
# e.g. "mobile_app_<device>". Set in house/.env on the real house.
NOTIFY_SERVICE = os.environ.get("NOTIFY_SERVICE", "hearth_test")
CALENDAR_ENTITY = os.environ.get("CALENDAR_ENTITY", "calendar.hearthbeat_family")
APPROVAL_HELPER = os.environ.get("APPROVAL_HELPER", "input_text.hearthbeat_last_approval")

WATCH_DIR = Path(os.environ.get("WATCH_DIR", REPO_ROOT / "data" / "school_inbox"))
MIRROR_SECONDS = int(os.environ.get("MIRROR_SECONDS", "900"))
POLL_SECONDS = int(os.environ.get("POLL_SECONDS", "20"))
JUDGE_AUTO_APPROVE_SECONDS = int(os.environ.get("JUDGE_AUTO_APPROVE_SECONDS", "30"))

# Entities worth mirroring (prefix match), beyond anything named in the map.
SNAPSHOT_PREFIXES = tuple(
    p.strip()
    for p in os.environ.get(
        "SNAPSHOT_PREFIXES",
        "media_player.,person.,calendar.,input_text.hearthbeat",
    ).split(",")
    if p.strip()
)
ENERGY_KEYWORDS = ("energy", "power_usage", "grid_power")

# Privacy tier: local Gemma via ollama, deterministic qwen fallback.
PRIVACY_TIER = os.environ.get("PRIVACY_TIER", "gemma")
OLLAMA_BASE = os.environ.get("OLLAMA_BASE", "http://127.0.0.1:11434")
GEMMA_MODEL = os.environ.get("GEMMA_MODEL", "gemma3")
QWEN_BASE = os.environ.get("QWEN_BASE", "http://127.0.0.1:8000/v1")
QWEN_MODEL = os.environ.get("QWEN_MODEL", "qwen2.5-7b")
GATEWAY_TIMEOUT_S = int(os.environ.get("GATEWAY_TIMEOUT_S", "120"))
