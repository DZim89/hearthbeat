# Hearthbeat — final 3:20 video script (hard ceiling 4:00)

This is an edited montage with one clearly labeled, uninterrupted live
segment. The fixed live segment is 85 seconds at 1× speed from one continuous
source interval; it has no temporal edits, transitions, freezes, or internal
cuts. Every other beat is labeled as a pickup.

The visual spine is **ACT · ASK · REFUSE**:

- **Act:** the calendar event and morning briefing complete in the authentic
  scheduled run.
- **Ask:** the personal notification remains permission-gated.
- **Refuse:** disclosed local judge mode rejects a planted forbidden action.

## Exact edit clock

| Final time | Length | Source and visible content | Required label |
|---|---:|---|---|
| 0:00–0:15 | 15s | New result-first pickup: clean completed action rows, calendar result, and Hearthbeat title. Do not show the briefing body. | `PICKUP · RESULT · RUN 2026-08-31` |
| 0:15–0:30 | 15s | New personal-friction/no-chat pickup: quiet-house, calendar, or clean title imagery. | `PICKUP · CONTEXT` |
| 0:30–1:55 | 85s | `live-core-uncut.mp4` exactly as prepared: one constant crop, 1× speed, no temporal edits. | `LIVE · UNCUT · 1× · RUN 2026-08-31 · SCHEDULED` throughout |
| 1:55–2:07 | 12s | `run-evidence-pickup.mp4`: 11 calls, zero configured protected-alias matches, 4.9906¢, run ID. | `PICKUP · RUN EVIDENCE · 2026-08-31` |
| 2:07–2:27 | 20s | New permission pickup: awaiting-approval state and, only if public-safe and available, the controlled approval plus household-channel result. | `PICKUP · SAME RUN · HUMAN APPROVAL · RECORDED AFTER LIVE RUN` |
| 2:27–3:01 | 34s | `architecture-pickup-final.mp4`. | `PICKUP · ARCHITECTURE` |
| 3:01–3:13 | 12s | New judge-mode pickup: one-command invocation and local denial result. | `PICKUP · JUDGE MODE · LOCAL EMULATOR · MANUAL` |
| 3:13–3:20 | 7s | `closing-card-final.mp4`. | Existing final card |

## Exact voiceover

### 0:00–0:15 — result first

> With four kids and two working parents, one buried school email can turn
> breakfast into a scramble. Hearthbeat wakes before us, builds the morning
> plan, and acts only within permission.

### 0:15–0:30 — no-chat promise

> There is no chat window and no prompt to remember. At 6:45, the agent starts
> itself, turns scattered school and calendar facts into action, asks when
> needed, and refuses what is not allowed.

### 0:30–1:55 — uninterrupted live core

> This is the real 6:45 run at normal speed, shown in one continuous take.
> Cloud Scheduler fires the service. The request authenticates as Hearthbeat’s
> configured OIDC invoker principal, and Scheduler history plus timing
> corroborate the cron origin. Four ADK gatherers collect tokenized home,
> calendar, and school-mail context. Gemini produces a structured plan. A
> LoopAgent critic and deterministic default-deny policy review the exact
> revision before dispatch. The dispatcher writes content-hash action
> documents and reuses them under the tested retry path. Mission Control is
> scoped to run 2026-08-31. Gathered, planned, reviewed, dispatched—every stage
> completes. The permitted calendar event and morning briefing finish
> autonomously. The proposed family notification does not. It stops at
> awaiting approval, because a model can suggest a personal action, but it
> cannot grant itself authority. That is Hearthbeat’s trust boundary: routine
> coordination happens quietly, while I keep the consequential decision.

Read this naturally and leave quiet space for stage transitions. Do not speed
up the live core or the narration to fill silence.

### 1:55–2:07 — run evidence

> For this filmed run, the egress guard scanned 11 instrumented outbound model
> calls and found zero configured protected-alias matches. Its run-scoped
> estimated list-rate model cost was 4.9906 cents.

Keep the words “estimated list-rate model cost.” Do not call this billed spend
or exact cloud cost.

### 2:07–2:27 — permission boundary

Use this only if the pickup visibly proves the real approval and resulting
household-channel release:

> This is a labeled pickup from the same run. I approve the held draft, and
> Hearthbeat releases it only to the configured household notification
> channel. It does not contact the named recipient directly; denying would
> leave the action stopped.

If the approval path is unavailable, show the unchanged awaiting-approval
state and use:

> This labeled pickup shows the personal action still held for my decision.
> Hearthbeat can release the draft only to the configured household
> notification channel after approval.

Before recording, clear unrelated notifications and exclude real contact
names, phone numbers, account identifiers, and notification previews.

### 2:27–3:01 — architecture

> Google ADK composes Parallel, Sequential, and Loop agents. Gemini 3.5
> Flash-Lite gathers context; Gemini 3.5 Flash plans and critiques on Vertex
> AI. Cloud Run hosts the pipeline. Firestore stores checkpoints, actions, and
> permission slips; Pub/Sub carries run-scoped audit events to BigQuery. The
> house pulls approved actions and revalidates policy locally. Known aliases
> are tokenized locally, a local Gemma/Qwen tier scans additional free-text
> PII, and instrumented Gemini requests pass the protected-alias egress guard.

### 3:01–3:13 — judge mode and refusal

> Judges can run the disclosed fixture house with one Docker command and no
> Google credentials. It exercises the same orchestration and default-deny
> policy, including a planted forbidden action.

Show `SIMULATED_HOME=1 docker compose up`, followed by the local Mission
Control denial row. The pickup may jump from command to result; do not imply
that the complete Docker startup occurred in 12 seconds. Keep the badge
`LOCAL EMULATOR · MANUAL`, because judge mode uses a separate datastore even
when its date-derived run ID matches production.

### 3:13–3:20 — close

> Hearthbeat: less remembering, less nagging, and fewer rushed
> surprises—without another chat window.

## Edit integrity and release gates

- The 85-second live-core sequence remains temporally intact inside the
  montage. It is never trimmed internally, sped up, frozen, or rearranged; the
  separately preserved source asset is hashed in the evidence record.
- The constant prepared crop and persistent integrity badge remain unchanged.
  No moment-specific masks are added.
- Pickups never imply they occurred inside the uninterrupted execution.
- The malformed nested display token in the longer briefing is not shown.
- Production evidence and the local fixture run are never visually blended.
- The final video is under four minutes, publicly visible, captioned in
  English, and verified while logged out.
- Complete a frame-by-frame public-data scan before upload, including browser
  chrome, notifications, terminal text, account avatars, and URLs.
