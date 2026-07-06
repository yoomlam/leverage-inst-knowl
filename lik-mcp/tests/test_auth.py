"""GoogleOIDCVerifier: the token-validation rules that stand between a Bearer token and a
verified caller email. Google's tokeninfo endpoint is mocked so no network is touched."""

import httpx
import pytest

from lik_mcp.auth import GoogleOIDCVerifier

CLIENT_ID = "client-123.apps.googleusercontent.com"
TOKENINFO = "https://tokeninfo.test/v3"


def _mock_tokeninfo(monkeypatch, handler):
    """Route the verifier's httpx calls through a MockTransport running `handler`."""
    transport = httpx.MockTransport(handler)
    real_client = httpx.AsyncClient

    def factory(*args, **kwargs):
        return real_client(transport=transport)

    monkeypatch.setattr("lik_mcp.auth.httpx.AsyncClient", factory)


def _ok_payload(**overrides):
    payload = {
        "aud": CLIENT_ID,
        "email": "alice@navapbc.com",
        "email_verified": "true",
        "scope": "openid email",
        "exp": "9999999999",
        "iss": "https://accounts.google.com",
    }
    payload.update(overrides)
    return payload


async def test_valid_token_resolves_to_email(monkeypatch):
    _mock_tokeninfo(monkeypatch, lambda req: httpx.Response(200, json=_ok_payload()))
    verifier = GoogleOIDCVerifier(client_id=CLIENT_ID, tokeninfo_url=TOKENINFO)

    access = await verifier.verify_token("good-token")

    assert access is not None
    assert access.subject == "alice@navapbc.com"
    assert access.client_id == CLIENT_ID
    assert "email" in access.scopes


async def test_audience_mismatch_is_denied(monkeypatch):
    """A token minted for another OAuth client must not be accepted here."""
    _mock_tokeninfo(monkeypatch, lambda req: httpx.Response(200, json=_ok_payload(aud="someone-else")))
    verifier = GoogleOIDCVerifier(client_id=CLIENT_ID, tokeninfo_url=TOKENINFO)

    assert await verifier.verify_token("wrong-aud") is None


async def test_unverified_email_is_denied(monkeypatch):
    _mock_tokeninfo(monkeypatch, lambda req: httpx.Response(200, json=_ok_payload(email_verified="false")))
    verifier = GoogleOIDCVerifier(client_id=CLIENT_ID, tokeninfo_url=TOKENINFO)

    assert await verifier.verify_token("unverified") is None


async def test_missing_email_is_denied(monkeypatch):
    payload = _ok_payload()
    del payload["email"]
    _mock_tokeninfo(monkeypatch, lambda req: httpx.Response(200, json=payload))
    verifier = GoogleOIDCVerifier(client_id=CLIENT_ID, tokeninfo_url=TOKENINFO)

    assert await verifier.verify_token("no-email") is None


async def test_invalid_token_status_is_denied(monkeypatch):
    """Google answers 400 for an invalid/expired token; that must be a clean deny (None),
    not an exception."""
    _mock_tokeninfo(monkeypatch, lambda req: httpx.Response(400, json={"error": "invalid_token"}))
    verifier = GoogleOIDCVerifier(client_id=CLIENT_ID, tokeninfo_url=TOKENINFO)

    assert await verifier.verify_token("expired") is None


async def test_result_is_cached(monkeypatch):
    """A repeated token is served from cache, not re-validated over the network."""
    calls = {"n": 0}

    def handler(req):
        calls["n"] += 1
        return httpx.Response(200, json=_ok_payload())

    _mock_tokeninfo(monkeypatch, handler)
    verifier = GoogleOIDCVerifier(client_id=CLIENT_ID, tokeninfo_url=TOKENINFO)

    await verifier.verify_token("repeat")
    await verifier.verify_token("repeat")

    assert calls["n"] == 1


def test_verifier_requires_client_id():
    with pytest.raises(ValueError):
        GoogleOIDCVerifier(client_id="")
