# Devpost submission mirror — every field, paste-ready

> Live form requirements verified against submission `1162918` on August 31,
> 2026. Save the draft after every section; do not click the final submit
> button until the complete preview and every anonymous link are verified.

## Project name
Hearthbeat

## Elevator pitch (≤200 chars)
A no-chat household agent that turns school email and calendars into a safe morning plan—acting when policy permits and asking only when a human decision is required.

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

## Inspiration

My wife and I both work full-time, and we are raising four kids. Getting
everyone ready for school, fed, and to the right activity—while also remembering
the dog, the cat litter, appointments, permission slips, and everything else—can
feel overwhelming. It starts in the morning, but if I am honest, the mental
checklist runs until we fall asleep.

I tend to build AI the same way I approach any useful automation: I look for
work that creates repeated stress, drains attention, or is simply a poor use of
a person's time, and then I try to remove that friction. If it is frustrating
for me, another family is probably living through some version of it too.

Hearthbeat came from a few very ordinary failures: an important school email
got buried, the kids did not know what to prepare on their own, and an
after-school schedule change surfaced only when we reached drop-off. One rough
morning also revealed that we had run out of easy breakfast food. I did not
pretend a deadline-night build could solve the entire household. I chose the
repeatable failure at the center—school-email and calendar facts reaching us too
late—and built the smallest dependable agent that could act before the morning
became stressful.

## What it does

Every morning at 6:45, Cloud Scheduler starts Hearthbeat. Four parallel Google
ADK gatherers read a tokenized Firestore mirror of Home Assistant state, the
family calendar, and the school-email inbox. Gemini turns those scattered facts
into a structured morning briefing and a bounded action plan.

There is no chat window and no prompt to remember. Hearthbeat can create a
permitted calendar proposal and deliver the household briefing autonomously.
If a proposed action requires a human decision—such as releasing a drafted
person-to-person message—it stops at an Approve/Deny permission slip on a real
phone. A planted front-door action takes the third path: deterministic policy
refuses it and records the denial as evidence.

Mission Control is a read-only, run-scoped view of what happened: each stage,
action, approval state, model ID, trigger provenance, estimated list-rate model
cost, and protected-alias scan result. Most agents only answer. Hearthbeat has
three outcomes—act, ask, or refuse—and Mission Control shows which path it
took. The result is less remembering, less nagging, and fewer rushed surprises.

## How we built it

The first reachable Git commit is timestamped **August 30, 2026 at 4:07:10 PM
PDT**. From that point, I built Hearthbeat as a focused overnight sprint with a
single rule: finish a narrow, dependable system before adding more ideas.

The cloud pipeline uses Google ADK `ParallelAgent`, `SequentialAgent`, and
`LoopAgent` primitives with structured outputs. Gemini 3.5 Flash-Lite gathers
context; Gemini 3.5 Flash plans and critiques; a deterministic policy gate
reviews the exact hash-bound plan; and a pure-code dispatcher writes
content-addressed action documents to Firestore. The house then pulls approved
actions from the cloud, revalidates policy locally, rehydrates privacy tokens,
and executes through Home Assistant. The cloud never reaches directly into the
home.

The decision contract is intentionally simpler than the model:

$$
\operatorname{Execute}(a)
=
\operatorname{Allowlisted}(a)
\land
\left(\neg \operatorname{HumanGated}(a)
\lor \operatorname{Approved}(a)\right)
$$

In plain language: an action must be explicitly allowed, and any human-gated
action must also be approved. Unknown, malformed, or incomplete output fails
closed.

Privacy is an architectural boundary. On the intended filmed path, configured
family aliases are tokenized locally; a local Gemma/Qwen tier scans free text
for additional PII; and every instrumented outbound Gemini request is checked
against the configured protected-alias hash set. A match blocks the model call.
The filmed run reports its own protected-alias count; historical blocked rows
are labeled separately as caught build failures.

For failure tolerance, runs are date-keyed, stage-checkpointed, and resumable.
Action documents use content hashes and are reused under the tested retry path.
Cloud Scheduler uses OIDC, while attempt-scoped provenance keeps a scheduled
run, manual run, or manual resume visibly distinct. Pub/Sub and a dead-letter
topic carry audit events into BigQuery.

Judges can also clone the public repository and run the disclosed fixture house
with one command and no Google credentials. The Firestore emulator, recorded
model responses, and simulated Home Assistant exercise the same orchestration,
policy, and dispatch paths.

