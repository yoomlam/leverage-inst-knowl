"""Store round-trip tests. Require a reachable `_test` Postgres (see conftest `db`)."""


def test_upsert_user_is_idempotent(store):
    first = store.upsert_user("alice@navapbc.com")
    again = store.upsert_user("alice@navapbc.com")
    assert first["id"] == again["id"]
    assert store.get_user_by_email("alice@navapbc.com")["id"] == first["id"]


def test_user_vault_mapping_roundtrips_and_is_unique(store):
    user = store.upsert_user("bob@navapbc.com")
    assert store.get_user_vault(user["id"]) is None
    store.set_user_vault(user["id"], "vlt_1")
    assert store.get_user_vault(user["id"]) == "vlt_1"
    # One vault per user: a second set overwrites rather than duplicating.
    store.set_user_vault(user["id"], "vlt_2")
    assert store.get_user_vault(user["id"]) == "vlt_2"


def test_conversations_are_scoped_to_their_user(store):
    a = store.upsert_user("a@navapbc.com")
    b = store.upsert_user("b@navapbc.com")
    conv = store.create_conversation(a["id"], "agent_1", "sess_1", title="First")
    assert [c["id"] for c in store.list_conversations(a["id"])] == [conv["id"]]
    assert store.list_conversations(b["id"]) == []
    # b cannot open a's conversation
    assert store.get_conversation(conv["id"], b["id"]) is None
    assert store.get_conversation(conv["id"], a["id"])["session_id"] == "sess_1"


def test_dcr_registration_absent_then_stored_and_reused(store):
    assert store.get_dcr_registration("https://cf.mcp.atlassian.com") is None
    store.put_dcr_registration(
        "https://cf.mcp.atlassian.com", "client_abc", "secret_xyz", {"redirect_uris": ["https://x/cb"]}
    )
    got = store.get_dcr_registration("https://cf.mcp.atlassian.com")
    assert got["client_id"] == "client_abc"
    assert got["metadata"]["redirect_uris"] == ["https://x/cb"]
    # Re-registering the same issuer updates in place (no duplicate; issuer is the PK).
    store.put_dcr_registration("https://cf.mcp.atlassian.com", "client_def", "secret_new", {})
    assert store.get_dcr_registration("https://cf.mcp.atlassian.com")["client_id"] == "client_def"
