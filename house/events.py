"""House-side ledger emission — same sinks as the cloud plugin, so Gemma's
work shows up in the same BigQuery table (or judge-mode JSONL)."""

from __future__ import annotations

import time
from typing import Any

from app.ledger import LedgerSink, make_sink

_sink: LedgerSink | None = None


def emit(event_type: str, run_id: str = "house", **attrs: Any) -> None:
    global _sink
    try:
        if _sink is None:
            _sink = make_sink()
        _sink.emit(
            {
                "event_type": event_type,
                "run_id": run_id,
                "trigger_source": "house",
                "ts_ms": int(time.time() * 1000),
                **attrs,
            }
        )
        _sink.flush()
    except Exception as e:  # noqa: BLE001
        print(f"[house.events] emit failed for {event_type}: {e}")
