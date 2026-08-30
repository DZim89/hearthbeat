# Devpost submission mirror — every field, paste-ready

> Char limits get verified against tonight's form-recon screenshots and
> annotated here before the 11:15 AM fill. Save draft after every section.

## Project name
hearthbeat

## Elevator pitch (~200 chars)
An autonomous household-operations agent with no chat UI: a Cloud Scheduler
cron fires an ADK pipeline that runs a real family home's morning — plan,
policy critic, human permission slips, pull-only actions.

## Category (exactly one)
**The Taskmaster**

## Text description (long form)

**What it does.** Every morning at 6:45, Cloud Scheduler fires hearthbeat.
Four parallel ADK gatherers read a token-scrubbed Firestore mirror of our real
home — Home Assistant state, the family calendar, the school-email inbox. A
Gemini 3.5 planner drafts the day as structured output: a morning briefing,
and actions like "pause the kids' TV", "write the calendar fix for tonight's
collision", "message Grandma about moving dinner". A LoopAgent policy critic
argues with that plan until a deterministic, default-deny whitelist is
satisfied — a critique is only trusted if it hash-matches the exact plan
revision it graded. A pure-code dispatcher writes content-hashed action docs
to Firestore. Then the house takes over: a poller inside the home PULLS the
actions, rehydrates the privacy tokens locally, re-validates the policy a
third time, and executes in Home Assistant. Anything that touches a person
stops at a permission slip on a real phone — Approve or Deny.

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
standing verdict: `egress_violations_v` = 0 rows. (During the build this
guard caught a genuinely misconfigured mirror and refused to talk to Gemini —
we kept the story in the README.)

**Run integrity.** `trigger_source=scheduled` is writable from exactly one
code path — `/run`, behind in-app OIDC verification of the scheduler's
service-account identity. Filming and judge runs are labeled `manual`,
structurally. Runs are date-keyed with Firestore `create()` preconditions,
stage-checkpointed, and resumable: kill it mid-run, re-fire it, and it
finishes without duplicating a single action.

**Built with.** Google ADK (SequentialAgent / ParallelAgent / LoopAgent /
custom BaseAgents / BasePlugin / structured outputs / LiteLlm+AgentTool),
Gemini 3.5 Flash + Flash-Lite on Vertex AI (location=global), Cloud Run,
Cloud Scheduler (OIDC), Pub/Sub + DLQ with a native BigQuery subscription,
Firestore, BigQuery, and local Gemma 3 as a load-bearing privacy tier.
A full run costs ~1.5¢, audited in BigQuery, with a 50¢/day budget the policy
engine enforces mid-run.

## Built with (tags)
google-adk, gemini, vertex-ai, cloud-run, cloud-scheduler, pub-sub, firestore,
bigquery, gemma, ollama, python, fastapi, home-assistant, docker

## Links
- Repo (public): https://github.com/dzimm3rman/hearthbeat
- Hosted (read-only Mission Control): https://hearthbeat-369944070051.us-central1.run.app/missioncontrol
- Video (public YouTube, ≤4:00, EN captions): «FILL AFTER UPLOAD»
- Architecture diagram: in repo — docs/architecture.png (+ docs/ARCHITECTURE.md)
- dev.to build log (bonus): «FILL»
- Social post w/ #AllThingsAgenticHackathon (bonus): «FILL»

## Try it (judges)
```bash
git clone https://github.com/dzimm3rman/hearthbeat.git && cd hearthbeat
SIMULATED_HOME=1 docker compose up
# open http://localhost:8080/missioncontrol
```
Zero Google credentials; the Firestore emulator + recorded model responses +
a simulated home run the identical pipeline. Disclosures in README →
"Honesty ledger".

## Team / AI disclosure
Solo build (Donny Zimmerman) with Claude Code (Anthropic) as the coding agent
— disclosed in README. All code authored Aug 30–31, 2026. Pre-existing Home
Assistant + local model servers are environment/data sources only.
