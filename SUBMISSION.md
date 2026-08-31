# Devpost submission mirror — every field, paste-ready

> Char limits get verified against tonight's form-recon screenshots and
> annotated here before the 11:15 AM fill. Save draft after every section.

## Project name
hearthbeat

## Elevator pitch (≤200 chars — verified 183)
A no-chat household agent that turns school email and calendars into a safe morning plan—acting autonomously when confidence is high and asking only when a human decision is required.

## Category (exactly one)
**The Taskmaster**

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

**Privacy as architecture, not policy.** Real names exist only inside the
house. A deterministic token map runs before AND after a local **Gemma 3**
pass (ollama, on our own GPU box): the map catches the family, Gemma catches
strangers' PII the map can't know — a teacher's name and phone in a school
email — and a hard `assert_clean` gate fails the pipeline if either missed.
In the cloud, every outbound Vertex request is scanned against **salted
hashes** of the protected names; a match blocks the model call. BigQuery's
verdict for the filmed run: zero protected-alias matches — the only rows the
violations view has ever held are the guard blocking our own build mistakes,
kept and shown separately. (During the build this
guard caught a genuinely misconfigured mirror and refused to talk to Gemini —
we kept the story in the README.)

**Run integrity.** `POST /run` is the only application code path that
assigns `trigger_source=scheduled`, after validating the caller's OIDC
identity against the configured Scheduler service account. Filming and judge runs are labeled `manual`,
structurally. Runs are date-keyed with Firestore `create()` preconditions,
stage-checkpointed, and resumable: under the retry paths we tested (kill
mid-run, re-fire), it finishes without duplicating a single action.

**Built with.** Google ADK (SequentialAgent / ParallelAgent / LoopAgent /
custom BaseAgents / BasePlugin / structured outputs / LiteLlm+AgentTool),
Gemini 3.5 Flash + Flash-Lite on Vertex AI (location=global), Cloud Run,
Cloud Scheduler (OIDC), Pub/Sub + DLQ with a native BigQuery subscription,
Firestore, BigQuery, and local Gemma 3 as a load-bearing privacy tier.
Each run's cost is a run-scoped list-rate estimate from the configured
official per-token rates, recorded in BigQuery (`runs_v.cost_cents`) and on
Mission Control; a configured spend ceiling is enforced mid-run against
observed spend.

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
Solo build (Donny Zimmerman). AI tools, disclosed: Claude Code (Anthropic) as
the sole repository writer / coding agent; Codex Desktop (OpenAI) as
coordinator/acceptance reviewer and thumbnail generator; Gemini-based
reviewers (geminiclaw / Antigravity) as read-only Google-stack reviewers.
None of the reviewers authored repository code. All code authored Aug 30–31,
2026. Pre-existing Home Assistant + local model servers are environment/data
sources only.
