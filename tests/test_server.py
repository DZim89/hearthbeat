"""Mission Control run-window belt filter — FAIL-CLOSED semantics: the exact
run_id equality filter lives in the Firestore queries (app/server.py
missioncontrol()); this belt additionally requires every displayed row to sit
inside the run's own server-timestamp window, with only a disclosed ±10s
clock-skew tolerance. Missing timestamps show nothing."""

from datetime import datetime, timedelta, timezone

from app.server import _within_run_window

T0 = datetime(2026, 8, 31, 13, 45, tzinfo=timezone.utc)
T_END = T0 + timedelta(minutes=3)


def _doc(offset_s):
    return {"created_at": T0 + timedelta(seconds=offset_s)}


def test_row_inside_window_shown():
    assert _within_run_window(_doc(30), T0, T_END)


def test_row_before_window_hidden():
    assert not _within_run_window(_doc(-11), T0, T_END)


def test_row_after_window_hidden():
    assert not _within_run_window(_doc(180 + 11), T0, T_END)


def test_exact_boundaries_with_disclosed_skew():
    assert _within_run_window(_doc(-10), T0, T_END)       # start - 10s: allowed
    assert _within_run_window(_doc(180 + 10), T0, T_END)  # end + 10s: allowed
    assert not _within_run_window(_doc(-10.5), T0, T_END)
    assert not _within_run_window(_doc(190.5), T0, T_END)


def test_running_run_uses_now_as_end():
    now = datetime.now(timezone.utc)
    assert _within_run_window({"created_at": now - timedelta(seconds=10)},
                              now - timedelta(minutes=5), None)
    assert not _within_run_window({"created_at": now - timedelta(minutes=10)},
                                  now - timedelta(minutes=5), None)


def test_missing_timestamps_fail_closed():
    assert not _within_run_window({}, T0, T_END)          # row without created_at
    assert not _within_run_window(_doc(0), None, None)    # run without started_at
    assert not _within_run_window({}, None, None)


# ---- provenance badge -------------------------------------------------------

def test_pure_scheduled_run_renders_green():
    from app.server import _provenance_badge
    label, cls, by = _provenance_badge(
        {"trigger_source": "scheduled", "triggered_by": "sa@x",
         "current_trigger_source": "scheduled", "current_triggered_by": "sa@x"})
    assert (label, cls, by) == ("scheduled", "scheduled", "sa@x")


def test_manual_resume_renders_mixed_never_scheduled_only():
    from app.server import _provenance_badge
    label, cls, by = _provenance_badge(
        {"trigger_source": "scheduled", "triggered_by": "sa@x", "attempt": 2,
         "current_trigger_source": "manual", "current_triggered_by": "operator"})
    assert "scheduled initial" in label and "manual resume" in label and "2" in label
    assert cls == "manual"           # the green class is unreachable when mixed
    assert by == "sa@x → operator"


def test_manual_only_run_renders_manual():
    from app.server import _provenance_badge
    label, cls, _ = _provenance_badge(
        {"trigger_source": "manual", "triggered_by": "op"})
    assert (label, cls) == ("manual", "manual")


def test_scheduled_manual_scheduled_renders_mixed_chain():
    from app.server import _provenance_badge
    doc = {
        "trigger_source": "scheduled", "triggered_by": "sa@x", "attempt": 3,
        "current_trigger_source": "scheduled", "current_triggered_by": "sa@x",
        "attempt_history": [
            {"attempt": 1, "source": "scheduled", "principal": "sa@x"},
            {"attempt": 2, "source": "manual", "principal": "operator"},
            {"attempt": 3, "source": "scheduled", "principal": "sa@x"},
        ]
    }
    label, cls, by = _provenance_badge(doc)
    assert label == "scheduled → manual → scheduled (attempt 3)"
    assert cls == "manual"  # mixed provenance MUST NOT be green scheduled
    assert by == "sa@x → operator → sa@x"


def test_pure_scheduled_with_history_renders_green():
    from app.server import _provenance_badge
    doc = {
        "trigger_source": "scheduled", "triggered_by": "sa@x", "attempt": 2,
        "current_trigger_source": "scheduled", "current_triggered_by": "sa@x",
        "attempt_history": [
            {"attempt": 1, "source": "scheduled", "principal": "sa@x"},
            {"attempt": 2, "source": "scheduled", "principal": "sa@x"},
        ]
    }
    label, cls, by = _provenance_badge(doc)
    assert label == "scheduled"
    assert cls == "scheduled"
    assert by == "sa@x"
