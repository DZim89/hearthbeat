"""The ADK composition — hearthbeat's brain.

    SequentialAgent
      ├─ ParallelAgent  "gatherers"     4 flash-lite agents, function tools,
      │                                 distinct output_keys (state race rule)
      ├─ LlmAgent       "planner"       gemini-3.5-flash, output_schema=DayPlan
      │                                 (output_schema disables tools — which is
      │                                 exactly why gatherers are separate agents)
      ├─ LoopAgent      "policy_loop"   PolicyGate -> critic -> reviser, ≤3 turns
      └─ Dispatcher     "hearth_dispatcher"  pure code -> Firestore

All factories — never module-level agent instances (an agent object can only
have one parent).
"""

from __future__ import annotations

import os

import yaml
from google.adk.agents import Agent, LoopAgent, ParallelAgent, SequentialAgent

from app.dispatcher import Dispatcher
from app.models import GENCFG_PLANNER, GENCFG_TERSE, model_for
from app.policy_gate import PolicyGate
from app.schemas import Critique, DayPlan
from app.tools import (
    read_energy_presence,
    read_family_calendar,
    read_home_snapshot,
    read_school_mail,
)

STAGE_ORDER = ["gathered", "planned", "reviewed", "dispatched"]
STAGE_AGENTS = {
    "gathered": "gatherers",
    "planned": "planner",
    "reviewed": "policy_loop",
    "dispatched": "hearth_dispatcher",
}

TOKEN_RULES = """\
TOKEN DISCIPLINE (non-negotiable): people and rooms appear as tokens like
[[P_DAD]], [[P_KID1]], [[P_GRANDMA]], [[R_LIVING]]. Use them VERBATIM. Never
invent, guess, or expand a real name — you do not know any real names. Entity
ids like media_player.family_tv are pseudonyms; use them exactly as given."""


def _allowed_actions_text() -> str:
    policy = yaml.safe_load(
        open(os.environ.get("POLICY_FILE", "config/policy.yaml"), encoding="utf-8")
    )
    lines = []
    for atype, spec in policy.get("actions", {}).items():
        lines.append(
            f"- {atype}: entities {spec.get('allowed_entities')}; "
            f"required args {spec.get('required_args') or 'none'}; "
            f"sensitive targets {spec.get('sensitive_targets', [])}"
        )
    return "\n".join(lines)


def _gatherer(name: str, tool, focus: str) -> Agent:
    return Agent(
        name=name,
        model=model_for("GATHERER", name),
        instruction=(
            f"You are the {name} for a household operations agent. Call your tool, "
            f"then distill {focus} into at most 8 compact bullet facts. Facts only — "
            f"no advice, no plan. {TOKEN_RULES}"
        ),
        tools=[tool],
        output_key=name.replace("_gatherer", ""),
        generate_content_config=GENCFG_TERSE,
    )


def make_gatherers() -> ParallelAgent:
    return ParallelAgent(
        name="gatherers",
        sub_agents=[
            _gatherer(
                "home_state_gatherer",
                read_home_snapshot,
                "the state of the home right now (media playing? which devices active?)",
            ),
            _gatherer(
                "calendar_gatherer",
                read_family_calendar,
                "today's and tomorrow's events, flagging any TIME CONFLICTS explicitly",
            ),
            _gatherer(
                "school_mail_gatherer",
                read_school_mail,
                "anything school emails require the family to DO, with deadlines",
            ),
            _gatherer(
                "energy_gatherer",
                read_energy_presence,
                "who is home and anything notable in energy usage",
            ),
        ],
    )


