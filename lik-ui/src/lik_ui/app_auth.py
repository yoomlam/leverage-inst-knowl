"""App login via Google Workspace SSO — identity only.

This is deliberately separate from the per-source data connections (the OAuth connector).
Login requests only ``openid email`` and yields the user's verified email, which is the
app identity. It does NOT request data or offline scopes; the lik-mcp *data* connection is
a distinct flow with its own (reused) client id.

Endpoints (authorization-server endpoints are read from Google's OIDC discovery document,
never hardcoded):
  GET /login          landing page with a "Sign in with Google" action
  GET /auth/login     start the OIDC flow (store state+nonce, redirect to Google)
  GET /auth/callback  validate state, exchange code, verify email, upsert user + vault
  GET /logout         clear the session
  GET /               home; requires a logged-in user (placeholder until U6)

No tokens, codes, or cookies are logged.
"""

import secrets

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from .db import Store
from .settings import Settings
from .vault import VaultClient, ensure_user_vault


class NotAuthenticated(Exception):
    """Raised by ``require_user`` when there is no logged-in user; the app's handler
    turns this into a redirect to /login."""


def get_current_user(request: Request) -> dict | None:
    return request.session.get("user")


def require_user(request: Request) -> dict:
    user = get_current_user(request)
    if not user:
        raise NotAuthenticated()
    return user


class GoogleOidcClient:
    """Identity-only OIDC client for app login. Endpoints come from Google's discovery
    document; the access token is used once to read the verified email from userinfo."""

    def __init__(self, client_id: str, client_secret: str, discovery_url: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.discovery_url = discovery_url
        self.redirect_uri = redirect_uri
        self._metadata: dict | None = None

    async def metadata(self) -> dict:
        if self._metadata is None:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.discovery_url)
                resp.raise_for_status()
                self._metadata = resp.json()
        return self._metadata

    async def authorization_url(self, state: str, nonce: str) -> str:
        meta = await self.metadata()
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "scope": "openid email",
            "redirect_uri": self.redirect_uri,
            "state": state,
            "nonce": nonce,
            "access_type": "online",  # identity only; no refresh token needed
            "prompt": "select_account",
        }
        return str(httpx.URL(meta["authorization_endpoint"], params=params))

    async def exchange_code(self, code: str) -> dict:
        meta = await self.metadata()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                meta["token_endpoint"],
                data={
                    "code": code,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "redirect_uri": self.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            return resp.json()

    async def fetch_userinfo(self, access_token: str) -> dict:
        meta = await self.metadata()
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                meta["userinfo_endpoint"],
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            return resp.json()


def _email_verified(userinfo: dict) -> bool:
    v = userinfo.get("email_verified")
    return v is True or str(v).lower() == "true"


def register_auth_routes(app: FastAPI) -> None:
    from .app import templates  # local import avoids a circular import at module load

    @app.exception_handler(NotAuthenticated)
    async def _redirect_to_login(request: Request, exc: NotAuthenticated):
        return RedirectResponse("/login", status_code=303)

    @app.get("/login", response_class=HTMLResponse)
    async def login(request: Request):
        if get_current_user(request):
            return RedirectResponse("/", status_code=303)
        return templates.TemplateResponse(request, "login.html", {})

    @app.get("/auth/login")
    async def auth_login(request: Request):
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        request.session["oauth_login"] = {"state": state, "nonce": nonce}
        url = await request.app.state.app_oidc.authorization_url(state, nonce)
        return RedirectResponse(url, status_code=303)

    @app.get("/auth/callback")
    async def auth_callback(request: Request, code: str = "", state: str = ""):
        saved = request.session.get("oauth_login") or {}
        if not state or state != saved.get("state"):
            return HTMLResponse("Login state mismatch. Please try again.", status_code=400)

        oidc: GoogleOidcClient = request.app.state.app_oidc
        tokens = await oidc.exchange_code(code)
        userinfo = await oidc.fetch_userinfo(tokens["access_token"])
        if not _email_verified(userinfo) or not userinfo.get("email"):
            return HTMLResponse("Google account has no verified email.", status_code=403)

        store: Store = request.app.state.store
        vault_client: VaultClient = request.app.state.vault_client
        user = store.upsert_user(userinfo["email"])
        ensure_user_vault(store, vault_client, user)

        request.session.pop("oauth_login", None)
        request.session["user"] = {"id": user["id"], "email": user["email"]}
        return RedirectResponse("/", status_code=303)

    @app.get("/logout")
    async def logout(request: Request):
        request.session.clear()
        return RedirectResponse("/login", status_code=303)

    @app.get("/", response_class=HTMLResponse)
    async def home(request: Request):
        user = require_user(request)
        return templates.TemplateResponse(request, "home.html", {"user": user})
