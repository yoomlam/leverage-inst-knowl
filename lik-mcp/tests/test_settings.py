"""Transport selection settings (U1). These read only env vars, so no DB is needed."""

from lik_mcp.settings import Settings


def test_transport_defaults_to_stdio(monkeypatch):
    """No LIK_TRANSPORT set -> stdio, so `uv run python -m lik_mcp` and the test
    fixtures keep their spawned-per-session behavior."""
    monkeypatch.delenv("LIK_TRANSPORT", raising=False)
    assert Settings(_env_file=None).transport == "stdio"


def test_transport_reads_lik_transport_env(monkeypatch):
    """The container sets LIK_TRANSPORT=streamable-http to run the HTTP listener."""
    monkeypatch.setenv("LIK_TRANSPORT", "streamable-http")
    assert Settings(_env_file=None).transport == "streamable-http"


def test_transport_env_is_case_insensitive(monkeypatch):
    """LIK_-prefixed settings are case-insensitive (pydantic-settings default), so a
    lowercased var name still resolves."""
    monkeypatch.delenv("LIK_TRANSPORT", raising=False)
    monkeypatch.setenv("lik_transport", "streamable-http")
    assert Settings(_env_file=None).transport == "streamable-http"


def test_http_host_port_defaults(monkeypatch):
    """Default to loopback:8000 — the no-Docker default. The container overrides
    LIK_HTTP_HOST to 0.0.0.0 to be reachable through its published port."""
    monkeypatch.delenv("LIK_HTTP_HOST", raising=False)
    monkeypatch.delenv("LIK_HTTP_PORT", raising=False)
    settings = Settings(_env_file=None)
    assert settings.http_host == "127.0.0.1"
    assert settings.http_port == 8000


def test_http_host_port_read_from_env(monkeypatch):
    monkeypatch.setenv("LIK_HTTP_HOST", "0.0.0.0")
    monkeypatch.setenv("LIK_HTTP_PORT", "9999")
    settings = Settings(_env_file=None)
    assert settings.http_host == "0.0.0.0"
    assert settings.http_port == 9999
