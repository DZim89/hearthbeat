"""Unit tests for house/action_poller — fail-closed slip enforcement and local policy authority."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from app.stores import ACTIONS, SLIPS
from house import action_poller, scrub

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE_MAP = REPO_ROOT / "fixtures" / "token_map.fixture.json"


class _Snap:
    def __init__(self, doc_id: str, data: dict | None, ref: _DocRef | None = None):
        self.id = doc_id
        self._data = data
        self.reference = ref

    def to_dict(self):
        return dict(self._data) if self._data is not None else None


class _DocRef:
    def __init__(self, coll: _Collection, doc_id: str):
        self._coll = coll
        self.id = doc_id

    def get(self):
        return _Snap(self.id, self._coll.docs.get(self.id), self)

    def update(self, fields: dict):
        self._coll.docs.setdefault(self.id, {}).update(fields)


class _Query:
    def __init__(self, coll: _Collection, field: str, op: str, value):
        self._coll = coll
        self._field = field
        self._op = op
        self._value = value

    def get(self):
        out = []
        for doc_id, data in self._coll.docs.items():
            if self._op == "==" and data.get(self._field) == self._value:
                out.append(_Snap(doc_id, data, _DocRef(self._coll, doc_id)))
        return out


class _Collection:
    def __init__(self):
        self.docs: dict[str, dict] = {}

    def document(self, doc_id: str) -> _DocRef:
        return _DocRef(self, doc_id)

    def where(self, field: str, op: str, value) -> _Query:
        return _Query(self, field, op, value)


class _FakeDB:
    def __init__(self):
        self._colls = {ACTIONS: _Collection(), SLIPS: _Collection()}

    def collection(self, name: str) -> _Collection:
        return self._colls.setdefault(name, _Collection())


@pytest.fixture()
def poller_env(monkeypatch):
    fake_db = _FakeDB()
    ha_calls: list[tuple[str, str, dict]] = []
    emitted: list[tuple[str, dict]] = []

    monkeypatch.setattr(action_poller, "db", lambda: fake_db)
    monkeypatch.setattr(action_poller.config, "REPO_ROOT", REPO_ROOT)
    monkeypatch.setattr(
        action_poller.ha,
        "call_service",
        lambda domain, service, data: ha_calls.append((domain, service, data)),
    )
    monkeypatch.setattr(
        action_poller.events,
        "emit",
        lambda event_type, **kw: emitted.append((event_type, kw)),
    )
    return fake_db, ha_calls, emitted, scrub.load_map(FIXTURE_MAP)


def test_sensitive_target_refused_even_if_doc_sensitive_cleared(poller_env):
    fake_db, ha_calls, emitted, tmap = poller_env
    doc = {
        "sensitive": False,  # cloud-writable field cleared by attacker
        "action": {
            "action_type": "notify_family_member",
            "entity": "[[P_GRANDMA]]",
            "message": "Dinner at 6",
            "sensitive": True,
        },
        "ha_domain": "notify",
        "ha_service": "send",
    }
    fake_db.collection(ACTIONS).docs["a1"] = dict(doc)

    action_poller._execute("a1", doc, tmap)

    assert ha_calls == []
    assert fake_db.collection(ACTIONS).docs["a1"]["status"] == "refused_by_house"
    assert fake_db.collection(ACTIONS).docs["a1"]["result"] == "slip_not_verified"
    assert emitted[-1] == ("action_refused_by_house", {"action_id": "a1", "rules": ["slip_not_verified"]})


def test_action_sensitive_flag_requires_verified_slip_channel(poller_env):
    fake_db, ha_calls, _emitted, tmap = poller_env
    doc = {
        "sensitive": False,
        "action": {
            "action_type": "notify_family_member",
            "entity": "[[P_DAD]]",
            "message": "Check calendar",
            "sensitive": True,
        },
        "ha_domain": "notify",
        "ha_service": "send",
    }
    fake_db.collection(ACTIONS).docs["a2"] = dict(doc)
    fake_db.collection(SLIPS).docs["a2"] = {
        "status": "approved",
        "decided_via": "cloud_forged",
    }

    action_poller._execute("a2", doc, tmap)

    assert ha_calls == []
    assert fake_db.collection(ACTIONS).docs["a2"]["status"] == "refused_by_house"
    assert fake_db.collection(ACTIONS).docs["a2"]["result"] == "slip_not_verified"


def test_verified_slip_executes_with_rehydration(poller_env):
    fake_db, ha_calls, emitted, tmap = poller_env
    doc = {
        "sensitive": True,
        "action": {
            "action_type": "notify_family_member",
            "entity": "[[P_GRANDMA]]",
            "message": "Pick up [[P_KID1]] at 3pm",
            "sensitive": True,
        },
        "ha_domain": "notify",
        "ha_service": "send",
    }
    fake_db.collection(ACTIONS).docs["a3"] = dict(doc)
    fake_db.collection(SLIPS).docs["a3"] = {
        "status": "approved",
        "decided_via": "ha_mobile",
    }

    action_poller._execute("a3", doc, tmap)

    assert len(ha_calls) == 1
    domain, service, payload = ha_calls[0]
    assert (domain, service) == ("notify", action_poller.config.NOTIFY_SERVICE)
    assert "[[P_GRANDMA]]" not in payload["title"]
    assert "[[P_KID1]]" not in payload["message"]
    assert fake_db.collection(ACTIONS).docs["a3"]["status"] == "done"
    assert emitted[-1] == ("action_executed", {"action_id": "a3", "action_type": "notify_family_member"})


def test_execute_uses_local_policy_domain_and_service(poller_env):
    fake_db, ha_calls, _emitted, tmap = poller_env
    doc = {
        "sensitive": False,
        "action": {"action_type": "media_pause", "entity": "media_player.family_tv"},
        # Tampered cloud-supplied service metadata must be ignored in favor of policy.yaml
        "ha_domain": "lock",
        "ha_service": "unlock",
    }
    fake_db.collection(ACTIONS).docs["a_media"] = dict(doc)

    action_poller._execute("a_media", doc, tmap)

    assert ha_calls == [("media_player", "media_pause", {"entity_id": "media_player.den_smart_tv_4k"})]
    assert fake_db.collection(ACTIONS).docs["a_media"]["status"] == "done"


def test_unlisted_action_refused_and_never_calls_ha(poller_env):
    fake_db, ha_calls, emitted, tmap = poller_env
    doc = {
        "sensitive": False,
        "action": {"action_type": "front_door_unlock", "entity": "lock.front"},
        "ha_domain": "lock",
        "ha_service": "unlock",
    }
    fake_db.collection(ACTIONS).docs["a4"] = dict(doc)

    action_poller._execute("a4", doc, tmap)

    assert ha_calls == []
    assert fake_db.collection(ACTIONS).docs["a4"]["status"] == "refused_by_house"
    assert "unlisted_action_type:front_door_unlock" in fake_db.collection(ACTIONS).docs["a4"]["result"]
    assert emitted[-1][0] == "action_refused_by_house"


def test_rehydrate_value_handles_nested_quotes_and_preserves_structure():
    tmap = scrub.TokenMap(
        version=1,
        salt="test-salt",
        entries=[scrub.MapEntry(token="[[P_KID1]]", kind="person", aliases=['O"Connor'])],
    )
    action = {
        "action_type": "notify_family_member",
        "message": "Call [[P_KID1]] now",
        "extra": ["[[P_KID1]]", {"nested": "[[P_KID1]]"}, 42],
    }
    out = action_poller._rehydrate_action(action, tmap)
    assert out["message"] == 'Call O"Connor now'
    assert out["extra"] == ['O"Connor', {"nested": 'O"Connor'}, 42]


def test_requeue_stale_claims_only_resets_expired(poller_env):
    fake_db, _ha_calls, emitted, _tmap = poller_env
    now = datetime.now(UTC)
    fake_db.collection(ACTIONS).docs["stale"] = {
        "status": "claimed",
        "claimed_at": now - timedelta(seconds=601),
        "claimed_by": "old-host",
    }
    fake_db.collection(ACTIONS).docs["fresh"] = {
        "status": "claimed",
        "claimed_at": now - timedelta(seconds=30),
        "claimed_by": "live-host",
    }

    action_poller._requeue_stale_claims()

    assert fake_db.collection(ACTIONS).docs["stale"]["status"] == "approved"
    assert fake_db.collection(ACTIONS).docs["stale"]["claimed_by"] == ""
    assert fake_db.collection(ACTIONS).docs["fresh"]["status"] == "claimed"
    assert emitted == [("action_requeued_stale_claim", {"action_id": "stale"})]
