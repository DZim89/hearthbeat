"""The action path — the house PULLS, the cloud never pushes.

Every POLL_SECONDS the poller:
  1. claims `pending_actions` with status=approved (Firestore transaction — two
     pollers can't double-fire), REHYDRATES tokens locally, re-validates against
     the same policy file (third enforcement), executes in Home Assistant.
  2. sends the HA companion-app actionable notification for fresh permission
     slips (Approve / Deny buttons on a real phone).
  3. reads the approval helper entity that an additive HA automation fills when
     a notification button is tapped, and flips the slip + action accordingly.

No inbound socket exists anywhere in the house. Compromise the cloud and the
worst you can do is add an action the whitelist refuses."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from google.cloud import firestore

from app.policy import load_policy
from app.stores import ACTIONS, SLIPS, db
from house import config, events, ha, scrub

APPROVE_PREFIX = "HEARTH_APPROVE_"
DENY_PREFIX = "HEARTH_DENY_"


def _rehydrate_action(action: dict, tmap: scrub.TokenMap) -> dict:
    return json.loads(scrub.rehydrate(json.dumps(action), tmap))


def _claim(ref) -> bool:
    tx = db().transaction()

    @firestore.transactional
    def _run(txn) -> bool:
        snap = ref.get(transaction=txn)
        if (snap.to_dict() or {}).get("status") != "approved":
            return False
        txn.update(
            ref,
            {
                "status": "claimed",
                "claimed_by": config.HOSTNAME,
                "claimed_at": firestore.SERVER_TIMESTAMP,
                "attempts": firestore.Increment(1),
            },
        )
        return True

    return _run(tx)


def _execute(doc_id: str, doc: dict, tmap: scrub.TokenMap) -> None:
    policy = load_policy(config.REPO_ROOT / "config" / "policy.yaml")
    action_tok = doc.get("action") or {}
    human_approved = bool(doc.get("sensitive"))
    violations = policy.check_action(
        action_tok, now=datetime.now(policy.tz), human_approved=human_approved
    )
    if violations:
        db().collection(ACTIONS).document(doc_id).update(
            {"status": "refused_by_house", "result": ",".join(violations)}
        )
        events.emit("action_refused_by_house", action_id=doc_id, rules=violations)
        return

    a = _rehydrate_action(action_tok, tmap)   # tokens -> real, ONLY here, in-house
    domain, service = doc.get("ha_domain", ""), doc.get("ha_service", "")
    atype = a.get("action_type")

    if atype == "media_pause":
        ha.call_service(domain, service, {"entity_id": a["entity"]})
    elif atype == "calendar_create_event":
        ha.call_service(
            domain,
            service,
            {
                "entity_id": config.CALENDAR_ENTITY,
                "summary": a.get("title", "[hearthbeat]"),
                "start_date_time": a.get("start_iso"),
                "end_date_time": a.get("end_iso"),
                "description": a.get("why", ""),
            },
        )
    elif atype in ("notify_family_member", "send_briefing"):
        title = (
            "hearthbeat · morning briefing"
            if atype == "send_briefing"
            else f"hearthbeat → {a.get('entity')}"
        )
        ha.call_service("notify", config.NOTIFY_SERVICE, {
            "title": title,
            "message": a.get("message", "")[:600],
        })
    else:  # policy already refused unknown types; belt and suspenders
        raise ValueError(f"no executor for action_type {atype!r}")

    db().collection(ACTIONS).document(doc_id).update(
        {"status": "done", "finished_at": firestore.SERVER_TIMESTAMP, "result": "ok"}
    )
    events.emit("action_executed", action_id=doc_id, action_type=str(atype))
    print(f"[poller] executed {doc_id} ({atype})")


def _notify_slips(tmap: scrub.TokenMap) -> None:
    for snap in db().collection(SLIPS).where("status", "==", "pending").get():
        s = snap.to_dict() or {}
        message = scrub.rehydrate(str(s.get("message", "")), tmap)
        target = scrub.rehydrate(str(s.get("target", "")), tmap)
        try:
            ha.call_service("notify", config.NOTIFY_SERVICE, {
                "title": "hearthbeat · permission slip",
                "message": f"Send to {target}: “{message[:200]}”",
                "data": {
                    "actions": [
                        {"action": f"{APPROVE_PREFIX}{snap.id}", "title": "Approve"},
                        {"action": f"{DENY_PREFIX}{snap.id}", "title": "Deny"},
                    ]
                },
            })
            snap.reference.update(
                {"status": "notified", "notified_at": firestore.SERVER_TIMESTAMP}
            )
            events.emit("slip_notified", slip_id=snap.id, target=str(s.get("target")))
            print(f"[poller] permission slip sent to phone: {snap.id}")
        except Exception as e:  # noqa: BLE001
            print(f"[poller] slip notify failed {snap.id}: {e}")


def _decide(slip_id: str, approved: bool, via: str) -> None:
    slip_ref = db().collection(SLIPS).document(slip_id)
    s = slip_ref.get().to_dict() or {}
    if not s or s.get("status") in ("approved", "denied", "done"):
        return
    status = "approved" if approved else "denied"
    slip_ref.update(
        {"status": status, "decided_at": firestore.SERVER_TIMESTAMP, "decided_via": via}
    )
    db().collection(ACTIONS).document(s["action_id"]).update({"status": status})
    events.emit("slip_decided", slip_id=slip_id, decision=status, via=via)
    print(f"[poller] slip {slip_id}: {status} via {via}")


def _check_approval_helper() -> None:
    state = ha.get_state(config.APPROVAL_HELPER)
    if not state:
        return
    value = str(state.get("state", ""))
    if value.startswith(APPROVE_PREFIX):
        _decide(value.removeprefix(APPROVE_PREFIX), True, "ha_mobile")
    elif value.startswith(DENY_PREFIX):
        _decide(value.removeprefix(DENY_PREFIX), False, "ha_mobile")
    else:
        return
    ha.call_service(
        "input_text", "set_value", {"entity_id": config.APPROVAL_HELPER, "value": ""}
    )


def _judge_auto_approve() -> None:
    """Judge mode has no phone: slips auto-approve after a visible delay,
    honestly labeled decided_via=judge_auto."""
    now = datetime.now(timezone.utc)
    for snap in db().collection(SLIPS).where("status", "==", "notified").get():
        s = snap.to_dict() or {}
        at = s.get("notified_at")
        if at and (now - at).total_seconds() > config.JUDGE_AUTO_APPROVE_SECONDS:
            _decide(snap.id, True, "judge_auto")


def cycle() -> None:
    tmap = scrub.load_map(config.TOKEN_MAP_PATH)
    for snap in db().collection(ACTIONS).where("status", "==", "approved").get():
        if _claim(snap.reference):
            try:
                _execute(snap.id, snap.reference.get().to_dict() or {}, tmap)
            except Exception as e:  # noqa: BLE001
                snap.reference.update({"status": "failed", "result": str(e)[:300]})
                events.emit("action_failed", action_id=snap.id, error=str(e)[:200])
                print(f"[poller] {snap.id} failed: {e}")
    _notify_slips(tmap)
    try:
        _check_approval_helper()
    except Exception as e:  # noqa: BLE001
        print(f"[poller] approval helper read failed: {e}")
    if config.SIMULATED:
        _judge_auto_approve()


def main() -> None:
    print(f"[poller] every {config.POLL_SECONDS}s against {config.HA_URL}")
    while True:
        try:
            cycle()
        except Exception as e:  # noqa: BLE001
            print(f"[poller] cycle failed: {e}")
        time.sleep(config.POLL_SECONDS)


if __name__ == "__main__":
    main()
