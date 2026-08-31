# Filmed-run evidence capsule

**STATUS: CAPTURED 06:46–06:50 PT from the live run's own evidence** (run doc,
`gcloud scheduler jobs describe`, BigQuery `runs_v` — raw copies in
`data/capture/`). One run id, every surface; all values token-space /
redacted by construction. This is the cross-reference judges can follow from
the video to the live system.

## Run `2026-08-31` (the uncut core)

| Surface | Evidence | Verified value |
|---|---|---|
| Cloud Scheduler | `hearth-morning` last-attempt status + time | lastAttemptTime 2026-08-31T13:45:00.8Z (= 06:45:00 PT), state ENABLED |
| Run doc | `trigger_source` / `triggered_by` | scheduled / sa-home@new-prompt-490003.iam.gserviceaccount.com (attempt 1, no resume — BQ `mixed_provenance=false`) |
| Run doc | `stage_status` | gathered/planned/reviewed/dispatched: all done |
| Mission Control | permalink | https://hearthbeat-369944070051.us-central1.run.app/missioncontrol?run=2026-08-31 |
| Models | ids used (from `model_usage` events) | gemini-3.5-flash + gemini-3.5-flash-lite @ location=global, 11 calls |
| Actions | dispatched (type → status) | calendar_create_event→done · send_briefing→done · notify_family_member→awaiting_approval (3 dispatched) |
| Permission slip | target / decided_via | [[P_GRANDMA]] / notified on phone at 06:46:04, decision pending (filmed tap at pickups) |
| Egress guard | checks / protected-alias matches | 11 / 0 |
| BigQuery | `runs_v` row (model_calls, cost_cents, denials) | 11 calls · 4.9906¢ · 0 denials (initial=latest=scheduled) |
| Cost | `runs_v.cost_cents` — run-scoped list-rate estimate at the verified configured rates | 4.9906¢ |

Historical `egress_block` rows (build days, Aug 30–31) are the guard blocking
our own misconfigurations — a fixture-map mirror leak, then an over-armed
placeholder-alias hash — separate from the filmed run and disclosed in the
README honesty ledger.

## Judge-mode run (local emulator, manual, separate datastore)

Judge mode uses a separate local Firestore-emulator datastore. Its date-derived
run ID can match the production date; that does not give it production
provenance and it is always labeled `manual`.

| Surface | Evidence | Value |
|---|---|---|
| Kickoff | `/trigger` response | HTTP 200; run `2026-08-31`, status `done`, attempt 1, manual, 7.4178¢ fixture estimate |
| Orchestration | fresh private clone of sanitized judged tree | `docker compose` built all four Hearthbeat images, polled agent + seeded-house readiness, and completed kickoff with exit 0 |
| Reproduction timing | two fresh-clone `--no-cache` validations on the submission host | 184.487 s and 194.845 s to successful kickoff; observed Windows/WSL/Docker timings, not an SLA |
| Runtime boundary | emulator + simulated home | Firestore emulator, the actual agent image, the fixture house mirror, and `ha-sim`; no Google credentials or household access |
| Follow-through | action poller / `ha-sim` | In normal mode the documented command keeps the stack running so its pollers can process approved actions, permission notification, and the labeled `judge_auto` continuation. The latest cold-start gate was verified through successful kickoff, not through post-kickoff device effects. |
| Ledger | file sink | Judge mode writes the same lifecycle event shapes to the `ledger` Docker volume at `/data/ledger.jsonl`, including live fixture egress checks |
