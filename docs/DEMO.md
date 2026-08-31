# DEMO runbook — filming night (Aug 30) + submit morning (Aug 31)

> **REV 2 (00:15 Aug 31): the evening window slipped — the plan's pre-authorized
> fallback is ACTIVE.** The 6:45 AM production cron is the money shot. House is
> fully armed autonomously: Local Calendar + helper + approval bridge live,
> collision seeded (clean), house processes running, stale test actions purged,
> repo pushed PRIVATE with scrubbed history, Mission Control capture loop armed
> for 6:43–6:53. If the 6:30 alarm is missed, nothing breaks: film everything at
> 8:15 pickups off the live Mission Control + Scheduler history + Cloud logs.

Integrity rule, non-negotiable: **the money shot is a real Cloud Scheduler
firing.** A manual `/trigger` run is labeled `manual` everywhere and is never
presented as scheduled. Test runs use suffixed run_ids (`2026-08-30-e2eN`) so
the real date-keyed run doc stays untouched until the camera is rolling.

## Pre-flight (done during the day, Claude)
- [x] Live E2E on real Vertex/Firestore (e2e3): 4 stages, red-team denial row,
      egress 13 checks / 0 matches, 1.7¢.
- [x] Cloud Run deployed + cloud E2E via /trigger (cloud2, 1.3¢); /health green.
- [x] Pub/Sub → BigQuery selftest row landed; 5 views created.
- [x] gemma3 pulled, warm ~2.5 s, load-bearing in deep_scrub (qwen fallback armed).
- [x] Real token map written (gitignored); real-hash egress guard in deploy env
      — and it CAUGHT a real leak (fixture-map mirror) during the build.
- [x] **Scheduled dry-fire PASSED** (17:04 one-off): OIDC verified,
      `trigger_source=scheduled`, `triggered_by=sa-home@…`, all 4 stages, 1.33¢.
      One-off job deleted; `runs/2026-08-30` gets `infra/preshot_cleanup.py` at 22:50.
- [x] **Kill-and-resume PROVEN** (drill4): SIGKILL mid-run → stale-heartbeat
      takeover on re-fire → `attempt: 2, status: done`; drill3 shows checkpoint
      persistence; zero duplicate actions. Re-runnable on camera at 8:15 AM.
- [x] Actionable notification delivered to the phone (transport test).

## Donny acts — evening (each ≤5 min)
1. **21:00** `! sudo apt-get install -y docker.io docker-compose-v2 && sudo chmod 666 /var/run/docker.sock`
   (judge-mode compose testing overnight).
2. **21:05** GitHub: create PRIVATE repo `hearthbeat`, then Claude pushes.
3. **21:10** HA UI: Settings → Devices & Services → **Add integration → Local
   Calendar**, name it `hearthbeat family` (entity `calendar.hearthbeat_family`).
4. **21:12** HA UI: Settings → Helpers → **Create helper → Text**, name
   `hearthbeat last approval` (entity `input_text.hearthbeat_last_approval`).
5. **21:15** Edit `config/token_map.local.json`: add Grandma's real first name
   to the `[[P_GRANDMA]]` aliases; add the school name as a new entry if wanted.
   (File is gitignored; never leaves the machine.)
6. **21:20** Confirm phone: HA companion app notifications ON.

After 3+4, Claude (no Donny needed): installs the approval-bridge automation
via REST (docs/ha_automation.yaml), seeds the calendar collision (soccer vs
dinner at Grandma's, disclosed as seeded), sends a hello-world actionable
notification for Donny to tap once as transport proof, re-exports egress
hashes if the map changed, updates the Cloud Run env, starts
`python -m house.run_all` under nohup, and re-runs a full suffixed E2E.

## The money shot (camera)
- **22:45** Donny: camera rig. Frame: GCP console (Scheduler jobs page) +
  a terminal tailing Cloud Run logs + clock visible. Phone on desk. Living
  Room TV **playing something** (it is the parental-action target).
- **22:50** Claude: creates the one-off REAL job → `bash infra/setup.sh oneoff
  <SERVICE_URL> "23:15"`. Deploy freeze from now until filmed.
- **23:10** OBS + camera rolling.
- **23:15** `hearth-oneoff` fires `/run` with OIDC → `trigger_source=scheduled`.
  On camera: console job state flip → logs stream → Mission Control stages
  light up → **the TV pauses** → briefing lands on the phone.
- **~23:20** Permission slip notification arrives (Grandma message). Donny taps
  **Approve** on camera → poller executes → calendar write visible in HA.
- **23:30** Claude: delete `hearth-oneoff`; unfreeze.
- Backup: one reschedule to 23:45; else the 6:45 AM production cron is the
  money shot (alarm 6:30, OBS auto-record 6:43 armed regardless).

## Red-team + durability beats (tonight if ahead, else 8:15 AM)
- Red team: `/trigger?red_team=1&run_id=<date>-redteam` → planted
  `front_door_unlock` → denial rows on Mission Control + `denials_v` in BQ.
- Kill-and-resume: start a suffixed run, kill the service mid-loop
  (`gcloud run services update ... --clear-env-vars=DUMMY` forces restart, or
  local uvicorn kill), re-fire → takeover + resume from checkpoints on camera.
- Zero-egress: BQ console → `SELECT * FROM agent_logs.egress_violations_v`
  → **0 rows**; `SELECT * FROM privacy_tier_v` shows Gemma's catches.

## Submit morning — see the plan's schedule (7:30 → 12:30 PT)
Filming pickups 8:15–9:15 · edit 9:15–10:15 · YouTube 10:15 · repo public
10:45 (AFTER the PII scan gates green) · Devpost 11:15 · bonuses 11:45 ·
**SUBMIT ≤ 12:30**.
