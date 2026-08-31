# Filmed-run evidence capsule

**STATUS: CAPTURED 06:46–06:50 PT from the live run's own evidence** (run doc,
`gcloud scheduler jobs describe`, BigQuery `runs_v` — raw copies in
`data/capture/`). One run id, every surface; all values token-space /
redacted by construction. This is the cross-reference judges can follow from
the video to the live system.

## Run `2026-08-31` (the uncut core)

| Surface | Evidence | Value (fill at 7:30 triage) |
|---|---|---|
| Cloud Scheduler | `hearth-morning` last-attempt status + time | lastAttemptTime 2026-08-31T13:45:00.8Z (= 06:45:00 PT), state ENABLED |
| Run doc | `trigger_source` / `triggered_by` | scheduled / sa-home@new-prompt-490003.iam.gserviceaccount.com (attempt 1, no resume — BQ `mixed_provenance=false`) |
| Run doc | `stage_status` | gathered/planned/reviewed/dispatched: all done |
| Mission Control | permalink | https://hearthbeat-369944070051.us-central1.run.app/missioncontrol?run=2026-08-31 |
| Models | ids used (from `model_usage` events) | gemini-3.5-flash + gemini-3.5-flash-lite @ location=global, 11 calls |
| Actions | dispatched (type → status) | calendar_create_event→done · send_briefing→done · notify_family_member→awaiting_approval (3 dispatched; house executed within 79s of fire) |
| Permission slip | target / decided_via | [[P_GRANDMA]] / notified on phone at 06:46:04, decision pending (filmed tap at pickups) |
| Egress guard | checks / protected-alias matches | 11 / 0 |
| BigQuery | `runs_v` row (model_calls, cost_cents, denials) | 11 calls · 4.9906¢ · 0 denials (initial=latest=scheduled) |
| Cost | `runs_v.cost_cents` — run-scoped list-rate estimate at the verified configured rates | 4.9906¢ |

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
