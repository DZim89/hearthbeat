"""One-shot HA wiring after the two 30-second UI acts (Local Calendar +
input_text helper exist). Idempotent; everything additive and reversible.

    python -m house.setup_ha            # verify + install bridge + seed calendar
    python -m house.setup_ha --verify   # checks only
"""

from __future__ import annotations

import sys
from datetime import datetime, timedelta

import httpx

from house import config, ha

AUTOMATION_ID = "hearthbeat_approval_bridge"
AUTOMATION = {
    "alias": "hearthbeat approval bridge",
    "description": "Copies tapped hearthbeat notification actions into the helper the poller polls.",
    "mode": "queued",
    "triggers": [{"trigger": "event", "event_type": "mobile_app_notification_action"}],
    "conditions": [
        {
            "condition": "template",
            "value_template": "{{ trigger.event.data.action.startswith('HEARTH_') }}",
        }
    ],
    "actions": [
        {
            "action": "input_text.set_value",
            "target": {"entity_id": config.APPROVAL_HELPER},
            "data": {"value": "{{ trigger.event.data.action }}"},
        }
    ],
}


def verify() -> bool:
    ok = True
    for eid, label in [
        (config.CALENDAR_ENTITY, "Local Calendar (Donny UI act #3)"),
        (config.APPROVAL_HELPER, "approval helper (Donny UI act #4)"),
    ]:
        state = ha.get_state(eid)
        print(f"  {eid}: {'OK — ' + str(state.get('state')) if state else 'MISSING — ' + label}")
        ok = ok and state is not None
    return ok


def install_bridge() -> None:
    r = httpx.post(
        f"{config.HA_URL}/api/config/automation/config/{AUTOMATION_ID}",
        headers={"Authorization": f"Bearer {config.HA_TOKEN}"},
        json=AUTOMATION,
        timeout=20,
    )
    r.raise_for_status()
    print(f"  approval-bridge automation installed ({r.json()})")


def seed_calendar() -> None:
    """The DISCLOSED demo collision: soccer vs dinner at Grandma's, tomorrow.
    Names come from the LOCAL token map at runtime — never from this file."""
    from house import scrub

    tmap = scrub.load_map(config.TOKEN_MAP_PATH)
    tz = datetime.now().astimezone().tzinfo
    tomorrow = (datetime.now(tz) + timedelta(days=1)).date()
    events = [
        (scrub.rehydrate("[[P_KID1]] soccer practice", tmap), "17:00", "18:30",
         "bring cleats"),
        (scrub.rehydrate("Family dinner at [[P_GRANDMA]]'s", tmap), "17:30", "19:00",
         "SEEDED DEMO EVENT (disclosed): overlaps soccer practice"),
    ]
    for summary, start, end, desc in events:
        ha.call_service(
            "calendar",
            "create_event",
            {
                "entity_id": config.CALENDAR_ENTITY,
                "summary": summary,
                "start_date_time": f"{tomorrow}T{start}:00",
                "end_date_time": f"{tomorrow}T{end}:00",
                "description": desc,
            },
        )
        print(f"  seeded: {summary} {start}-{end}")


def main() -> None:
    print("[setup_ha] verifying prerequisites:")
    if not verify():
        sys.exit("prerequisites missing — do the two HA UI acts first")
    if "--verify" in sys.argv:
        return
    print("[setup_ha] installing approval bridge:")
    install_bridge()
    print("[setup_ha] seeding the disclosed demo collision:")
    seed_calendar()
    print("[setup_ha] done — run `python -m house.run_all` next")


if __name__ == "__main__":
    main()
