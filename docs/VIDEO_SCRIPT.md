# hearthbeat — 3:50 video script (hard ceiling 4:00)

Structure: an **edited montage** with ONE clearly labeled uninterrupted live
segment. On-screen labels keep it honest: the uncut core carries a "LIVE —
UNCUT" badge with the run id; every other beat is a labeled "PICKUP" tied to
the same run id (or explicitly to the judge-mode run). Captions burned-in AND
uploaded as .srt.

## The uncut core (one continuous take, target 90–105s of the video)

**"LIVE — UNCUT · run 2026-08-31 · scheduled"** on screen throughout.
Continuous screen/camera capture, no cuts:

1. GCP console, Cloud Scheduler page, clock visible → `hearth-morning` fires.
2. Terminal alongside: Cloud Run logs stream; the run doc's
   `triggered_by: sa-home@new-prompt-490003.iam.gserviceaccount.com` shown —
   **authenticated as the dedicated Scheduler service account**.
3. Mission Control refreshes: stages light up gathered → planned → reviewed →
   dispatched; badge reads **scheduled** (green).
4. The autonomous consequences inside the same take: kid TV pauses (if playing
   at fire time) and the morning briefing lands on the phone.

VO over the core: "This is a real Cloud Scheduler cron firing, on camera, in
one take. The run authenticates the scheduler's own service-account
principal, Scheduler's run history corroborates the cron origin, and any
manual run — or manual resume — carries its own label. Watch the pipeline
argue with itself, dispatch, and the house quietly act."

## Labeled pickups (each badged "PICKUP · run 2026-08-31" unless noted)

| # | Beat | On screen | VO essence |
|---|------|-----------|------------|
| P1 | Cold open (before the core) | Quiet house b-roll; Mission Control ticking | "No chat window. The house runs its own morning standup." |
| P2 | Architecture | Diagram sweep: gatherers → planner → policy loop → dispatcher; house/cloud wall, pull arrow | ADK primitives named; "the cloud never reaches in — the house pulls." |
| P3 | Permission slip + calendar continuation | Phone close-up: Approve/Deny → tap Approve → HA calendar shows the **proposed** `[hearthbeat]` event; notification shows the **approved draft released to the household channel** | "Anything touching a person waits for a human signature. One tap: the proposed fix lands on the calendar and the approved draft is released to the family's notification channel — it never messages Grandma directly." |
| P4 | Red team | `/trigger?red_team=1` (labeled manual) → denial rows: `unlisted_action_type:front_door_unlock` on Mission Control + BQ `denials_v` | "Planted forbidden action, refused in writing. Denials are data." |
| P5 | Gemma / privacy | `ollama ps`; raw email → tokenized side-by-side; BQ: zero protected-alias matches for the filmed run; the historical `egress_block` rows shown separately and explained | "Known family names are deterministically tokenized before anything leaves the house, a local Gemma tier scans for PII we can't list, and every instrumented outbound request is checked against the protected-alias hash set. This run: zero matches — and the only rows that table has ever held are the guard catching OUR OWN build mistakes. We left the evidence in." |
| P6 | Console proof + judge mode (judge-mode run id shown) | Cloud Run service (sa-home), Scheduler SUCCESS history; `git clone` → `SIMULATED_HOME=1 docker compose up` → localhost Mission Control | "Live on Cloud Run, priced per run in BigQuery — and judges get the whole house with one command from a clean clone." |
| P7 | Close | Thumbnail card → URLs | "hearthbeat. The house that runs its own morning." |

## Integrity rules for the edit
- The "LIVE — UNCUT" badge appears ONLY on the continuous take; everything
  else carries a PICKUP badge. Nothing implies the pickups happened inside the
  uncut segment.
- Upload the final demo as **publicly visible** on YouTube or Vimeo. Private
  and unlisted visibility do not satisfy the live Devpost submission gate.
- All run-scoped claims cite the run id on screen.
- No absolute cost figure in VO; Mission Control's per-run figure is visible.
- Final frame-scan for PII before upload (terminal text included).

## Assembly plan (9:15–10:15)
ffmpeg straight cuts, burned-in captions + `.srt`; target 3:50. If the TV was
not playing at 6:45, the media_pause beat moves to a PICKUP with its own
labeled manual run — never blended into the uncut core.
