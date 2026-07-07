"""Account settings: the Settings page and the vault-delete action."""

from fastapi.testclient import TestClient

from lik_ui.app import build_app
from lik_ui.db import Store
from lik_ui.settings import Settings
from tests.test_app_auth import FakeOidc, _start_login_and_get_state
from tests.test_vault import FakeVaultClient


def _client(db):
    oidc = FakeOidc({"email": "alice@navapbc.com", "email_verified": True})
    vc = FakeVaultClient()
    app = build_app(Settings(env="test"), store=Store(db), app_oidc=oidc, vault_client=vc)
    client = TestClient(app, follow_redirects=False)
    state = _start_login_and_get_state(client)
    client.get(f"/auth/callback?code=x&state={state}")  # logs in + provisions a vault
    return client, vc


def test_settings_requires_login(db):
    oidc = FakeOidc({})
    app = build_app(Settings(env="test"), store=Store(db), app_oidc=oidc, vault_client=FakeVaultClient())
    r = TestClient(app, follow_redirects=False).get("/settings")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_settings_page_renders(db):
    client, _ = _client(db)
    r = client.get("/settings")
    assert r.status_code == 200
    assert "Delete my vault" in r.text


def test_settings_page_lists_credentials(db):
    client, vc = _client(db)
    vc.credentials = [{"display_name": "lik-mcp", "url": "https://mcp.example/mcp"}]
    r = client.get("/settings")
    assert r.status_code == 200
    assert "lik-mcp" in r.text
    assert "https://mcp.example/mcp" in r.text


def test_delete_vault_deletes_and_forgets_mapping(db):
    client, vc = _client(db)
    user = Store(db).get_user_by_email("alice@navapbc.com")
    assert Store(db).get_user_vault(user["id"]) == "vlt_1"

    r = client.post("/settings/vault/delete")
    assert r.status_code == 303
    assert r.headers["location"] == "/settings?deleted=1"
    assert vc.deleted == ["vlt_1"]
    assert Store(db).get_user_vault(user["id"]) is None


def test_delete_vault_requires_login(db):
    oidc = FakeOidc({})
    app = build_app(Settings(env="test"), store=Store(db), app_oidc=oidc, vault_client=FakeVaultClient())
    r = TestClient(app, follow_redirects=False).post("/settings/vault/delete")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
