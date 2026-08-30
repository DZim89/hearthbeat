"""Observability ledger — ONE plugin, every lifecycle event, two sinks.

Every run emits a stream of events (run_started, step_completed, model_usage,
egress_check, policy_denial, action_dispatched, run_completed, …):

  production : Pub/Sub topic `agent-events` -> native BigQuery subscription
               -> agent_logs.agent_events   (DLQ: agent-events-dlq)
  judge mode : JSONL file on the compose volume — the emission code is
               byte-identical, only the sink differs.

The before_model hook is also the cloud-side EGRESS GUARD: it scans every
outbound model request against salted hashes of the family's real names
(EGRESS_ALIAS_HASHES). The cloud can prove nothing private is leaving without
ever holding a real name in plaintext. A match hard-fails the run.
"""

from __future__ import annotations

import json
import os
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml
from google.adk.plugins import BasePlugin

from house.scrub import scan_hashed

# Module-level per-run cost accumulator (single-process service; also persisted
# to the run doc at each checkpoint). PolicyGate reads this for budget checks.
RUN_COST_MICROCENTS: dict[str, int] = defaultdict(int)

# The plugin serving the currently-executing run (set by runcontrol.execute_run)
# so pure-code agents (PolicyGate, Dispatcher) can emit through the same sink.
ACTIVE: "LedgerPlugin | None" = None


def _now_ms() -> int:
    return int(time.time() * 1000)


class LedgerSink:
    def emit(self, event: dict[str, Any]) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    def flush(self) -> None:
        pass


