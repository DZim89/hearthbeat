# hearthbeat — 3:50 shot-by-shot script (hard ceiling 4:00)

Captions: burned-in AND uploaded .srt. On-screen proof beats: GCP console with
project visible, `trigger_source=scheduled`, BQ zero-egress query, clean-clone
judge mode. VO is Donny; two takes per line is plenty. Total 230 s.

| # | Time | Shot (what's on screen) | VO (verbatim) |
|---|------|--------------------------|----------------|
| 1 | 0:00–0:20 | Quiet living room, morning light. Cut to Mission Control ticking: stages lighting up. The TV visibly PAUSES by itself. Overlay: "Nobody touched anything." | "This is hearthbeat. Every morning, before anyone's awake, our house runs its own standup. Nobody typed a prompt — there's no chat window to type one into." |
| 2 | 0:20–0:40 | Split: school .eml landing in a folder → scrubbed tokens on Mission Control; calendar with two overlapping events highlighted. | "It reads what a family actually runs on — the school email nobody finished reading, the calendar collision nobody noticed — and it acts. Within limits. That's The Taskmaster: an autonomous background agent doing real household operations." |
| 3 | 0:40–1:05 | Architecture diagram, highlight sweeping left to right: gatherers → planner → policy loop → dispatcher. Then the house/cloud wall with the pull arrow. | "It's built on Google's Agent Development Kit: four parallel gatherers, a Gemini 3.5 planner with structured output, and a looping policy critic that argues with the plan until a deterministic whitelist is satisfied. And one architectural vow: the cloud never reaches into the house. The house pulls." |
| 4 | 1:05–1:40 | THE MONEY SHOT. GCP console Cloud Scheduler page, clock in frame. Job flips to Running. Terminal: Cloud Run logs streaming. Mission Control badge: **scheduled** (green). TV pauses. Phone lights up with the briefing. | "Eleven-fifteen at night for us — six forty-five every morning for real — this is a real Cloud Scheduler cron firing, on camera. And here's the honest part: the trigger source is cryptographically earned. Only the scheduler's OIDC identity can label a run 'scheduled'. A manual demo run can't impersonate this. Ever." |
| 5 | 1:40–2:10 | Phone close-up: "hearthbeat · permission slip — Send to Grandma: …" with Approve/Deny buttons. Thumb taps Approve. Cut: HA calendar shows the [hearthbeat] fix event appearing. | "Anything that touches a person stops at a permission slip. The agent drafted a message to Grandma about tonight's calendar conflict — and it waits, on my actual phone, for a human signature. One tap. The fix lands on the family calendar. The message goes out. Quiet hours? A human tap is consent." |
| 6 | 2:10–2:40 | Terminal: `/trigger?red_team=1`. Mission Control denials table fills: `unlisted_action_type:front_door_unlock` in red. BigQuery `denials_v` shows the same row. | "We red-team it on camera. A planted action: unlock the front door. The policy critic refuses — it's not on the whitelist, and nothing that isn't on the whitelist survives three separate enforcement layers. The refusal is written to the ledger. Denials are data here." |
| 7 | 2:40–3:10 | DadsPC terminal: `ollama ps` showing gemma3. Side-by-side: raw school email → tokenized version ([[P_KID4]], [[REDACTED_0]]). BQ: `egress_violations_v` → **0 rows for legitimate runs**, then the two `egress_block` rows from the build mistake; `privacy_tier_v` showing gemma spans. | "Family data never leaves this house raw. A deterministic token map runs before and after a local Gemma 3 — Gemma catches what the map can't know, like the teacher's phone number. And in the cloud, every outbound model call is scanned against salted hashes. Zero egress rows for every legitimate run — and the only rows in that table at all are the guard catching OUR OWN misconfigured mirror during the build, blocking Gemini until we fixed it. We left the evidence in." |
| 8 | 3:10–3:35 | Console: Cloud Run service (sa-home), Scheduler history with SUCCESS runs, project id visible. Then fast cut: `git clone` → `SIMULATED_HOME=1 docker compose up` → Mission Control on localhost. | "It's live on Cloud Run, fired by a real cron, with Pub/Sub and a dead-letter queue feeding a BigQuery ledger that prices every run — about a cent and a half a morning. And judges: one command, clean clone, zero credentials, the entire house included." |
| 9 | 3:35–3:50 | Mission Control URL + repo URL on screen over morning-house b-roll. | "hearthbeat. The house that runs its own morning. Links below." |

## Pickup list (shortest path, tonight + 8:15 AM)
- Money shot (4): tonight 23:15 — console + logs + TV + phone in ONE take if possible.
- Permission slip (5): tonight ~23:20, phone close-up + HA calendar.
- Red team (6): deterministic — any time, tomorrow 8:15 AM fine.
- Gemma/privacy (7): terminal capture, tomorrow.
- Console proof + judge mode (8): tomorrow after 6:45 (two SUCCESS entries in history).
- Cold open (1) + close (9): b-roll tomorrow morning; Mission Control screen-rec any time.
