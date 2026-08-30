"""Judge-mode fake Home Assistant — the same REST surface the real house
exposes, seeded from fixtures. Service calls mutate in-memory state so the
demo visibly 'happens': the kid TV pauses, the calendar gains the fix event,
notifications print to the container log."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request

REPO_ROOT = Path(__file__).resolve().parent.parent

app = FastAPI(title="ha-sim")

STATES: dict[str, dict[str, Any]] = {}
CALENDAR: list[dict[str, Any]] = []
SERVICE_LOG: list[dict[str, Any]] = []


def _load() -> None:
    snap = json.loads((REPO_ROOT / "fixtures" / "ha_snapshot.json").read_text())
    for s in snap:
        STATES[s["entity_id"]] = s
    CALENDAR.extend(json.loads((REPO_ROOT / "fixtures" / "calendar.json").read_text()))


_load()


@app.get("/api/")
async def health() -> dict[str, str]:
    return {"message": "API running."}


@app.get("/api/states")
async def states() -> list[dict[str, Any]]:
    return list(STATES.values())


@app.get("/api/states/{entity_id}")
async def state(entity_id: str) -> dict[str, Any]:
    return STATES.get(
        entity_id, {"entity_id": entity_id, "state": "", "attributes": {}}
    )


@app.get("/api/calendars/{entity_id}")
async def calendar(entity_id: str) -> list[dict[str, Any]]:
    return CALENDAR


@app.post("/api/services/{domain}/{service}")
async def call_service(domain: str, service: str, request: Request) -> list:
    data = await request.json()
    SERVICE_LOG.append({"domain": domain, "service": service, "data": data})
    print(f"[ha-sim] service call: {domain}.{service} {json.dumps(data)[:200]}")

    if domain == "media_player" and service == "media_pause":
        eid = data.get("entity_id", "")
        if eid in STATES:
            STATES[eid]["state"] = "paused"
            print(f"[ha-sim] ▶⏸  {eid} is now PAUSED")
    elif domain == "calendar" and service == "create_event":
        CALENDAR.append(
            {
                "summary": data.get("summary", ""),
                "start": {"dateTime": data.get("start_date_time", "")},
                "end": {"dateTime": data.get("end_date_time", "")},
                "description": data.get("description", ""),
            }
        )
        print(f"[ha-sim] 📅 calendar event created: {data.get('summary')}")
    elif domain == "notify":
        print(f"[ha-sim] 📱 NOTIFICATION → {service}: {data.get('title')} | {data.get('message')}")
    elif domain == "input_text" and service == "set_value":
        eid = data.get("entity_id", "")
        STATES.setdefault(eid, {"entity_id": eid, "attributes": {}})["state"] = data.get(
            "value", ""
        )
    return []


@app.get("/service_log")
async def service_log() -> list[dict[str, Any]]:
    return SERVICE_LOG
