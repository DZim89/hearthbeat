"""Minimal Home Assistant REST client (Bearer long-lived token). REST only —
the house never opens an inbound socket; everything is polling."""

from __future__ import annotations

from typing import Any

import httpx

from house import config


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.HA_TOKEN}",
        "Content-Type": "application/json",
    }


def get_states() -> list[dict[str, Any]]:
    r = httpx.get(f"{config.HA_URL}/api/states", headers=_headers(), timeout=15)
    r.raise_for_status()
    return r.json()


def get_state(entity_id: str) -> dict[str, Any] | None:
    r = httpx.get(
        f"{config.HA_URL}/api/states/{entity_id}", headers=_headers(), timeout=10
    )
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json()


def call_service(domain: str, service: str, data: dict[str, Any]) -> Any:
    r = httpx.post(
        f"{config.HA_URL}/api/services/{domain}/{service}",
        headers=_headers(),
        json=data,
        timeout=20,
    )
    r.raise_for_status()
    return r.json()


def get_calendar_events(entity_id: str, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    r = httpx.get(
        f"{config.HA_URL}/api/calendars/{entity_id}",
        headers=_headers(),
        params={"start": start_iso, "end": end_iso},
        timeout=15,
    )
    if r.status_code == 404:
        return []
    r.raise_for_status()
    return r.json()
