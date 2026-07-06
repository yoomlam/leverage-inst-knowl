"""Credential-vault provisioning. Each user gets one Anthropic credential vault, created
lazily on first login and remembered via the user->vault mapping in the store.

The vault holds the per-source MCP credentials the user connects (deposited by the OAuth
connector). Here we only create/lookup the vault itself. The concrete Anthropic call is
behind the ``VaultClient`` protocol so tests can substitute a fake without network access.
"""

from typing import Protocol

from .db import Store
from .settings import Settings


class VaultClient(Protocol):
    def create_vault(self, display_name: str, metadata: dict) -> str:
        """Create a vault and return its id (e.g. ``vlt_01ABC...``)."""
        ...


class AnthropicVaultClient:
    """Real ``VaultClient`` backed by the Anthropic SDK's Managed Agents vault API."""

    def __init__(self, api_key: str):
        import anthropic  # imported lazily so test/stub paths need no SDK/network

        self._client = anthropic.Anthropic(api_key=api_key)

    def create_vault(self, display_name: str, metadata: dict) -> str:
        vault = self._client.beta.vaults.create(display_name=display_name, metadata=metadata)
        return vault.id


def build_vault_client(settings: Settings) -> VaultClient | None:
    """Real client outside local/test; ``None`` in stub mode (no vault calls made)."""
    if settings.is_stub:
        return None
    return AnthropicVaultClient(settings.anthropic_api_key)


def ensure_user_vault(store: Store, vault_client: VaultClient, user: dict) -> str:
    """Return the user's vault id, creating the vault on first use.

    Idempotent: once the mapping exists, no new vault is created on later logins. The
    vault is tagged with ``external_user_id`` so it can be traced back to the app user.
    """
    existing = store.get_user_vault(user["id"])
    if existing:
        return existing
    vault_id = vault_client.create_vault(
        display_name=user["email"],
        metadata={"external_user_id": str(user["id"])},
    )
    store.set_user_vault(user["id"], vault_id)
    return vault_id
