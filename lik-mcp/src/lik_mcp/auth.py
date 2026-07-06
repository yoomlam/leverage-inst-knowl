"""Authentication: turning a request into a verified caller identity.

Two distinct concerns live here:

* **Token verification** (`GoogleOIDCVerifier`) validates the Bearer token on an HTTP
  request *before any tool runs*. It implements the MCP SDK's `TokenVerifier`, so the
  SDK's bearer middleware calls it and stores the result on the request context.
* **Identity resolution** (`Authenticator`) is what a tool calls to learn who it is
  acting as. In a real deployment that identity comes from the verified token on the
  context; local/test uses a fixed stub so tools have an identity without real tokens.

The auth token is a credential and is NEVER logged — only the email it resolves to.
"""

import logging
import time
from typing import Protocol

import httpx
from pydantic import BaseModel

from mcp.server.auth.middleware.auth_context import get_access_token
from mcp.server.auth.provider import AccessToken

logger = logging.getLogger("lik_mcp.auth")


class Identity(BaseModel):
    """A verified caller. `email` is the authorization claim; never self-asserted in prod."""

    email: str
    groups: list[str] = []


# --------------------------------------------------------------------------- #
# Token verification (HTTP transport, runs in the SDK's bearer middleware)
# --------------------------------------------------------------------------- #


class GoogleOIDCVerifier:
    """Validate a Google OAuth **access token** and expose the caller's verified email.

    The token is opaque (not a JWT), so it's validated by asking Google's tokeninfo
    endpoint. We require the token's audience (`aud`) to be our own OAuth client id — an
    audience check, so a token minted for some other app can't be replayed here — and a
    verified email, which becomes the authorization claim. Any failure returns `None`,
    which the SDK turns into a 401 (fail-closed). The raw token is never logged.

    A small TTL cache avoids a tokeninfo round-trip on every single tool call.
    """

    def __init__(
        self,
        client_id: str,
        tokeninfo_url: str = "https://www.googleapis.com/oauth2/v3/tokeninfo",
        cache_ttl: int = 300,
    ):
        if not client_id:
            raise ValueError("GoogleOIDCVerifier requires an OAuth client_id to validate 'aud' against.")
        self.client_id = client_id
        self.tokeninfo_url = tokeninfo_url
        self.cache_ttl = cache_ttl
        self._cache: dict[str, tuple[AccessToken, float]] = {}

    async def verify_token(self, token: str) -> AccessToken | None:
        cached = self._cache.get(token)
        if cached is not None:
            access, cache_until = cached
            if time.time() < cache_until:
                return access
            del self._cache[token]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(self.tokeninfo_url, params={"access_token": token})
        except httpx.HTTPError as exc:
            logger.warning("token verification failed: could not reach tokeninfo (%s)", exc)
            return None

        if resp.status_code != 200:
            # 400 is Google's answer for an invalid/expired token. Log the status, not the token.
            logger.warning("token verification failed: tokeninfo status=%s", resp.status_code)
            return None

        data = resp.json()
        access = self._to_access_token(token, data)
        if access is None:
            return None

        # Cache until the token expires, capped at cache_ttl so a revoked token can't linger.
        ttl = self.cache_ttl
        if access.expires_at is not None:
            ttl = min(ttl, max(0, access.expires_at - int(time.time())))
        if ttl > 0:
            self._cache[token] = (access, time.time() + ttl)
        return access

    def _to_access_token(self, token: str, data: dict) -> AccessToken | None:
        """Apply the authorization rules to a tokeninfo response. Returns None (deny) on
        any failed check; never logs the token."""
        aud = data.get("aud")
        if aud != self.client_id:
            logger.warning("token verification failed: aud mismatch (expected our client id)")
            return None

        email = data.get("email")
        verified = str(data.get("email_verified", "")).lower() == "true"
        if not email or not verified:
            logger.warning("token verification failed: missing or unverified email claim")
            return None

        expires_at = None
        if data.get("exp") is not None:
            try:
                expires_at = int(data["exp"])
            except (TypeError, ValueError):
                expires_at = None

        return AccessToken(
            token=token,
            client_id=self.client_id,  # == aud, already checked; typed str for the checker
            scopes=str(data.get("scope", "")).split(),
            expires_at=expires_at,
            subject=email,
            claims={"iss": data.get("iss"), "email": email},
        )


# --------------------------------------------------------------------------- #
# Identity resolution (what a tool calls to learn who it is acting as)
# --------------------------------------------------------------------------- #


class Authenticator(Protocol):
    def resolve(self) -> Identity: ...


class ContextAuthenticator:
    """Real-deployment identity: read the verified token the SDK's bearer middleware put
    on the request context and surface its email. Raises if no verified token is present
    (fail-closed) — with auth wired, that should only happen on a misroute or a direct
    call that bypassed the middleware."""

    def resolve(self) -> Identity:
        access = get_access_token()
        if access is None or not access.subject:
            raise PermissionError("No verified caller on the request (missing or invalid bearer token).")
        return Identity(email=access.subject)


class StubAuthenticator:
    """Local/test only. Returns a fixed identity so tools have a caller without real
    tokens — the streamable-http local container is loopback-only and stdio has no
    Authorization header. Must never be selected outside local/test."""

    def __init__(self, email: str = "service@navapbc.com", groups: list[str] | None = None):
        self.email = email
        self.groups = groups or []

    def resolve(self) -> Identity:
        return Identity(email=self.email, groups=list(self.groups))