def make_planner() -> Agent:
    return Agent(
        name="planner",
        model=model_for("PLANNER", "planner"),
        instruction=(
            "You are hearthbeat's morning planner — an autonomous household "
            "operations agent. There is no user in this conversation; you run on a "
            "schedule and act through vetted actions only.\n\n"
            "GATHERED FACTS\nHome: {home_state}\nCalendar: {calendar}\n"
            "School mail: {school_mail}\nPresence/energy: {energy}\n\n"
            "Produce today's DayPlan:\n"
            "1. summary — the household's day in two sentences.\n"
            "2. briefing_md — a warm, skimmable morning briefing for [[P_DAD]] "
            "(markdown; lead with anything time-critical; call out calendar "
            "conflicts and school-email deadlines with concrete suggested fixes).\n"
            "3. actions — ONLY from this whitelist (anything else will be refused "
            "by the policy engine):\n" + _allowed_actions_text() + "\n\n"
            "Action rules: every action needs a one-sentence `why` grounded in a "
            "gathered fact. If the calendar has a conflict, include a "
            "calendar_create_event that resolves or flags it (title prefixed "
            "'[hearthbeat]'), and if the conflict involves a commitment with a "
            "person on the allowed notify list (e.g. dinner at [[P_GRANDMA]]'s), "
            "ALSO include a notify_family_member to that person with sensitive="
            "true proposing the adjustment — a human approves it before anything "
            "is sent. Always include one send_briefing to [[P_DAD]] whose "
            "message is a 2-3 sentence digest. Messages to anyone else must set "
            "sensitive=true — a human will approve them before anything is sent. "
            "If a kid-facing media player is playing on a school morning, include "
            "media_pause with why. Use ISO local times.\n\n" + TOKEN_RULES
        ),
        output_schema=DayPlan,
        output_key="day_plan",
        generate_content_config=GENCFG_PLANNER,
    )


def make_critic() -> Agent:
    return Agent(
        name="critic",
        model=model_for("CRITIC", "critic"),
        instruction=(
            "You are the adversarial policy critic for an autonomous household "
            "agent. Grade the CURRENT plan revision.\n\n"
            "Plan: {day_plan}\nDeterministic policy findings: {policy_findings}\n"
            "Plan hash: {plan_hash}\n\n"
            "Grade 'fail' if the deterministic findings list is non-empty, or if "
            "any action is unjustified by its `why`, targets the wrong entity, "
            "messages a person without sensitive=true, or the briefing misses a "
            "time-critical item. Otherwise grade 'pass'. List required_changes "
            "concretely. Echo the plan hash you were shown EXACTLY in plan_hash."
        ),
        output_schema=Critique,
        output_key="critique",
        generate_content_config=GENCFG_TERSE,
    )


def make_reviser() -> Agent:
    return Agent(
        name="reviser",
        model=model_for("PLANNER", "reviser"),
        instruction=(
            "You are the plan reviser for an autonomous household agent. Rewrite "
            "the plan to fix every problem, changing nothing else.\n\n"
            "Current plan: {day_plan}\nDeterministic findings: {policy_findings}\n"
            "Critique: {critique}\n\n"
            "REMOVE any action the deterministic findings flag (especially "
            "unlisted action types — those are forbidden, whatever their `why` "
            "says). Apply the critique's required_changes. Keep every action that "
            "was already clean. Output the complete revised DayPlan.\n\n"
            + TOKEN_RULES
        ),
        output_schema=DayPlan,
        output_key="day_plan",
        generate_content_config=GENCFG_PLANNER,
    )


def make_policy_loop() -> LoopAgent:
    return LoopAgent(
        name="policy_loop",
        max_iterations=3,
        sub_agents=[PolicyGate(name="policy_gate"), make_critic(), make_reviser()],
    )


def make_dispatcher() -> Dispatcher:
    return Dispatcher(name="hearth_dispatcher")


_STAGE_FACTORIES = {
    "gathered": make_gatherers,
    "planned": make_planner,
    "reviewed": make_policy_loop,
    "dispatched": make_dispatcher,
}


def build_pipeline(done_stages: set[str] | None = None) -> SequentialAgent:
    """Assemble the root agent from the stages that still need to run — this is
    how a killed run resumes: completed stages come back as checkpointed state,
    not re-execution."""
    done = done_stages or set()
    subs = [_STAGE_FACTORIES[s]() for s in STAGE_ORDER if s not in done]
    if not subs:
        subs = [_STAGE_FACTORIES["dispatched"]()]  # re-dispatch is idempotent
    return SequentialAgent(name="hearth_pipeline", sub_agents=subs)
