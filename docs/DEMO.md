# DEMO runbook — submit day (Aug 31)

Integrity rule: the money shot is the REAL 6:45 AM Cloud Scheduler firing
(`hearth-morning`, run id `2026-08-31`). Manual runs are labeled `manual`
structurally and are never presented as scheduled. Test runs use suffixed run
ids.

## Captured production proof

- The uninterrupted recorder started at 6:43:49 AM PDT, before the scheduled
  trigger. Run `2026-08-31` started at 6:45:00 and completed at 6:45:51.
- Cloud Scheduler remained enabled on `45 6 * * *` in
  `America/Los_Angeles`; its last-attempt timestamp corroborates the filmed
  run's `scheduled` label and configured OIDC invoker principal.
- Mission Control reached `done` with all four stages complete. The calendar
  and briefing actions completed autonomously; the family notification stayed
  `awaiting_approval` and required a human decision.
- The run-scoped evidence is 11 instrumented model calls, zero configured
  protected-alias matches, and an estimated list-rate model cost of 4.9906¢.
- The preserved source recording is 1920×1080, 30 fps, 15:00, SHA-256
  `8083BB3E2D924E0D2E568D073B24FDEF19C0813948BFA34FBD4250E47AD9FD0C`.

## Preserved uncut core

- `live-core-uncut.mp4` is an 85-second, 1× extraction from one continuous
  source interval. It begins before the trigger appears and ends only after
  Mission Control reaches `done`; there are no internal edits.
- A consistent crop removes unrelated browser chrome and avoids the malformed
  nested display token in the longer briefing. The overlay remains
  `LIVE · UNCUT · 1× · RUN 2026-08-31` throughout.
- Pickups are labeled separately and never presented as part of the live take.

## Final narration and optional pickups (see VIDEO_SCRIPT.md)

Record the personal-friction hook and clean narration first. Add only a short,
clearly labeled permission-boundary or judge-mode pickup if it materially
improves legibility. The fixed live core, run-evidence card, architecture
pickup, closing card, and 3:2 thumbnail are already prepared.

## Final assembly and submission

- Record narration, assemble the montage around the fixed uncut core, generate
  English captions, and complete a frame-by-frame public-data scan.
- Upload as a publicly visible YouTube video, verify playback/captions while
  logged out, and confirm the duration is under four minutes.
- Run final tests and repository scans, change the repository to public, and
  verify a credential-free anonymous clone.
- Complete Devpost from `SUBMISSION.md`, including the exact run permalink and
  already-published bonus links; verify all five steps in Preview.
- Submit by 1:00 PM PDT. The 5:00 PM official deadline remains a recovery
  window, not the working target.
