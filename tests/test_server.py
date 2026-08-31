"""Mission Control run-window belt filter (the exact-run_id equality filter is
in the Firestore queries themselves — app/server.py missioncontrol())."""

from datetime import datetime, timedelta, timezone

from app.server import _within_run_window

T0 = datetime(2026, 8, 31, 13, 45, tzinfo=timezone.utc)
T_END = T0 + timedelta(minutes=3)


def _doc(offset_s):
    return {"created_at": T0 + timedelta(seconds=offset_s)}


def test_row_inside_window_shown():
    assert _within_run_window(_doc(30), T0, T_END)


def test_row_before_window_hidden():
    assert not _within_run_window(_doc(-500), T0, T_END)


def test_row_after_window_hidden():
    assert not _within_run_window(_doc(500), T0, T_END)


def test_skew_tolerance():
    assert _within_run_window(_doc(-60), T0, T_END)          # within 120s skew
    assert _within_run_window(_doc(180 + 60), T0, T_END)      # end + 60s


def test_running_run_uses_now_as_end():
    recent = {"created_at": datetime.now(timezone.utc) - timedelta(seconds=10)}
    assert _within_run_window(recent, datetime.now(timezone.utc) - timedelta(minutes=5), None)


def test_missing_timestamps_fall_back_to_id_filter():
    assert _within_run_window({}, T0, T_END)
    assert _within_run_window(_doc(0), None, None)
