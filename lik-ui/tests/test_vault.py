"""Vault provisioning: created lazily on first login, reused thereafter, and deletable."""

from lik_ui.vault import delete_user_vault, ensure_user_vault


class FakeVaultClient:
    def __init__(self):
        self.calls = 0
        self.last_metadata = None
        self.deleted = []
        self.credentials: list[dict] = []

    def create_vault(self, display_name: str, metadata: dict) -> str:
        self.calls += 1
        self.last_metadata = metadata
        return f"vlt_{self.calls}"

    def list_credentials(self, vault_id: str) -> list[dict]:
        return self.credentials

    def delete_vault(self, vault_id: str) -> None:
        self.deleted.append(vault_id)


def test_ensure_user_vault_creates_then_reuses(store):
    vc = FakeVaultClient()
    user = store.upsert_user("v@navapbc.com")

    first = ensure_user_vault(store, vc, user)
    assert first == "vlt_1"
    assert vc.calls == 1

    again = ensure_user_vault(store, vc, user)
    assert again == "vlt_1"  # reused
    assert vc.calls == 1  # no new vault created
    assert store.get_user_vault(user["id"]) == "vlt_1"


def test_vault_tagged_with_external_user_id(store):
    vc = FakeVaultClient()
    user = store.upsert_user("m@navapbc.com")
    ensure_user_vault(store, vc, user)
    assert vc.last_metadata["external_user_id"] == str(user["id"])


def test_delete_user_vault_removes_vault_and_mapping(store):
    vc = FakeVaultClient()
    user = store.upsert_user("d@navapbc.com")
    vault_id = ensure_user_vault(store, vc, user)

    assert delete_user_vault(store, vc, user) is True
    assert vc.deleted == [vault_id]
    assert store.get_user_vault(user["id"]) is None

    # A subsequent ensure provisions a brand-new vault.
    fresh = ensure_user_vault(store, vc, user)
    assert fresh != vault_id


def test_delete_user_vault_noop_when_absent(store):
    vc = FakeVaultClient()
    user = store.upsert_user("n@navapbc.com")
    assert delete_user_vault(store, vc, user) is False
    assert vc.deleted == []
