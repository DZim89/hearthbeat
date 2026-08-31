# DEMO runbook — submit day (Aug 31)

Integrity rule: the money shot is the REAL 6:45 AM Cloud Scheduler firing
(`hearth-morning`, run id `2026-08-31`). Manual runs are labeled `manual`
structurally and are never presented as scheduled. Test runs use suffixed run
ids.

## Current state (00:45 AM)
- House fully armed autonomously: Local Calendar (`calendar.hearthbeat_family`)
  + approval helper + bridge automation live; the disclosed collision seeded
  (two events, clean); house processes (mirror / ingest / poller) running;
  stale test actions purged; `runs/2026-08-31` verified unclaimed.
- Deployed revision carries all 22 review fixes; final cloud E2E `done`.
- Repo pushed PRIVATE (history PII-scrubbed, verified `git log -S` clean).
- Capture: session wake scheduled 6:44 → Mission Control snapshots + run-doc,
  scheduler-state, and BigQuery evidence saved to `data/capture/`.

## 6:45 AM — the scheduled run (live footage optional)
- If awake (alarm 6:30): camera on GCP Scheduler console + phone from 6:43;
  film the UNCUT CORE per docs/VIDEO_SCRIPT.md.
- If not: nothing breaks. The run executes; Mission Control keeps displaying
  it all morning; Cloud Logging holds the fire-time logs; Scheduler history
  shows SUCCESS — the uncut core is then screen-captured live at pickups
  (Mission Control + logs are still the real scheduled run; only room b-roll
  is lost).

## 8:15–9:15 — pickups (see VIDEO_SCRIPT pickup table)
Red-team labeled manual run; Gemma terminal beat; permission-slip tap +
calendar continuation; judge-mode clean-clone beat; 3:2 thumbnail already at
docs/hearthbeat-thumbnail.png. Evidence capsule filled in docs/EVIDENCE.md.

## 9:15 → 12:30 — assembly and submission
- 9:15–10:15 video edit (montage + labeled uncut core; PII frame-scan).
- 10:15 YouTube upload, PUBLIC, captions verified, ≤4:00 confirmed.
- 10:45 final scans (`pytest`, fixture contamination grep, `git log -S` name
  scan, working-tree PII grep) → **repo public flip** → verify incognito.
- 11:15 Devpost fill from SUBMISSION.md (+ the scheduled-run permalink
  `…/missioncontrol?run=2026-08-31`), save draft per section.
- 11:45 bonuses: dev.to publish, #AllThingsAgenticHackathon post, links back.
- 12:10 incognito link sweep → **SUBMIT ≤ 12:30** (13:00 internal hard
  ceiling; 5:00 PM Devpost deadline is the disaster valve only).
