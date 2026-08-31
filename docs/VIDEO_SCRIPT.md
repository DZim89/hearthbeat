# hearthbeat — 3:45 video script (hard ceiling 4:00)

Structure: an **edited montage** with ONE clearly labeled uninterrupted live
segment. On-screen labels keep it honest: the uncut core carries a "LIVE —
UNCUT" badge with the run id; every other beat is a labeled "PICKUP" tied to
the same run id (or explicitly to the judge-mode run). Captions burned-in AND
uploaded as .srt.

## Exact edit clock

| Time | Length | Beat |
|---|---:|---|
| 0:00–0:12 | 12s | Result-first hook: completed morning plan + proposed calendar event |
| 0:12–0:28 | 16s | Personal friction + “no chat” promise |
| 0:28–2:05 | 97s target | **LIVE — UNCUT** scheduled execution; no internal edits |
| 2:05–2:38 | 33s | Permission boundary + planted forbidden-action denial |
| 2:38–3:12 | 34s | Architecture + visible Google Cloud / ADK / Gemini proof |
| 3:12–3:38 | 26s | Clean-clone judge mode + run-scoped cost/privacy evidence |
| 3:38–3:45 | 7s | Close and public URLs |

## The uncut core (one continuous take, target 97s of the final video)

**"LIVE — UNCUT · run 2026-08-31 · scheduled"** on screen throughout.
Continuous screen/camera capture, no cuts:

1. GCP console, Cloud Scheduler page, clock visible → `hearth-morning` fires.
2. Terminal alongside: Cloud Run logs stream; the run doc's
   `triggered_by: sa-home@new-prompt-490003.iam.gserviceaccount.com` shown —
   **authenticated as the configured OIDC invoker principal**.
3. Mission Control refreshes: stages light up gathered → planned → reviewed →
   dispatched; badge reads **scheduled** (green).
4. The autonomous consequences inside the same take: the proposed calendar
   event appears and the morning briefing lands on the phone. Show the TV pause
   only if the fixture/device is actually playing when the run fires.

VO over the core: "This is a real Cloud Scheduler cron firing, on camera, in
one take. The run authenticates as the configured OIDC invoker principal,
Scheduler's run history corroborates the cron origin, and any
manual run — or manual resume — carries its own label. Watch the pipeline
argue with itself, dispatch, and the house quietly act."

## Labeled pickups (each badged "PICKUP · run 2026-08-31" unless noted)

| # | Beat | On screen | VO essence |
|---|------|-----------|------------|
| P1 | Cold open (before the core) | Quiet house b-roll; Mission Control ticking | "No chat window. The house runs its own morning standup." |
| P2 | Architecture | Diagram sweep: gatherers → planner → policy loop → dispatcher; house/cloud wall, pull arrow | ADK primitives named; "the cloud never reaches in — the house pulls." |
| P3 | Permission slip beside autonomous calendar action | Show the HA calendar event already present → phone close-up: Approve/Deny → tap Approve → notification shows the **approved draft released to the household channel** | "The calendar proposal landed autonomously; one tap releases the approved draft to the household notification channel — it never contacts the recipient directly." |
| P4 | Red team | `/trigger?red_team=1` (labeled manual) → denial rows: `unlisted_action_type:front_door_unlock` on Mission Control + BQ `denials_v` | "Planted forbidden action, refused in writing. Denials are data." |
| P5 | Gemma / privacy | `ollama ps`; raw email → tokenized side-by-side; BQ: zero protected-alias matches for the filmed run; historical `egress_block` rows shown separately and explained | "On this filmed path, configured family aliases are tokenized locally; a local Gemma/Qwen tier scans additional PII; and instrumented Gemini requests are checked against the configured protected-alias hashes. This run shows zero matches. Historical blocked rows are shown separately as caught build failures." |
| P6 | Console proof + judge mode (judge-mode run id shown) | Cloud Run service (sa-home), Scheduler SUCCESS history; `git clone` → `SIMULATED_HOME=1 docker compose up` → localhost Mission Control | "Live on Cloud Run, with a run-scoped list-rate cost estimate recorded in BigQuery — and judges get the whole house with one command from a clean clone." |
| P7 | Close | Thumbnail card → URLs | "Hearthbeat: less remembering, less nagging, and fewer rushed surprises." |

## Tight narration spine

Use this as the spoken spine; pause naturally over the live state changes and
do not race the visuals.

**0:00–0:28 — hook and friction**

> I built Hearthbeat after mornings when school email got buried, an
> after-school change surfaced only at drop-off, and the kids were stressed
> before we left. By breakfast, Hearthbeat has already turned school email and
> calendars into a safe plan and a proposed calendar fix. There is no chat
> window and no prompt to remember. The house runs its own morning standup.

**0:28–2:05 — uninterrupted live execution**

> This is one continuous take of the real 6:45 Cloud Scheduler run. The request
> authenticates as the configured OIDC invoker principal, while
> Scheduler history and timing corroborate the cron origin. Four ADK gatherers
> collect tokenized home, calendar, and school-mail context. Gemini plans the
> day; a LoopAgent critic and deterministic default-deny policy review it; then
> the dispatcher creates content-hash action documents and reuses them under
> the tested retry path. Mission Control is scoped to this exact run. The
> calendar proposal and briefing are autonomous. The
> drafted person-to-person message stops at a permission slip because the agent
> is not allowed to make that decision for me.

**2:05–2:38 — boundary and refusal**

> One tap can approve the proposed continuation, but the draft is released only
> to the household channel; it never messages the recipient directly. A planted
> front-door action takes the other path: the whitelist refuses it, and the
> denial becomes evidence instead of disappearing into a log.

**2:38–3:12 — architecture and Google proof**

> Hearthbeat uses ADK Parallel, Sequential, and Loop agents; Gemini 3.5 Flash
> and Flash-Lite on Vertex AI; Cloud Run; Scheduler; Firestore; Pub/Sub; and
> BigQuery. The cloud never reaches into the house—the house polls approved
> action documents. Known aliases are tokenized locally; a local Gemma/Qwen tier
> scans free text on the house path; disclosed judge mode replays recorded
> fixture findings; and instrumented Gemini requests are checked against the
> configured protected-alias hash set.

**3:12–3:45 — reproducibility and close**

> This filmed run shows its own model IDs, actions, list-rate cost estimate, and
> protected-alias match count. Judges can clone the public repository and run
> the disclosed fixture house with one command and no Google credentials.
> Hearthbeat: less remembering, less nagging, and fewer rushed surprises.

## Integrity rules for the edit
- The "LIVE — UNCUT" badge appears ONLY on the continuous take; everything
  else carries a PICKUP badge. Nothing implies the pickups happened inside the
  uncut segment.
- Upload the final demo as **publicly visible** on YouTube or Vimeo. Private
  and unlisted visibility do not satisfy the live Devpost submission gate.
- All run-scoped claims cite the run id on screen.
- No absolute cost figure in VO; Mission Control's per-run figure is visible.
- Final frame-scan for PII before upload (terminal text included).
- If the genuine take exceeds the 97-second target, uniformly speed the whole
  uninterrupted segment and display the multiplier throughout; never trim,
  splice, or rearrange frames inside it.

## Assembly plan (9:15–10:15)
ffmpeg straight cuts, burned-in captions + `.srt`; target 3:45. If the TV was
not playing at 6:45, the media_pause beat moves to a PICKUP with its own
labeled manual run — never blended into the uncut core.
