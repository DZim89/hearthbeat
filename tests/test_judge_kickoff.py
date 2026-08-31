"""Judge-kickoff readiness polling: success, partial readiness, timeout
wording, probe retry, and non-2xx trigger failure."""

import time
from types import SimpleNamespace

import pytest

from infra import judge_kickoff as jk


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def monotonic(self):
        return self.t

    def sleep(self, s):
        self.t += s


@pytest.fixture()
def clock(monkeypatch):
    c = FakeClock()
    monkeypatch.setattr(jk.time, "monotonic", c.monotonic)
    monkeypatch.setattr(jk.time, "sleep", c.sleep)
    return c


def test_wait_seeded_retries_until_ready(clock, monkeypatch):
    states = iter([(False, False), (True, False), (True, True)])
    monkeypatch.setattr(jk, "_readiness", lambda: next(states))
    jk.wait_seeded(deadline=clock.monotonic() + 60)  # returns without raising


def test_wait_seeded_probe_errors_are_retried(clock, monkeypatch):
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ConnectionError("emulator booting")
        return True, True

    monkeypatch.setattr(jk, "_readiness", flaky)
    jk.wait_seeded(deadline=clock.monotonic() + 60)
    assert calls["n"] == 3


def test_wait_seeded_timeout_names_missing_pieces(clock, monkeypatch):
    monkeypatch.setattr(jk, "_readiness", lambda: (True, False))
    with pytest.raises(SystemExit) as ei:
        jk.wait_seeded(deadline=clock.monotonic() + 10)
    msg = str(ei.value)
    assert "school_mail" in msg and "docker compose logs house" in msg
    assert "homes/main" not in msg  # only the ACTUALLY missing piece is named


def test_wait_health_timeout_actionable(clock, monkeypatch):
    monkeypatch.setattr(jk.httpx, "get", lambda *a, **k: (_ for _ in ()).throw(ConnectionError()))
    with pytest.raises(SystemExit) as ei:
        jk.wait_health(deadline=clock.monotonic() + 10)
    assert "/health" in str(ei.value)


def test_fire_non_2xx_is_failure(monkeypatch):
    monkeypatch.setattr(
        jk.httpx, "post",
        lambda *a, **k: SimpleNamespace(status_code=500, text="Internal Server Error"),
    )
    with pytest.raises(SystemExit, match="KICKOFF FAILED"):
        jk.fire()


def test_fire_success(monkeypatch, capsys):
    monkeypatch.setattr(
        jk.httpx, "post",
        lambda *a, **k: SimpleNamespace(status_code=200, text='{"status":"done"}'),
    )
    jk.fire()
    assert "missioncontrol" in capsys.readouterr().out
