"""Vault provisioning: created lazily on first login, reused thereafter."""

from lik_ui.vault import ensure_user_vault


class FakeVaultClient:
    def __init__(self):
        self.calls = 0
        self.last_metadata = None

    def create_vault(self, display_name: str, metadata: dict) -> str:
        self.calls += 1
        self.last_metadata = metadata
        return f"vlt_{self.calls}"


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