class FileSink(LedgerSink):
    def __init__(self, path: str | None = None):
        self.path = Path(path or os.environ.get("LEDGER_FILE", "data/ledger.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, event: dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")


class PubSubSink(LedgerSink):
    def __init__(self) -> None:
        from google.cloud import pubsub_v1  # lazy: judge mode never imports this

        self._publisher = pubsub_v1.PublisherClient()
        self._topic = self._publisher.topic_path(
            os.environ["GOOGLE_CLOUD_PROJECT"],
            os.environ.get("PUBSUB_TOPIC", "agent-events"),
        )
        self._futures: list[Any] = []

    def emit(self, event: dict[str, Any]) -> None:
        data = json.dumps(event, default=str).encode("utf-8")
        fut = self._publisher.publish(
            self._topic,
            data,
            event_type=str(event.get("event_type", "")),
            run_id=str(event.get("run_id", "")),
        )
        self._futures.append(fut)

    def flush(self) -> None:
        # Cloud Run throttles CPU after the response returns — block here so no
        # batched publish is silently lost.
        for fut in self._futures:
            fut.result(timeout=10)
        self._futures.clear()


def make_sink() -> LedgerSink:
    if os.environ.get("LEDGER_SINK", "pubsub" if os.environ.get("K_SERVICE") else "file") == "pubsub":
        return PubSubSink()
    return FileSink()


def _prices() -> dict[str, dict[str, float]]:
    path = Path(os.environ.get("PRICES_FILE", "config/prices.yaml"))
    if not path.exists():
        return {"default": {"input_usd_per_1m": 0.30, "output_usd_per_1m": 2.50}}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    table = dict(raw.get("models", {}))
    table["default"] = raw.get("default", {"input_usd_per_1m": 0.30, "output_usd_per_1m": 2.50})
    return table


class LedgerPlugin(BasePlugin):
    """Global lifecycle hooks -> ledger events + egress guard + cost meter."""

    def __init__(self, run_id: str, trigger_source: str, sink: LedgerSink | None = None):
        super().__init__(name="ledger_plugin")
        self.run_id = run_id
        self.trigger_source = trigger_source
        self.sink = sink or make_sink()
        self.prices = _prices()
        self.egress_salt = os.environ.get("EGRESS_SALT", "")
        self.alias_hashes = {
            h for h in os.environ.get("EGRESS_ALIAS_HASHES", "").split(",") if h
        }
        self.record_dir = (
            Path("fixtures/llm") if os.environ.get("RECORD_LLM") == "1" else None
        )
        self._record_counters: dict[str, int] = defaultdict(int)
        self.egress_checks = 0
        self.egress_matches = 0

    # ---- emission ----------------------------------------------------------

    def _emit(self, event_type: str, **attrs: Any) -> None:
        try:
            self.sink.emit(
                {
                    "event_type": event_type,
                    "run_id": self.run_id,
                    "trigger_source": self.trigger_source,
                    "ts_ms": _now_ms(),
                    **attrs,
                }
            )
        except Exception as e:  # noqa: BLE001 — observability must not kill runs
            print(f"[ledger] emit failed for {event_type}: {e}")

    def emit_public(self, event_type: str, **attrs: Any) -> None:
        """For other modules (gate, dispatcher) to write through the same sink."""
        self._emit(event_type, **attrs)

    # ---- lifecycle hooks ---------------------------------------------------

    async def before_run_callback(self, *, invocation_context):
        self._emit("run_started")
        return None

    async def after_run_callback(self, *, invocation_context) -> None:
        self._emit(
            "run_completed",
            cost_microcents=RUN_COST_MICROCENTS.get(self.run_id, 0),
            cost_cents=round(RUN_COST_MICROCENTS.get(self.run_id, 0) / 1_000_000, 4),
        )
        self.sink.flush()

    async def after_agent_callback(self, *, agent, callback_context):
        self._emit("step_completed", agent=agent.name)
        try:
            from app import runcontrol

            runcontrol.on_agent_complete(self.run_id, agent.name, callback_context)
        except Exception as e:  # noqa: BLE001
            print(f"[ledger] checkpoint hook failed after {agent.name}: {e}")
        return None

    async def before_model_callback(self, *, callback_context, llm_request):
        text = _request_text(llm_request)
        if self.alias_hashes:
            matches = scan_hashed(text, self.egress_salt, self.alias_hashes)
            self.egress_checks += 1
            self.egress_matches += matches
            if matches:
                self._emit(
                    "egress_block",
                    agent=callback_context.agent_name,
                    matches=matches,
                )
                self.sink.flush()
                raise RuntimeError(
                    f"EGRESS GUARD: {matches} token(s) in the outbound model request "
                    f"match a protected family alias hash — refusing the model call."
                )
            self._emit(
                "egress_check",
                agent=callback_context.agent_name,
                chars_scanned=len(text),
                matches=0,
            )
        return None

    async def after_model_callback(self, *, callback_context, llm_response):
        agent = callback_context.agent_name
        usage = getattr(llm_response, "usage_metadata", None)
        if usage is not None:
            model_version = getattr(llm_response, "model_version", "") or "default"
            price = self.prices.get(model_version, self.prices["default"])
            p_in = int(getattr(usage, "prompt_token_count", 0) or 0)
            p_out = int(getattr(usage, "candidates_token_count", 0) or 0)
            p_thought = int(getattr(usage, "thoughts_token_count", 0) or 0)
            micro = round(
                p_in * price["input_usd_per_1m"] * 100
                + (p_out + p_thought) * price["output_usd_per_1m"] * 100
            )
            RUN_COST_MICROCENTS[self.run_id] += micro
            self._emit(
                "model_usage",
                agent=agent,
                model=model_version,
                prompt_tokens=p_in,
                output_tokens=p_out,
                thought_tokens=p_thought,
                cost_microcents=micro,
            )
        if self.record_dir is not None:
            try:
                idx = self._record_counters[agent]
                self._record_counters[agent] += 1
                d = self.record_dir / agent
                d.mkdir(parents=True, exist_ok=True)
                (d / f"{idx:03d}.json").write_text(
                    llm_response.model_dump_json(exclude_none=True), encoding="utf-8"
                )
            except Exception as e:  # noqa: BLE001
                print(f"[ledger] RECORD_LLM failed for {agent}: {e}")
        return None

    async def on_model_error_callback(self, *, callback_context, llm_request, error):
        self._emit("model_error", agent=callback_context.agent_name, error=str(error)[:300])
        return None

    async def on_agent_error_callback(self, *, agent, callback_context, error) -> None:
        self._emit("agent_error", agent=agent.name, error=str(error)[:300])

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        self._emit("tool_completed", tool=tool.name, agent=tool_context.agent_name)
        return None


def _request_text(llm_request: Any) -> str:
    """Every text part headed to the model — system instruction + contents."""
    chunks: list[str] = []
    cfg = getattr(llm_request, "config", None)
    si = getattr(cfg, "system_instruction", None) if cfg else None
    if isinstance(si, str):
        chunks.append(si)
    for content in getattr(llm_request, "contents", None) or []:
        for part in getattr(content, "parts", None) or []:
            t = getattr(part, "text", None)
            if t:
                chunks.append(t)
    return "\n".join(chunks)
