# Building hearthbeat in one night: an ADK agent that runs my house's morning (and audits every outbound call for protected aliases)

*Build log for the All Things Agentic Hackathon. Category: The Taskmaster.*

I built an autonomous household-operations agent in one night with Google's
Agent Development Kit, Gemini 3.5 on Vertex, and a stack of Google Cloud
plumbing — and the most interesting bugs were the ones my own privacy guard
caught. Build log below, roughly in commit order.

The motivation was painfully ordinary: a school email gets buried, the kids do
not know what to prepare on their own, and an after-school change surfaces only
when we reach drop-off. One rough morning also revealed that we had run out of
easy breakfast food. I did not claim a one-night MVP could solve all of that. I
started with the repeatable failure at the center — school-email and calendar
facts reaching us too late — and built a dependable scheduled agent around it.

## The product in one sentence

No chat UI: a Cloud Scheduler cron fires an ADK pipeline on Cloud Run that
reads a token-scrubbed mirror of my actual home (Home Assistant, family
calendar, school email), plans the day, refuses its own bad ideas against a
default-deny whitelist, asks my phone for a permission slip before messaging a
human, and then my house *pulls* the approved actions — the cloud has no way in.

## Hour 0: kill the scary unknowns first

Two probes before any code: (1) which Gemini 3.5 IDs actually answer in my
project — answer: `gemini-3.5-flash` and `-flash-lite`, **only at
`location=global`** (us-central1 404s all of them); (2) the empty-text trap —
with a small `maxOutputTokens`, thinking consumes the whole budget and
`.text` comes back empty. Both went straight into a canary script
(`infra/canary.py`) and hard rules in the model factory: floor
`max_output_tokens` at 2048, always set an explicit `ThinkingConfig`.

## The ADK composition that survived contact with the API

Original sketch: "the planner drafts the plan and calls tools." Real API:
**`output_schema` disables tools.** So the shape became four tool-bearing
gatherers (`ParallelAgent`, distinct `output_key`s — the docs warn you about
state races) feeding a tool-less structured planner, then a `LoopAgent`:

```
PolicyGate (custom BaseAgent, pure code) → critic (LLM) → reviser (LLM), ≤3 turns
```

PolicyGate is the fun part. It runs a deterministic whitelist/quiet-hours/
budget check, hashes the plan, and only escalates (ends the loop) when the
findings are empty AND the critic's structured `Critique` both passes and
**echoes the hash of the exact plan revision it graded**. A stale "pass" can
never green-light a newer plan. The dispatcher then re-checks every action
anyway — and the house-side poller checks a third time before touching Home
Assistant. Default-deny, enforced three times, all from one YAML file.

## Privacy that doesn't depend on a model behaving

House-side, every piece of free text goes through `deep_scrub`: deterministic
token map → **local Gemma 3 via ollama** (a local Gemma/Qwen tier scans for
additional PII the family map can't know — the teacher's name and phone in a school email)
→ token map again → scrub validation. My 4080 is so VRAM-contended by other local
models that gemma runs mostly on CPU at ~12 tok/s — fine for short scans, and
the ledger records which tier did each pass (`PRIVACY_TIER=qwen` is the
fallback).

Cloud-side, an ADK `BasePlugin`'s `before_model_callback` scans every instrumented outbound
Vertex request against **salted hashes** of the protected names. The guard
stores and compares salted alias hashes.

Three real bugs this architecture caught *during the build*:

1. My token for Dad was `[[P_DAD]]` — and the alias regex happily matched
   "DAD" inside the token, producing `[[P_[[P_DAD]]]]`. Scrub only outside
   token spans.
2. My "hash every word of multi-word aliases" idea hashed the word **"the"**
   (from a room alias) — instant false positives on all English text.
   Per-word hashes now apply only to person names, ≥4 chars, minus a
   family-word stoplist.
3. The big one: I ran the first mirror with the fixture map instead of the
   real one, so real first names landed in Firestore. On the very next cloud
   run, **the egress guard refused to call Gemini** — 2 hash matches,
   blocked, run failed. The privacy system's first real catch was my own
   mistake. It's in the README's honesty ledger.

## Run integrity as a feature

`POST /run` authenticates the configured invoker principal via OIDC; for the
filmed run, Scheduler history and fire-time logs corroborate cron origin.
The filming/judge endpoint hard-codes `manual`. When you see "scheduled" in the
filmed demo, it is corroborated by Scheduler history.

Also: GFE quietly intercepts the literal path `/healthz` on `*.run.app` and
serves a Google 404 that never reaches your container. Renamed to `/health`.
You're welcome, future me.

## Judge mode

`SIMULATED_HOME=1 docker compose up` from a clean clone: the same container
image, the real **Firestore emulator** (real transactions and `create()`
preconditions), a fake Home Assistant seeded from fixtures, recorded Gemini
responses, and a kickoff that fires `/trigger`. Substitutions only where no
free emulator exists (BigQuery → JSONL), each disclosed.

## Numbers

- Per-run cost: a run-scoped list-rate estimate at official configured
  rates (`runs_v.cost_cents` in BigQuery); a configured observed-spend
  threshold makes the policy layer deny the plan (not a hard billing cap).
- `egress_violations_v`: zero protected-alias matches in the filmed run.
  Historical blocked rows are shown separately as caught build failures.
- Unit tests: the scrub round-trip and policy table tests are the graded core.

Repo: https://github.com/DZim89/hearthbeat · Mission Control (live,
read-only, token-space): https://hearthbeat-369944070051.us-central1.run.app/missioncontrol

*I built Hearthbeat solo with my home-grown AI Agent Fleet Workspace: a
private multi-agent engineering environment that gives Claude Code,
Antigravity/Gemini, Codex, and geminiclaw a shared plan, bounded work, and
evidence gates under my direction. The first repository commit is timestamped
August 30, 2026 at 4:07:10 PM PDT. My house now holds a better morning standup
than most teams I've worked on.*

#AllThingsAgenticHackathon
