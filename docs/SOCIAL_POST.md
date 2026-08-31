# Social post draft (X/LinkedIn — bonus artifact)

---

My house now runs its own morning standup. 🫀

No chat UI — a Cloud Scheduler cron fires a Google ADK pipeline (parallel
gatherers → Gemini 3.5 planner → a LoopAgent policy critic that argues with
the plan) on Cloud Run. My phone gets a permission slip before a person-facing
draft can be released to the household notification channel. The house PULLS
its actions — the cloud can't reach in.

The part I'm proudest of: on the filmed path, configured family aliases are
tokenized locally; a local Gemma/Qwen tier scans additional PII; and
instrumented Gemini calls pass a salted-hash protected-alias guard. That guard
once refused a call because I misconfigured a mirror. BigQuery shows zero
protected-alias matches in the filmed run — a query, not a promise.

One command for the whole demo from a clean clone:
SIMULATED_HOME=1 docker compose up

Repo: https://github.com/DZim89/hearthbeat
Live Mission Control: https://hearthbeat-369944070051.us-central1.run.app/missioncontrol

Built solo from a first commit at 4:07:10 PM PDT on August 30 for the All
Things Agentic Hackathon — category: The Taskmaster — using my home-grown AI
Agent Fleet Workspace with Claude Code, Gemini/Antigravity, Codex, and
geminiclaw under my direction and evidence gates.

#AllThingsAgenticHackathon
