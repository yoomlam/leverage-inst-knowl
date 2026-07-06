"""make_server wiring (DB-free): the security-critical authenticator-selection branch and
HTTP host/port forwarding. Database and build_server are stubbed so no DB is touched."""

import pytest

import lik_mcp.__main__ as main_mod
from lik_mcp.auth import ContextAuthenticator, GoogleOIDCVerifier, StubAuthenticator
from lik_mcp.settings import Settings


def _capture(monkeypatch):
    """Stub out Database (no connection) and build_server (capture its args)."""
    captured = {}
    monkeypatch.setattr(main_mod, "Database", lambda conninfo: object())

    def fake_build_server(db, authenticator, resolver, host="127.0.0.1", port=8000, **kwargs):
        captured.update(authenticator=authenticator, host=host, port=port, **kwargs)
        return object()

    monkeypatch.setattr(main_mod, "build_server", fake_build_server)
    return captured


@pytest.mark.parametrize("env", ["local", "test"])
def test_make_server_uses_stub_authenticator_in_local_and_test(monkeypatch, env):
    captured = _capture(monkeypatch)
    main_mod.make_server(Settings(_env_file=None, env=env))
    assert isinstance(captured["authenticator"], StubAuthenticator)
    # No real token verification is wired in local/test.
    assert captured.get("token_verifier") is None
    assert captured.get("auth_settings") is None


@pytest.mark.parametrize("env", ["prod", "dev", "staging"])
def test_make_server_fails_closed_without_oauth_config(monkeypatch, env):
    """Anything other than local/test — including a cloud `dev` — must refuse to start
    without OAuth configured, rather than silently running open. This is the control that
    keeps an unauthenticated service out of a real deployment."""
    _capture(monkeypatch)
    with pytest.raises(RuntimeError, match="Refusing to start"):
        main_mod.make_server(Settings(_env_file=None, env=env))


@pytest.mark.parametrize("env", ["prod", "dev", "staging"])
def test_make_server_wires_real_auth_when_configured(monkeypatch, env):
    captured = _capture(monkeypatch)
    main_mod.make_server(
        Settings(
            _env_file=None,
            env=env,
            oauth_client_id="client-123.apps.googleusercontent.com",
            resource_server_url="https://lik.example.com/mcp",
        )
    )
    assert isinstance(captured["authenticator"], ContextAuthenticator)
    assert isinstance(captured["token_verifier"], GoogleOIDCVerifier)
    assert captured["token_verifier"].client_id == "client-123.apps.googleusercontent.com"
    assert captured["auth_settings"] is not None


def test_make_server_forwards_http_host_and_port(monkeypatch):
    captured = _capture(monkeypatch)
    main_mod.make_server(Settings(_env_file=None, http_host="0.0.0.0", http_port=9999))
    assert captured["host"] == "0.0.0.0"
    assert captured["port"] == 9999
