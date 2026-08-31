# Filmed-run evidence capsule

One run id, every surface. Filled after the scheduled run; all values are
token-space / redacted by construction. This is the cross-reference judges can
follow from the video to the live system.

## Run `2026-08-31` (the uncut core)

| Surface | Evidence | Value (fill at 7:30 triage) |
|---|---|---|
| Cloud Scheduler | `hearth-morning` last-attempt status + time | «SUCCESS @ 06:4x PT» |
| Run doc | `trigger_source` / `triggered_by` | «scheduled / sa-home@new-prompt-490003.iam.gserviceaccount.com» |
| Run doc | `stage_status` | «gathered/planned/reviewed/dispatched: done» |
| Mission Control | permalink | https://hearthbeat-369944070051.us-central1.run.app/missioncontrol?run=2026-08-31 |
| Models | ids used (from `model_usage` events) | «gemini-3.5-flash, gemini-3.5-flash-lite @ location=global» |
| Actions | dispatched (type → status) | «…» |
| Permission slip | target / decided_via | «[[P_GRANDMA]] / ha_mobile or console» |
| Egress guard | checks / protected-alias matches | «N / 0» |
| BigQuery | `runs_v` row (model_calls, cost_cents, denials) | «…» |
| Cost | `runs_v.cost_cents` at corrected list rates | «…» |

Historical `egress_block` rows (2 matches, 2026-08-30) are the guard blocking
our own build misconfiguration — separate from the filmed run and disclosed in
the README honesty ledger.

## Judge-mode run (pickup P6)

| Surface | Evidence | Value |
|---|---|---|
| Kickoff | `/trigger` response | «status done, trigger_source manual» |
| ha-sim log | TV pause / calendar event / notifications | «…» |
| Ledger file | `egress_check` events with fixture hashes | «…» |