## Challenges we ran into

- **Making autonomy useful without making it reckless.** A model can propose
  an action, but it cannot grant itself authority. The deterministic whitelist,
  permission-slip boundary, and fail-closed parsing became the real product.
- **Keeping household data local while still using cloud reasoning.** Token
  replacement alone was not enough, so the runtime combines a known-alias map,
  local free-text scanning, and a protected-alias egress guard. That guard
  caught a real build misconfiguration and refused the Gemini call.
- **Proving what actually happened.** Scheduler identity, retries, resumes,
  model usage, privacy checks, and cost can easily become vague claims. We made
  them run-scoped evidence instead.
- **Retries without duplicate action documents.** A resumed run continues from
  a checkpoint and reuses the same content-hash action document under the
  tested retry path. This is not a universal exactly-once guarantee for
  external Home Assistant side effects.
- **Shipping honestly under a hard deadline.** We cut attractive features such
  as pantry awareness, learned trust, and role-specific child briefings rather
  than describe roadmap ideas as finished capabilities.

## Accomplishments that we're proud of

- A genuine no-chat agent that wakes on schedule and produces visible household
  consequences instead of another conversational demo.
- A clean three-way action boundary: autonomous when explicitly allowed,
  approval-gated when a person must decide, and denied when the action is
  unknown or forbidden.
- A privacy path designed around tokenized identities and fail-closed egress,
  with the filmed result stated only for the exact run being shown.
- Mission Control evidence that connects the agent's reasoning to actions,
  approvals, provenance, privacy checks, model use, and cost.
- A credential-free judge mode plus a current full-suite result of **95 passing
  tests**, with six Firestore-emulator tests skipped when the emulator was not
  running.
- A complete working system built from the repository's first commit at 4:07:10
  PM PDT on August 30 through the overnight submission sprint.

## What we learned

The most important lesson was that safe autonomy is not primarily a prompting
problem. The model is useful for interpreting context and proposing a plan, but
trust comes from deterministic authority boundaries, content-hash
action-document reuse under the tested retry path, observable evidence, and a
clear human decision point.

We also learned that an agent feels more natural when the user does less. A
scheduled briefing, a calendar proposal, and one meaningful permission slip can
be more useful than a sophisticated chat interface. Finally, narrowing claims
to the exact run made the engineering better: if a privacy, provenance, cost, or
reliability statement could not be shown on screen or reproduced from the
repository, it did not belong in the submission.

## What's next for Hearthbeat

The next priorities are an injection-resistant school-mail boundary,
role-aware briefings that give adults and children only the information they
need, and consent-bounded memory whose trust is earned per action, expires, and
can always be revoked. After those foundations, Hearthbeat can look ahead to
district schedules, weather, presence, and pantry readiness so tomorrow's
problems are handled tonight—without turning the home into another app the
family has to manage.

## AI-assisted build provenance

This is a solo entry by Donny Zimmerman, built with a home-grown **AI Agent
Fleet Workspace**: a private multi-agent engineering environment that lets me
give several AI systems a shared plan, bounded work, a single source of truth,
and evidence gates before changes are accepted. I directed the problem,
product decisions, household data boundaries, safety policy, acceptance
criteria, and final submission; the fleet accelerated research,
implementation, testing, and adversarial review.

The workspace used Claude Code, Antigravity/Gemini, Codex, and geminiclaw. Its
private fleet infrastructure is intentionally outside this public entry, but
its design philosophy is visible in Hearthbeat: specialize the agents, bound
their authority, and require evidence before action. All Hearthbeat application
code was authored August 30–31, 2026. The pre-existing Home Assistant
installation and local model servers are environment and data sources, not
submission code.

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
a simulated home run the same orchestration, policy, and dispatch code paths.
Disclosures in README →
"Honesty ledger".

## Team / AI disclosure
Solo build by Donny Zimmerman using a home-grown AI Agent Fleet Workspace.
Claude Code, Antigravity/Gemini, Codex, and geminiclaw assisted across research,
implementation, testing, and adversarial review under Donny's direction and
evidence gates. The first reachable commit is August 30, 2026 at 4:07:10 PM PDT;
all Hearthbeat application code was authored August 30–31. Pre-existing Home
Assistant and local model servers are environment/data sources only.
