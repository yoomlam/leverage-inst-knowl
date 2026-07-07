"""Account settings — user-facing management of their own data.

Currently one action: deleting the credential vault. Deleting the vault removes every
source credential the user has connected; a fresh, empty vault is provisioned the next
time an agent needs it.
"""

from .vault import VaultClient, delete_user_vault


def register_account_routes(app) -> None:
    from fastapi import Request
    from fastapi.responses import HTMLResponse, RedirectResponse

    from .app import templates
    from .app_auth import require_user

    @app.get("/settings", response_class=HTMLResponse)
    async def settings_page(request: Request, deleted: str = ""):
        user = require_user(request)
        vault_id = request.app.state.store.get_user_vault(user["id"])
        vault_client: VaultClient | None = request.app.state.vault_client
        credentials = []
        if vault_id and vault_client is not None:
            try:
                credentials = vault_client.list_credentials(vault_id)
            except Exception as exc:  # noqa: BLE001 - a listing failure shouldn't 500 the page
                return HTMLResponse(f"Could not load your credentials: {exc}", status_code=502)
        return templates.TemplateResponse(
            request,
            "settings.html",
            {"user": user, "vault_id": vault_id, "credentials": credentials, "deleted": bool(deleted)},
        )

    @app.post("/settings/vault/delete")
    async def delete_vault(request: Request):
        user = require_user(request)
        vault_client: VaultClient | None = request.app.state.vault_client
        try:
            delete_user_vault(request.app.state.store, vault_client, user)
        except Exception as exc:  # noqa: BLE001 - surface vault/SDK errors as a page, not a 500
            return HTMLResponse(f"Could not delete your vault: {exc}", status_code=502)
        return RedirectResponse("/settings?deleted=1", status_code=303)
