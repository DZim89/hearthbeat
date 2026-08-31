# Filmed-run evidence capsule

**STATUS: PENDING — nothing below is publishable until copied from the exact
06:45 run's evidence (run doc, Scheduler describe, BigQuery rows) within its
own time window.** One run id, every surface; all values token-space /
redacted by construction. This is the cross-reference judges can follow from
the video to the live system.

## Run `2026-08-31` (the uncut core)

| Surface | Evidence | Value (fill at 7:30 triage) |
|---|---|---|
| Cloud Scheduler | `hearth-morning` last-attempt status + time | PENDING CAPTURE |
| Run doc | `trigger_source` / `triggered_by` | PENDING CAPTURE (expect: scheduled / the configured scheduler SA) |
| Run doc | `stage_status` | PENDING CAPTURE |
| Mission Control | permalink | https://hearthbeat-369944070051.us-central1.run.app/missioncontrol?run=2026-08-31 |
| Models | ids used (from `model_usage` events) | PENDING CAPTURE (expect: the configured 3.5 model ids) |
| Actions | dispatched (type → status) | PENDING CAPTURE |
| Permission slip | target / decided_via | PENDING CAPTURE |
| Egress guard | checks / protected-alias matches | PENDING CAPTURE |
| BigQuery | `runs_v` row (model_calls, cost_cents, denials) | PENDING CAPTURE |
| Cost | `runs_v.cost_cents` — run-scoped list-rate estimate at the verified configured rates | PENDING CAPTURE |

Historical `egress_block` rows (build days, Aug 30–31) are the guard blocking
our own misconfigurations — a fixture-map mirror leak, then an over-armed
placeholder-alias hash — separate from the filmed run and disclosed in the
README honesty ledger.

## Judge-mode run (pickup P6)

| Surface | Evidence | Value |
|---|---|---|
| Kickoff | `/trigger` response | PENDING CAPTURE |
| ha-sim log | TV pause / calendar event / notifications | PENDING CAPTURE |
| Ledger file | `egress_check` events with fixture hashes | PENDING CAPTURE |
