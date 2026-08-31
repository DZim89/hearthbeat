"""Egress-guard configuration validation + outbound-surface coverage."""

import asyncio
from types import SimpleNamespace

import pytest

from app import ledger
from house import scrub

VALID_HASH = "a" * 64
VALID = {
    "EGRESS_SALT": "s1",
    "EGRESS_ALIAS_HASHES": VALID_HASH,
    "EGRESS_KNOWN_TOKENS": "[[P_DAD]],[[P_KID1]]",
}


def _env(base: dict | None = None, **kw) -> dict:
    e = dict(base or {})
    e.update(kw)
    return e


# ---- validate_egress_config matrix -----------------------------------------

def test_production_all_missing_fails():
    errs = ledger.validate_egress_config(_env(K_SERVICE="svc"))
    assert errs and "all three required" in errs[0]


@pytest.mark.parametrize("missing", ["EGRESS_SALT", "EGRESS_ALIAS_HASHES", "EGRESS_KNOWN_TOKENS"])
def test_production_each_missing_var_named(missing):
    env = _env(VALID, K_SERVICE="svc")
    env[missing] = ""
    errs = ledger.validate_egress_config(env)
    assert any(missing in e for e in errs)
    for e in errs:  # never leak values
        assert VALID_HASH not in e and "P_DAD" not in e


def test_malformed_hash_counted_not_printed():
    env = _env(VALID, K_SERVICE="svc", EGRESS_ALIAS_HASHES=f"{VALID_HASH},zz-not-hex,{'b' * 63}")
    errs = ledger.validate_egress_config(env)
    assert any("2 entries not 64-char hex" in e for e in errs)


def test_malformed_token_counted():
    env = _env(VALID, K_SERVICE="svc", EGRESS_KNOWN_TOKENS="[[P_DAD]],notatoken,[[lower]]")
    errs = ledger.validate_egress_config(env)
    assert any("EGRESS_KNOWN_TOKENS: 2" in e for e in errs)


def test_production_valid_passes():
    assert ledger.validate_egress_config(_env(VALID, K_SERVICE="svc")) == []


def test_csv_whitespace_stripped():
    env = _env(K_SERVICE="svc", EGRESS_SALT=" s ",
               EGRESS_ALIAS_HASHES=f" {VALID_HASH} , {'c' * 64} ",
               EGRESS_KNOWN_TOKENS=" [[P_DAD]] , [[P_MOM]] ")
    assert ledger.validate_egress_config(env) == []


def test_offline_fixture_replay_may_run_guardless():
    assert ledger.validate_egress_config(_env(SIMULATED_HOME="1")) == []


def test_fixture_judge_supplied_but_malformed_still_fails():
    env = _env(SIMULATED_HOME="1", EGRESS_ALIAS_HASHES="nothex")
    assert ledger.validate_egress_config(env) != []


def test_local_judge_live_requires_guard():
    errs = ledger.validate_egress_config(_env(SIMULATED_HOME="1", JUDGE_LLM="live"))
    assert errs  # real requests leave the machine — no silent guardless mode


def test_cloud_run_simulated_still_requires_guard():
    errs = ledger.validate_egress_config(_env(K_SERVICE="svc", SIMULATED_HOME="1"))
    assert errs  # K_SERVICE means real infra — SIMULATED_HOME grants no exemption


def test_bare_local_dev_requires_guard():
    errs = ledger.validate_egress_config(_env())
    assert errs  # bare local dev can reach real Vertex — guard config required


def test_plugin_constructor_fails_closed(monkeypatch):
    monkeypatch.setenv("K_SERVICE", "svc")
    for k in ("EGRESS_SALT", "EGRESS_ALIAS_HASHES", "EGRESS_KNOWN_TOKENS"):
        monkeypatch.delenv(k, raising=False)
    with pytest.raises(RuntimeError, match="egress guard config invalid"):
        ledger.LedgerPlugin("r1", "manual", sink=ledger.FileSink(path="data/test_ledger.jsonl"))


# ---- outbound payload surfaces ---------------------------------------------

def _part(**kw):
    base = {"text": None, "function_call": None, "function_response": None}
    base.update(kw)
    return SimpleNamespace(**base)


def test_request_text_covers_all_surfaces():
    req = SimpleNamespace(
        config=SimpleNamespace(
            system_instruction=SimpleNamespace(parts=[_part(text="SYS_PART")])
        ),
        contents=[
            SimpleNamespace(parts=[
                _part(text="PLAIN_TEXT"),
                _part(function_call=SimpleNamespace(args={"q": "CALL_ARG"})),
                _part(function_response=SimpleNamespace(response={"r": "TOOL_RESULT"})),
            ])
        ],
    )
    text = ledger._request_text(req)
    for needle in ("SYS_PART", "PLAIN_TEXT", "CALL_ARG", "TOOL_RESULT"):
        assert needle in text


def test_request_text_string_system_instruction():
    req = SimpleNamespace(config=SimpleNamespace(system_instruction="SYS_STR"), contents=[])
    assert "SYS_STR" in ledger._request_text(req)


def test_before_model_blocks_on_match(monkeypatch, tmp_path):
    salt = "s1"
    leak = "supersecretname"
    monkeypatch.setenv("EGRESS_SALT", salt)
    monkeypatch.setenv("EGRESS_ALIAS_HASHES", scrub._hash(salt, leak))
    monkeypatch.setenv("EGRESS_KNOWN_TOKENS", "[[P_DAD]]")
    monkeypatch.delenv("K_SERVICE", raising=False)
    plugin = ledger.LedgerPlugin("r1", "manual", sink=ledger.FileSink(path=str(tmp_path / "l.jsonl")))
    ctx = SimpleNamespace(agent_name="planner")
    req = SimpleNamespace(config=None, contents=[SimpleNamespace(parts=[
        _part(function_response=SimpleNamespace(response={"note": f"about {leak} today"}))
    ])])
    with pytest.raises(RuntimeError, match="EGRESS GUARD"):
        asyncio.get_event_loop().run_until_complete(
            plugin.before_model_callback(callback_context=ctx, llm_request=req)
        )
    # and the safe form passes:
    req2 = SimpleNamespace(config=None, contents=[SimpleNamespace(parts=[_part(text="[[P_DAD]] is home")])])
    asyncio.get_event_loop().run_until_complete(
        plugin.before_model_callback(callback_context=ctx, llm_request=req2)
    )
    assert plugin.egress_matches == 1 and plugin.egress_checks == 2
