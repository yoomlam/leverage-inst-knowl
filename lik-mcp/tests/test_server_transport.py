"""build_server's HTTP wiring (DB-free): host/port forwarding and the loopback
DNS-rebinding guard. build_server only uses `db` inside tool closures, so None is fine
for constructing the server."""

from lik_mcp.auth import StubVerifier
from lik_mcp.citations import ShapeResolver
from lik_mcp.server import build_server


def test_build_server_forwards_host_and_port():
    mcp = build_server(None, StubVerifier(), ShapeResolver(), host="0.0.0.0", port=9999)
    assert mcp.settings.host == "0.0.0.0"
    assert mcp.settings.port == 9999


def test_build_server_enables_loopback_dns_rebinding_guard():
    """The container binds 0.0.0.0, so the Host-header allowlist is the guard. Confirm it
    is on and scoped to loopback (a real deploy must widen it)."""
    mcp = build_server(None, StubVerifier(), ShapeResolver())
    ts = mcp.settings.transport_security
    assert ts.enable_dns_rebinding_protection is True
    assert "127.0.0.1:*" in ts.allowed_hosts
    assert "localhost:*" in ts.allowed_hosts
