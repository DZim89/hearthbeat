"""Structured-output schemas for the pipeline. All person/room references are in
token space ([[P_DAD]], [[P_KID1]]…) — known family aliases are tokenized
house-side before anything reaches this pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ActionType = Literal[
    "media_pause",            # pause a kid-facing media player
    "calendar_create_event",  # write a fix/entry to the family calendar
    "notify_family_member",   # message a person — sensitive, needs a permission slip
    "send_briefing",          # morning briefing to the household lead
]


class PlannedAction(BaseModel):
    action_type: ActionType
    entity: str = Field(description="Target entity or person token, e.g. media_player.family_tv or [[P_GRANDMA]]")
    when: str = Field(default="now", description="'now' or ISO-8601 local time to act")
    why: str = Field(description="One sentence: why this action, grounded in gathered facts")
    sensitive: bool = Field(default=False, description="True if a human must approve first")
    title: str = Field(default="", description="calendar_create_event: event title")
    start_iso: str = Field(default="", description="calendar_create_event: ISO start")
    end_iso: str = Field(default="", description="calendar_create_event: ISO end")
    message: str = Field(default="", description="notify/briefing: the message text (token space)")


class DayPlan(BaseModel):
    summary: str = Field(description="Two sentences: the household's day at a glance")
    briefing_md: str = Field(description="Markdown morning briefing for the household lead")
    actions: list[PlannedAction] = Field(default_factory=list)


class Critique(BaseModel):
    grade: Literal["pass", "fail"]
    plan_hash: str = Field(description="Echo the plan hash you were shown, verbatim")
    required_changes: list[str] = Field(default_factory=list)


class PiiSpan(BaseModel):
    text: str = Field(description="The exact span from the input that is personal information")
    kind: str = Field(description="name | phone | email | address | school | id | other")


class PiiFindings(BaseModel):
    spans: list[PiiSpan] = Field(default_factory=list)
