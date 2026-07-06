import logging

import pytest
from mcp.server.fastmcp.exceptions import ToolError

from lik_mcp.auth import ContextAuthenticator, StubAuthenticator
from lik_mcp.server import build_server


async def test_tool_call_logs_request_caller_and_result(db, resolver, caplog):
    """A tool call logs the request fields, the verified caller, and the outcome — the
    detail that 'Processing request of type CallToolRequest' alone doesn't give."""
    server = build_server(db, StubAuthenticator(email="alice@navapbc.com"), resolver)
    with caplog.at_level(logging.INFO, logger="lik_mcp.server"):
        await server.call_tool("lookup_catalog_entry", {"entry_type": "index", "subject": "Atlas"})

    messages = [r.getMessage() for r in caplog.records]
    assert any("tool=lookup_catalog_entry request" in m and "Atlas" in m for m in messages)
    assert any("authorized caller=alice@navapbc.com" in m for m in messages)
    assert any("tool=lookup_catalog_entry result count=" in m for m in messages)


async def test_authorization_denial_is_logged(db, resolver, caplog):
    """When no verified caller is on the request (bearer token missing/invalid), the
    ContextAuthenticator refuses and the refusal is logged at WARNING — so a denied call
    is visible in the logs instead of silently 500-ing. Here the tool is called directly
    with no request context, which is the same 'no verified caller' condition."""
    server = build_server(db, ContextAuthenticator(), resolver)
    with caplog.at_level(logging.INFO, logger="lik_mcp.server"):
        # FastMCP re-wraps the refusal as a ToolError; we only care that we logged it first.
        with pytest.raises(ToolError):
            await server.call_tool("list_catalog_entries", {"entry_type": "index"})

    denials = [r for r in caplog.records if "authorization denied" in r.getMessage()]
    assert denials, "expected an authorization-denied log line"
    assert denials[0].levelno == logging.WARNING
