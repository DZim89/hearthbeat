# Social post draft (X/LinkedIn — bonus artifact)

---

My house now runs its own morning standup. 🫀

No chat UI — a Cloud Scheduler cron fires a Google ADK pipeline (parallel
gatherers → Gemini 3.5 planner → a LoopAgent policy critic that argues with
the plan) on Cloud Run. My phone gets a permission slip before it messages a
human. The house PULLS its actions — the cloud can't reach in.

The part I'm proudest of: real names never leave the house. Deterministic
token map + local Gemma 3, and a salted-hash egress guard in the cloud that
once refused to call Gemini because I misconfigured a mirror. BigQuery says
zero private egress — with a query, not a promise.

One command for the whole demo from a clean clone:
SIMULATED_HOME=1 docker compose up

Repo: https://github.com/dzimm3rman/hearthbeat
Live Mission Control: https://hearthbeat-369944070051.us-central1.run.app/missioncontrol

Built solo overnight (with Claude Code as pair) for the All Things Agentic
Hackathon — category: The Taskmaster.

#AllThingsAgenticHackathon
