# DEMO runbook — submit day (Aug 31)

Integrity rule: the money shot is the REAL 6:45 AM Cloud Scheduler firing
(`hearth-morning`, run id `2026-08-31`). Manual runs are labeled `manual`
structurally and are never presented as scheduled. Test runs use suffixed run
ids.

## Verified pre-run state (03:18 AM)
- Local Calendar (`calendar.hearthbeat_family`), approval helper, bridge
  automation, and the disclosed collision fixture were provisioned earlier.
  Revalidate the house poller, phone path, and demo fixture at 6:35 before
  recording; `runs/2026-08-31` was verified unclaimed at this checkpoint.
- Cloud Run revision `hearthbeat-00015-rt7` serves 100% traffic; `/health` and
  run-scoped Mission Control return HTTP 200; Scheduler remains enabled for
  `45 6 * * *` in `America/Los_Angeles`.
- Repo pushed PRIVATE. The current tracked tree passes the protected-alias and
  source-context scans, but the one-time noreply history rewrite is still a
  required public-release gate.
- Evidence backup: Windows task `hearth-20260831-mc-snapshots-win` is scheduled
  for 6:44, can wake the machine, and writes 20 run-scoped Mission Control HTML
  snapshots to gitignored `data/evidence/cron645/`. Its HTTP/path preflight
  passed. These snapshots are evidence backup, **not video footage**.

## 6:45 AM — the scheduled run (live footage required for the money shot)
- Be ready by 6:35. Start the continuous capture no later than 6:43 with the
  GCP Scheduler job, a visible clock, Cloud Run logs, Mission Control, and the
  public-safe phone consequence arranged before recording begins.
- Film the uninterrupted core per `docs/VIDEO_SCRIPT.md`; do not stop, splice,
  or change sources inside that segment. The background HTML snapshots will
  preserve evidence but cannot replace this recording.
- If the scheduled firing is missed or fails, use the Cloud Scheduler
  console's authenticated manual-run action as the truthful backup and label
  the resulting take **manual**. Never relabel a post-run dashboard tour or a
  manual recovery as an uncut scheduled execution.

## 8:15–9:15 — pickups (see VIDEO_SCRIPT pickup table)
Red-team labeled manual run; Gemma terminal beat; permission-slip tap +
calendar continuation; judge-mode clean-clone beat; 3:2 thumbnail already at
docs/hearthbeat-thumbnail.png. docs/EVIDENCE.md stays PENDING until each cell
is copied from the exact 06:45 run's own evidence — never pre-filled.

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
