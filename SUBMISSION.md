# Devpost submission mirror — every field, paste-ready

> Live form requirements verified against submission `1162918` on August 31,
> 2026. Save the draft after every section; do not click the final submit
> button until the complete preview and every anonymous link are verified.

## Project name
Hearthbeat

## Elevator pitch (≤200 chars — verified 183)
A no-chat household agent that turns school email and calendars into a safe morning plan—acting autonomously when confidence is high and asking only when a human decision is required.

## Category (exactly one)
**Taskmaster**

## Project overview media

- Thumbnail: `docs/hearthbeat-thumbnail.png` (1536×1024, 3:2, under 5 MB)

## Required additional information

- Sponsor / Special Prizes: leave unselected (not entering Startup Excellence)
- Submitter Type: **Individuals**
- Submitter country of residence: **United States**
- Organization name: **Not applicable — individual submission**
- Project start date: **08-30-26** (oldest reachable commit: 2026-08-30)
- Code repository: https://github.com/DZim89/hearthbeat
- Reproducible Testing instructions in README: **Yes**
- Hosted project URL: https://hearthbeat-369944070051.us-central1.run.app/missioncontrol
- Google SDKs: **Agent Development Kit (ADK)**; **Google GenAI SDK (google-genai)**
- Google Cloud services offered by the form: **Cloud Run**; **Firestore**;
  **Pub/Sub**. The story and tags additionally disclose Cloud Scheduler,
  BigQuery, and Vertex AI.
- Architecture diagram upload: `docs/architecture.png`
- Startup-prize organization and corporate-email fields: leave blank
- Google AI models: **Gemini 3.5 Flash; Gemini 3.5 Flash-Lite; Gemma 3
  (local through Ollama)**
- Bonus content URL: fill after the public DEV Community article is published
- Bonus social URL: fill after the public post containing the exact hashtag
  `#AllThingsAgenticHackathon` is published

### Private testing instructions field

Clone the repository and follow README → “Judges: run the whole thing with
one command.” The
credential-free path uses disclosed fixtures, the Firestore emulator, recorded
model responses, and a simulated home. Run `SIMULATED_HOME=1 docker compose
up`, then open `http://localhost:8080/missioncontrol`. The hosted Mission
Control URL is public and read-only; no credentials are required. The live
cloud evidence uses run ID `2026-08-31`.

## Text description (long form)

**What it does.** Every morning at 6:45, Cloud Scheduler fires hearthbeat.
Four parallel ADK gatherers read a token-scrubbed Firestore mirror of our real
home — Home Assistant state, the family calendar, the school-email inbox. A
Gemini 3.5 planner drafts the day as structured output: a morning briefing,
and actions like "pause the kids' TV", "create a proposed calendar event for
tonight's collision", "draft a message about moving dinner". A LoopAgent policy critic
argues with that plan until a deterministic, default-deny whitelist is
satisfied — a critique is only trusted if it hash-matches the exact plan
revision it graded. A pure-code dispatcher writes content-hashed action docs
to Firestore. Then the house takes over: a poller inside the home PULLS the
actions, rehydrates the privacy tokens locally, re-validates the policy a
third time, and executes in Home Assistant. Anything that touches a person
stops at a permission slip on a real phone — Approve or Deny; approval
releases the drafted message to the household notification channel (it never
messages the recipient directly).

**The twist.** There is no chat window. No prompt box. The interfaces are a
cron, a read-only Mission Control page, a briefing that lands on a phone, and
things quietly happening in a real house with three kids in it.

**Privacy as architecture, not policy.** Known family aliases are
deterministically tokenized on the intended runtime path before AND after a local **Gemma 3**
pass (ollama, on our own GPU box): the map tokenizes the family, a local Gemma/Qwen tier scans
for additional PII the map can't know — a teacher's name and phone in a school
email. In the cloud, every instrumented outbound Gemini request is checked against the
**configured protected-alias hash set**; a match blocks the model call. BigQuery's
verdict for the filmed run: zero protected-alias matches — the only rows the
violations view has ever held are the guard blocking our own build mistakes,
kept and shown separately. (During the build this
guard caught a genuinely misconfigured mirror and refused to talk to Gemini —
we kept the story in the README.)

**Run integrity.** `POST /run` authenticates the configured invoker principal
via OIDC; Scheduler history/timing corroborate cron origin. Filming and judge runs are labeled `manual`,
structurally. Runs are date-keyed with Firestore `create()` preconditions,
stage-checkpointed, and resumable: under the retry paths we tested (kill
mid-run, re-fire), it finishes without duplicating a single action.

**Built with.** Google ADK (SequentialAgent / ParallelAgent / LoopAgent /
custom BaseAgents / BasePlugin / structured outputs),
Gemini 3.5 Flash + Flash-Lite on Vertex AI (location=global), Cloud Run,
Cloud Scheduler (OIDC), Pub/Sub + DLQ with a native BigQuery subscription,
Firestore, BigQuery, and local Gemma 3 as a load-bearing privacy tier.
Each run's cost is an estimated list-rate model cost for this run from the configured
official per-token rates, recorded in BigQuery (`runs_v.cost_cents`) and on
Mission Control; a configured observed-spend threshold causes the policy
layer and dispatcher to deny the action plan (not a hard billing cap).

## Built with (tags)
google-adk, gemini, vertex-ai, cloud-run, cloud-scheduler, pub-sub, firestore,
bigquery, gemma, ollama, python, fastapi, home-assistant, docker

## Links
- Repo (public): https://github.com/DZim89/hearthbeat
- Hosted (read-only Mission Control): https://hearthbeat-369944070051.us-central1.run.app/missioncontrol
- Video (public YouTube, ≤4:00, EN captions): «FILL AFTER UPLOAD»
- Architecture diagram: in repo — docs/architecture.png (+ docs/ARCHITECTURE.md)
- Gallery thumbnail (3:2): docs/hearthbeat-thumbnail.png
- dev.to build log (bonus): «FILL»
- Social post w/ #AllThingsAgenticHackathon (bonus): «FILL»

## Try it (judges)
```bash
git clone https://github.com/DZim89/hearthbeat.git && cd hearthbeat
SIMULATED_HOME=1 docker compose up
# open http://localhost:8080/missioncontrol
```
Zero Google credentials; the Firestore emulator + recorded model responses +
a simulated home run the identical pipeline. Disclosures in README →
"Honesty ledger".

## Team / AI disclosure
Solo build (Donny Zimmerman). AI tools, disclosed: Claude Code (Anthropic) and
Antigravity with Gemini 3.7 Flash High authored implementation and public-copy
changes under Donny's direction; Codex Desktop (OpenAI) coordinated,
independently reviewed, generated the thumbnail, and applied final
claim-discipline corrections; geminiclaw provided read-only Google-stack
reviews. All code was authored Aug 30–31, 2026. Pre-existing Home Assistant +
local model servers are environment/data sources only.
