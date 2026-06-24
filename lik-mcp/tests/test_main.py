"""make_server wiring (DB-free): the security-critical verifier-selection branch and
HTTP host/port forwarding. Database and build_server are stubbed so no DB is touched."""

import pytest

import lik_mcp.__main__ as main_mod
from lik_mcp.auth import FailClosedVerifier, StubVerifier
from lik_mcp.settings import Settings


def _capture(monkeypatch):
    """Stub out Database (no connection) and build_server (capture its args)."""
    captured = {}
    monkeypatch.setattr(main_mod, "Database", lambda conninfo: object())

    def fake_build_server(db, verifier, resolver, host="127.0.0.1", port=8000):
        captured.update(verifier=verifier, host=host, port=port)
        return object()

    monkeypatch.setattr(main_mod, "build_server", fake_build_server)
    return captured


@pytest.mark.parametrize("env", ["local", "test"])
def test_make_server_uses_stub_verifier_in_local_and_test(monkeypatch, env):
    captured = _capture(monkeypatch)
    main_mod.make_server(Settings(_env_file=None, env=env))
    assert isinstance(captured["verifier"], StubVerifier)


@pytest.mark.parametrize("env", ["prod", "dev", "staging"])
def test_make_server_fails_closed_outside_local_and_test(monkeypatch, env):
    """Anything other than local/test — including a cloud `dev` — must fail closed.
    This is the control that keeps the stub out of a real deployment."""
    captured = _capture(monkeypatch)
    main_mod.make_server(Settings(_env_file=None, env=env))
    assert isinstance(captured["verifier"], FailClosedVerifier)


def test_make_server_forwards_http_host_and_port(monkeypatch):
    captured = _capture(monkeypatch)
    main_mod.make_server(Settings(_env_file=None, http_host="0.0.0.0", http_port=9999))
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9999
