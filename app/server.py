"""Cloud Run service surface.

  POST /run            — Cloud Scheduler ONLY (OIDC verified in-app). The single
                         code path that may label a run trigger_source=scheduled.
  POST /trigger        — manual/filming/judge entrypoint; labeled manual, and a
                         manual RESUME of a scheduled run renders as mixed provenance.
  GET  /missioncontrol — public read-only dashboard (token-space data only).
  GET  /slip/{id}      — console approval standby path (token-gated).
  GET  /health
"""

from __future__ import annotations

import html
import os
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from datetime import datetime, timedelta, timezone

from app import ledger, runcontrol
from app.stores import ACTIONS, RUNS, SLIPS, db, is_simulated

api = FastAPI(title="hearthbeat", docs_url=None, redoc_url=None)

SCHEDULER_SA = os.environ.get(
    "SCHEDULER_INVOKER_SA", "sa-home@new-prompt-490003.iam.gserviceaccount.com"
)


def _verify_scheduler_oidc(request: Request) -> str:
    """Only a valid OIDC token from the scheduler SA reaches trigger_source=scheduled."""
    auth = request.headers.get("authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(403, "missing bearer token")
    token = auth.removeprefix("Bearer ").strip()
    try:
        from google.auth.transport import requests as ga_requests
        from google.oauth2 import id_token

        audience = os.environ.get("SERVICE_URL") or str(request.base_url).rstrip("/")
        claims = id_token.verify_oauth2_token(token, ga_requests.Request(), audience=audience)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(403, f"OIDC verification failed: {e}") from e
    email = claims.get("email", "")
    if not claims.get("email_verified") or email != SCHEDULER_SA:
        raise HTTPException(403, f"caller {email!r} is not the scheduler service account")
    return email


def _verify_trigger_token(request: Request) -> None:
    if is_simulated():
        return  # judge mode: open manual trigger, honestly labeled
    expected = os.environ.get("HEARTH_TRIGGER_TOKEN", "")
    if not expected or request.headers.get("x-hearth-token") != expected:
        raise HTTPException(403, "bad or missing X-Hearth-Token")


def _require_valid_egress_config() -> None:
    """Non-2xx BEFORE any run doc is claimed — a stranded status=running doc
    would block the real cron for the staleness window."""
    errors = ledger.validate_egress_config()
    if errors:
        raise HTTPException(500, "egress guard config invalid: " + "; ".join(errors))


@api.post("/run")
async def run_scheduled(request: Request) -> dict[str, Any]:
    email = _verify_scheduler_oidc(request)
    _require_valid_egress_config()
    return await runcontrol.execute_run(trigger_source="scheduled", triggered_by=email)


@api.post("/trigger")
async def run_manual(
    request: Request,
    run_id: str | None = Query(default=None),
    red_team: int = Query(default=0),
) -> dict[str, Any]:
    _verify_trigger_token(request)
    _require_valid_egress_config()
    caller = "judge-mode" if is_simulated() else "operator-token"
    return await runcontrol.execute_run(
        run_id,
        trigger_source="manual",
        triggered_by=caller,
        red_team=bool(red_team),
    )


@api.get("/slip/{slip_id}/{decision}")
async def decide_slip(slip_id: str, decision: str, request: Request) -> dict[str, Any]:
    """Console-approval standby path (primary path is the HA actionable
    notification handled house-side). Approving flips the underlying action to
    approved; the house poller does the rest."""
    _verify_trigger_token(request)
    if decision not in ("approve", "deny"):
        raise HTTPException(400, "decision must be approve|deny")
    slip_ref = db().collection(SLIPS).document(slip_id)
    snap = slip_ref.get()
    if not snap.exists:
        raise HTTPException(404, "no such permission slip")
    status = "approved" if decision == "approve" else "denied"
    slip_ref.update({"status": status, "decided_via": "console"})
    db().collection(ACTIONS).document((snap.to_dict() or {})["action_id"]).update(
        {"status": status if status == "approved" else "denied"}
    )
    return {"slip": slip_id, "status": status, "decided_via": "console"}


@api.get("/health")
async def healthz() -> dict[str, str]:
    return {"ok": "true", "service": "hearthbeat"}


@api.get("/")
async def index() -> RedirectResponse:
    return RedirectResponse("/missioncontrol")


# ---------------------------------------------------------------------------
# Mission Control — public, read-only, token-space-only by construction.
# ---------------------------------------------------------------------------

_STYLE = """
body{background:#12141a;color:#e8e6e0;font:15px/1.5 system-ui,sans-serif;margin:0;padding:2rem;max-width:1000px;margin-inline:auto}
h1{font-size:1.4rem;letter-spacing:.04em} h2{font-size:1.05rem;margin-top:1.8rem;color:#f0c674}
.badge{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.8rem;font-weight:600;vertical-align:middle}
.scheduled{background:#1d3a24;color:#7ee08a;border:1px solid #2e6b3a}
.manual{background:#3a2f1d;color:#e0c47e;border:1px solid #6b572e}
.stage{display:inline-block;margin-right:.5rem;padding:.3rem .7rem;border-radius:6px;background:#1c1f27;border:1px solid #2a2e39}
.stage.done{border-color:#2e6b3a;color:#7ee08a}
table{border-collapse:collapse;width:100%;margin-top:.5rem}
td,th{border-bottom:1px solid #2a2e39;padding:.45rem .6rem;text-align:left;font-size:.9rem}
.deny{color:#e07e7e}.ok{color:#7ee08a}.muted{color:#8b8fa3}
pre{background:#1c1f27;border:1px solid #2a2e39;border-radius:8px;padding:1rem;white-space:pre-wrap;font-size:.88rem}
.kv{color:#8b8fa3;font-size:.85rem}
"""


def _provenance_badge(data: dict) -> tuple[str, str, str]:
    """(badge_label, badge_css_class, by_line). A run only renders the green
    scheduled badge when BOTH its immutable initial source AND its current
    attempt are scheduled — a manually resumed scheduled run renders as mixed
    provenance, never as scheduled-only."""
    initial = str(data.get("trigger_source", "—"))
    current = str(data.get("current_trigger_source") or initial)
    by_initial = str(data.get("triggered_by", "—"))
    by_current = str(data.get("current_triggered_by") or by_initial)
    if current != initial:
        label = f"{initial} initial → {current} resume (attempt {data.get('attempt', '?')})"
        return label, "manual", f"{by_initial} → {by_current}"
    cls = "scheduled" if current == "scheduled" else "manual"
    return current, cls, by_initial


def _within_run_window(doc: dict, started_at, ended_at, *, skew_s: int = 10) -> bool:
    """Belt on top of the exact run_id equality filter: a displayed row must
    have been created inside the run's own server-timestamp window (start ...
    end, or now while running). FAIL CLOSED: a row with no created_at, or a
    run with no started_at, shows nothing. The only tolerance is a disclosed
    ±10s clock-skew allowance (all timestamps are Firestore server time)."""
    ts = doc.get("created_at")
    if ts is None or started_at is None:
        return False
    end = ended_at or datetime.now(timezone.utc)
    skew = timedelta(seconds=skew_s)
    return (started_at - skew) <= ts <= (end + skew)


@api.get("/missioncontrol", response_class=HTMLResponse)
async def missioncontrol(run: str | None = Query(default=None)) -> str:
    run_id = run or runcontrol.today_run_id()
    snap = db().collection(RUNS).document(run_id).get()
    data = (snap.to_dict() or {}) if snap.exists else {}
    started_at = data.get("started_at")
    finished_at = data.get("finished_at")
    evidence_note = ""
    if data and started_at is None:
        # Fail closed: without a run start timestamp no action/slip evidence
        # can be window-verified — show none and say so.
        actions, slips = [], []
        evidence_note = "evidence incomplete — run has no start timestamp; action/slip rows withheld"
    else:
        actions = [
            a
            for a in (
                {"id": d.id, **(d.to_dict() or {})}
                for d in db().collection(ACTIONS).where("run_id", "==", run_id).get()
            )
            if _within_run_window(a, started_at, finished_at)
        ]
        slips = [
            s
            for s in (
                {"id": d.id, **(d.to_dict() or {})}
                for d in db().collection(SLIPS).where("run_id", "==", run_id).get()
            )
            if _within_run_window(s, started_at, finished_at)
        ]

    e = html.escape
    badge_label, badge_cls, by_line = _provenance_badge(data)
    trig = e(badge_label)
    stages = "".join(
        f'<span class="stage {"done" if (data.get("stage_status") or {}).get(s) == "done" else ""}">{s}</span>'
        for s in runcontrol.STAGE_ORDER
    )
    action_rows = "".join(
        f"<tr><td>{e(str((a.get('action') or {}).get('action_type')))}</td>"
        f"<td>{e(str((a.get('action') or {}).get('entity')))}</td>"
        f"<td class={'ok' if a.get('status') in ('done', 'approved') else 'muted'}>{e(str(a.get('status')))}</td>"
        f"<td>{'yes' if a.get('sensitive') else ''}</td>"
        f"<td class=muted>{e(str((a.get('action') or {}).get('why', '')))[:120]}</td></tr>"
        for a in actions
    ) or "<tr><td colspan=5 class=muted>none yet</td></tr>"
    denial_rows = "".join(
        f"<tr><td class=deny>{e(str(d.get('rule')))}</td><td>{e(str(d.get('stage')))}</td>"
        f"<td class=muted>{e(str(d.get('detail', '')))[:120]}</td></tr>"
        for d in (data.get("denials") or [])
    ) or "<tr><td colspan=3 class=muted>none — no policy violations</td></tr>"
    slip_rows = "".join(
        f"<tr><td>{e(str(s.get('action_type')))}</td><td>{e(str(s.get('target')))}</td>"
        f"<td>{e(str(s.get('status')))}</td><td class=muted>{e(str(s.get('message', '')))[:100]}</td></tr>"
        for s in slips
    ) or "<tr><td colspan=4 class=muted>none</td></tr>"
    egress = data.get("egress") or {}
    cost_cents = round(int(data.get("cost_microcents", 0)) / 1_000_000, 4)

    return f"""<!doctype html><html><head><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<meta http-equiv=refresh content=10><title>hearthbeat · mission control</title>
<style>{_STYLE}</style></head><body>
<h1>hearthbeat <span class=muted>/ mission control</span></h1>
<p class=kv>run <b>{e(run_id)}</b> · status <b>{e(str(data.get('status', 'no run yet')))}</b>
· trigger <span class="badge {badge_cls}">{trig}</span>
· by {e(by_line)}
· attempt {e(str(data.get('attempt', '—')))}
· window {e(str(started_at)[:19])} → {e(str(finished_at)[:19]) if finished_at else 'running'}
· read-only, auto-refreshes</p>
{f'<p class="kv deny">{e(evidence_note)}</p>' if evidence_note else ''}
<h2>Pipeline</h2><p>{stages}</p>
<h2>Day summary</h2><pre>{e(str(data.get('summary', '— pipeline has not planned yet —')))}</pre>
<h2>Morning briefing (token space — known family aliases are tokenized house-side)</h2>
<pre>{e(str(data.get('briefing_md', '—')))}</pre>
<h2>Actions</h2><table><tr><th>action</th><th>entity</th><th>status</th><th>needs human</th><th>why</th></tr>{action_rows}</table>
<h2>Permission slips</h2><table><tr><th>action</th><th>target</th><th>status</th><th>message</th></tr>{slip_rows}</table>
<h2>Policy denials (red team lands here)</h2><table><tr><th>rule</th><th>stage</th><th>detail</th></tr>{denial_rows}</table>
<h2>Privacy &amp; spend</h2>
<p class=kv>egress guard: <b>{e(str(egress.get('checks', 0)))}</b> outbound model calls scanned,
<b class={'deny' if egress.get('matches') else 'ok'}>{e(str(egress.get('matches', 0)))}</b> protected-alias matches
· model spend this run: <b>{cost_cents}¢</b></p>
<p class=muted>hearthbeat — an autonomous household agent. No chat UI: it plans, a policy
critic argues with it, a human approves anything personal, and the house pulls
its actions — the cloud can't reach in.</p>
</body></html>"""
