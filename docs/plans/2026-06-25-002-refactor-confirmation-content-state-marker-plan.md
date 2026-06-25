---
title: "refactor: Replace version with content-state marker in confirmations"
type: refactor
status: active
date: 2026-06-25
origin: docs/brainstorms/2026-06-25-02-confirmation-content-state-marker-requirements.md
---

# refactor: Replace version with content-state marker in confirmations

## Summary

Rename `confirmations.version` → `source_state` and change it from an identity field to a non-key state column, enabling "edited since" detection for in-place-edited sources without version-number dependency. Remove `fetched_at` and `version` from `SourceRef`. Extend `read_confirmations` to accept a caller-supplied live token and return an `edited_since` flag. Docs land first as a review gate; code changes follow.

---

## Problem Frame

See origin document. Short form: `confirmations.version` sits in the unique constraint, so every content change creates a new confirmation slot instead of updating it — "edited since" is undetectable, and `fetched_at` is a broken proxy that false-positives on every daily sync. (see origin: docs/brainstorms/2026-06-25-02-confirmation-content-state-marker-requirements.md)

---

## Requirements

- R1. Confirmation records which content state was vouched for (`source_state` non-key column, updated on re-confirm)
- R2. "Edited since" detection: stored `source_state` ≠ `current_source_state` → `edited_since: true`
- R3. No version-number dependency — token is opaque text, compared by equality only
- R4. Store-agnostic: same schema and comparison logic for all `store_kind` values; only token derivation varies per store in the calling skill
- R5. `fetched_at` removed from `source_refs`; recency uses `catalog.updated_at`
- R6. Architecture and strategy docs describe the marker model, not version/etag framing

---

## Scope Boundaries

- No content hash computation in the MCP server — token derivation is a skill-side responsibility
- No per-store fetch logic in `read_confirmations` — caller supplies the live token
- No changes to `last_validated_at` pipeline or owner-agnostic reconciliation
- No version history or ordered version tracking
- `CitationResolver` reachability deferred (unchanged)

### Deferred to Follow-Up Work

- Per-connector verification of native token fields for gdoc/gsheet/postgres/bigquery: each store needs the same probe Confluence received before leaving the hash fallback. Tracked in the origin requirements doc Decision 1 table.

---

## Context & Research

### Relevant Code and Patterns

- `lik-mcp/db/init.sql` lines 48–58: `confirmations` DDL with current `version` column and unique constraint
- `lik-mcp/db/init.sql` line 63+: existing idempotent `ALTER TABLE` migration pattern to follow
- `lik-mcp/src/lik_mcp/confirmations.py`: `ConfirmationRow` (line 14), `confirm_source` (line 45, INSERT-DO-NOTHING), `read_confirmations` (line 59); inline SQL constants
- `lik-mcp/src/lik_mcp/catalog.py` lines 10–18: `SourceRef` Pydantic model — current shape `{ id: str, version: Optional[str], fetched_at: Optional[str] }`
- `lik-mcp/src/lik_mcp/citations.py`: `Citation` model with `version` field and `_normalize_version` validator
- `lik-mcp/src/lik_mcp/server.py` lines 123, 136: `confirm_source` and `read_confirmations` MCP tool wrappers
- `lik-mcp/tests/test_confirmations.py`: integration tests against real Postgres; dedup tests currently assert `"duplicate"` return value
- `lik-mcp/tests/test_catalog.py`: `SourceRef` tests including `fetched_at`

---

## Key Technical Decisions

- **`Citation.version` → `Citation.source_state` (clean rename):** Keeps MCP input field name consistent with DB column. No in-repo callers to break. Mapping `version` → `source_state` internally would create a permanent naming inconsistency across the MCP API surface.
- **"Edited since" computed server-side in `read_confirmations` with caller-supplied token:** `read_confirmations` adds optional `current_source_state: str` param; returns `edited_since: Optional[bool]` per row. The Query skill fetches the live token and passes it in — server never calls external APIs.
- **`edited_since: None` means unknown, not clean:** When `current_source_state` is not supplied, `edited_since` is `None`. Callers must treat `None` as "unknown," not as "not edited."
- **Schema applied by DB reset, no migration script:** Project is in drafting mode with no production deployment, so `db/init.sql` is edited directly and the change is applied via `docker compose down -v && docker compose up -d` (see CLAUDE.md).
- **`SourceRef` forbids extra fields (`extra='forbid'`):** A caller still sending the removed `version` / `fetched_at` fails loudly at the contract boundary instead of having them silently dropped — converts the System-Wide Impact "break silently" risk into a visible `ValidationError`.

---

## Open Questions

### Resolved During Planning

- **Live token fetch location:** Caller supplies `current_source_state` to `read_confirmations`; server compares. No server-side external calls.
- **Content hash canonicalization:** Skill-side decision, deferred to skill authors. Server treats token as opaque.
- **`Citation.version` rename:** Clean rename to `Citation.source_state` (see Key Technical Decisions).

### Deferred to Implementation

- Whether `ConfirmationRow` gets a new `edited_since` field or whether `read_confirmations` returns a wrapper type — depends on whether the Pydantic model shape is used elsewhere.

---

## Implementation Units

- U1. **Update v0.4 architecture and strategy docs**

**Goal:** Replace version/etag-specific language with the generalized content-state marker model across three docs. Review gate before code changes.

**Requirements:** R6

**Dependencies:** None

**Files:**
- Modify: `v0.4/05-architecture.md`
- Modify: `v0.4/04-strategy.md`
- Modify: `v0.4/07-storage.md`

**Approach:**
- `v0.4/05-architecture.md`:
  - §2 "Version drift" bullet (`computed from v5 but source is now v7; comparing the version/etag in source_refs`) → restate as content-state marker comparison; drop version-number framing.
  - §2 "Confirmed, but edited since" bullet → stored marker vs live marker comparison.
  - §3 `source_refs` row description (`IDs/URLs + version/etag`) → entry carries a content-state token (native or hash); remove `fetched_at`.
  - §3 Detection paragraph (`comparing the stored version/etag against the live source`) → marker equality.
- `v0.4/04-strategy.md`:
  - §1.3 citation shape (`store_kind + location + locator + version`) → note `version` slot is the opaque content-state token (may be a hash or native id, not necessarily a version number).
  - Level 3 wording (`each signal records the version of the confirmed data`) → "records the content-state marker of the confirmed data."
- `v0.4/07-storage.md`: locate any version-specific confirmations-store wording; update to marker model.
- Preserve exact "version number unavailable" phrasing where it refers to the Confluence MCP connector limitation — only generalize the change-detection mechanism.

**Test scenarios:**
Test expectation: none — doc-only unit, no behavioral code change.

**Verification:**
- No remaining "version/etag" language in change-detection context across these three files
- `source_refs` description no longer mentions `fetched_at`
- "Version number unavailable" (MCP connector limitation) still present where accurate

---

- U2. **DB schema migration**

**Goal:** Rename `version` → `source_state` in `confirmations`; update unique constraint to `(confirmed_by, store_kind, location, locator)`.

**Requirements:** R1, R3

**Dependencies:** U1

**Files:**
- Modify: `lik-mcp/db/init.sql`

**Approach:**
- Edit the `CREATE TABLE IF NOT EXISTS confirmations` DDL directly: rename `version` → `source_state`; update the unique constraint to 4 fields `(confirmed_by, store_kind, location, locator)`.
- No migration script needed — project is in drafting mode with no production deployment. Schema changes are applied by resetting the DB: `docker compose down -v && docker compose up -d`.
- No DDL change needed for `source_refs.fetched_at` — it is a JSONB column; enforcement is at the Pydantic model layer (U3).

**Test scenarios:**
- Happy path: fresh `db/init.sql` run creates `confirmations` with `source_state` column and 4-field unique constraint
- Edge case: confirming same source twice as same user → one row (not two), `source_state` reflects latest value

**Verification:**
- `\d confirmations` shows `source_state` column; no `version` column; unique constraint covers exactly `(confirmed_by, store_kind, location, locator)`

---

- U3. **Update `SourceRef` model**

**Goal:** Remove `fetched_at` and `version` from `SourceRef`; add `source_state: Optional[str]`.

**Requirements:** R5, R4

**Dependencies:** U2

**Files:**
- Modify: `lik-mcp/src/lik_mcp/catalog.py`
- Modify: `lik-mcp/tests/test_catalog.py`

**Approach:**
- In `SourceRef` Pydantic model: remove `fetched_at` field; remove `version` field; add `source_state: Optional[str] = None`.
- Update any tests that construct `SourceRef` with `fetched_at` or `version`.

**Patterns to follow:**
- Existing Pydantic model style in `catalog.py` (optional fields with `None` default)

**Test scenarios:**
- Happy path: `SourceRef(id="x", source_state="abc123")` round-trips without `fetched_at` or `version` keys
- Edge case: `SourceRef(id="x")` (no `source_state`) is valid; `source_state` is `None`
- Error path: constructing `SourceRef` with `fetched_at=...` raises Pydantic validation error (field removed)

**Verification:**
- `SourceRef` has no `fetched_at` field and no `version` field; `source_state` is optional text
- All `test_catalog.py` tests pass

---

- U4. **Refactor `confirm_source`: rename field, upsert semantics**

**Goal:** Rename `Citation.version` → `Citation.source_state`; change `confirm_source` from INSERT-DO-NOTHING to upsert (one row per user per source, `source_state` updated on re-confirm).

**Requirements:** R1, R2, R3, R4

**Dependencies:** U2

**Files:**
- Modify: `lik-mcp/src/lik_mcp/citations.py`
- Modify: `lik-mcp/src/lik_mcp/confirmations.py`
- Modify: `lik-mcp/src/lik_mcp/server.py`
- Test: `lik-mcp/tests/test_confirmations.py`

**Approach:**
- `citations.py`: rename `Citation.version` → `Citation.source_state`; rename `_normalize_version` validator to `_normalize_source_state`. Keep normalization logic unchanged.
- `confirmations.py`:
  - Rename `ConfirmationRow.version` → `ConfirmationRow.source_state`.
  - Change `_INSERT` SQL to `INSERT … ON CONFLICT (confirmed_by, store_kind, location, locator) DO UPDATE SET source_state = EXCLUDED.source_state, created_at = now()`.
  - Return value: always return `"recorded"` — upsert always succeeds, no "duplicate" case.
- `server.py`: update field name references in the `confirm_source` tool wrapper.

**Patterns to follow:**
- Postgres `ON CONFLICT … DO UPDATE` upsert pattern
- Existing inline SQL constant style in `confirmations.py`

**Test scenarios:**
- Happy path: `confirm_source` with new source inserts row, returns `"recorded"`, `source_state` stored correctly
- Happy path: `confirm_source` called twice for same `(confirmed_by, store, location, locator)` with different `source_state` → one row, `source_state` updated to second value, returns `"recorded"` both times
- Happy path: `confirm_source` with `source_state=None` or empty string → stores null/empty, no error, returns `"recorded"`
- Edge case: two different users confirm same source → two rows, each with their own `source_state`
- Integration: confirm → re-confirm with new token → `source_state` column reflects new token

**Verification:**
- No `version` field in `Citation`, `ConfirmationRow`, or `_INSERT` SQL
- Double-confirm returns `"recorded"` and updates `source_state`
- All `test_confirmations.py` tests pass

---

- U5. **Extend `read_confirmations`: "edited since" flag**

**Goal:** Add optional `current_source_state` param to `read_confirmations`; return `edited_since: Optional[bool]` per confirmation row.

**Requirements:** R2, R4

**Dependencies:** U4

**Files:**
- Modify: `lik-mcp/src/lik_mcp/confirmations.py`
- Modify: `lik-mcp/src/lik_mcp/server.py`
- Test: `lik-mcp/tests/test_confirmations.py`

**Approach:**
- Add `edited_since: Optional[bool] = None` to `ConfirmationRow` (or a dedicated return wrapper if the model is used elsewhere in a way that conflicts).
- `read_confirmations` signature: add `current_source_state: Optional[str] = None`.
- After the DB query, if `current_source_state` is provided, set `row.edited_since = (row.source_state != current_source_state)` for each row. If not provided, leave `edited_since = None`.
- `server.py` MCP tool: expose `current_source_state` as optional parameter; pass through to function.

**Patterns to follow:**
- Existing `read_confirmations` return shape in `confirmations.py`

**Test scenarios:**
- Happy path: `read_confirmations` with `current_source_state` matching stored `source_state` → `edited_since: false`
- Happy path: `read_confirmations` with `current_source_state` differing from stored `source_state` → `edited_since: true`
- Edge case: `read_confirmations` without `current_source_state` → `edited_since: null` for all rows
- Edge case: `read_confirmations` for source with no confirmations → empty list, no error
- Edge case: stored `source_state` is `None` and `current_source_state` is provided → `edited_since: true` (they differ)
- Integration: confirm source (stores token A) → `read_confirmations(current_source_state="A")` → `edited_since: false`; call again with `current_source_state="B"` → `edited_since: true`

**Verification:**
- `read_confirmations` returns `edited_since: bool` when `current_source_state` supplied; `null` when not
- All `test_confirmations.py` tests pass

---

## System-Wide Impact

- **External contract change — `Citation.source_state`:** All callers of `confirm_source` (sync/DL-creation skills outside this repo) must rename `version` → `source_state` in their `Citation` payloads. Document in U1.
- **External contract change — `SourceRef`:** Skills that write `source_refs` entries must stop sending `fetched_at`/`version` and start sending `source_state`. Document in U1.
- **`edited_since: None` semantics:** Callers must treat `None` as "unknown," not "not edited." Query skills consuming `read_confirmations` need this documented.
- **Unchanged invariants:** `catalog.updated_at` remains the recency signal for reconciliation. `last_validated_at` pipeline untouched. `CitationResolver` untouched. Dedup key narrows to 4 fields — no existing data model consumers depend on the old 5-field key.
- **Integration coverage:** Upsert correctness (token update on re-confirm) and `edited_since` accuracy require integration tests against real Postgres — unit tests with mocks will not prove these.

---

## Risks & Dependencies

| Risk | Mitigation |
|---|---|
| External sync skills pass `version` / `fetched_at` in `SourceRef` — break silently after model change | External contract change; document in U1 docs and in limitations.md if appropriate |
| `edited_since: None` (no token supplied) misread by callers as "not edited" | Document clearly in `read_confirmations` docstring and in v0.4 docs |
| `ON CONFLICT` target must exactly match new constraint — any drift between DDL and SQL causes runtime error | Migration and `_INSERT` SQL are updated in the same unit (U2 and U4); verify together in tests |

---

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-25-02-confirmation-content-state-marker-requirements.md](docs/brainstorms/2026-06-25-02-confirmation-content-state-marker-requirements.md)
- Superseded plan: [docs/plans/2026-06-24-04-refactor-decouple-version-fields-from-mcp-plan.md](docs/plans/2026-06-24-04-refactor-decouple-version-fields-from-mcp-plan.md)
- Related code: `lik-mcp/src/lik_mcp/confirmations.py`, `lik-mcp/src/lik_mcp/catalog.py`, `lik-mcp/src/lik_mcp/citations.py`, `lik-mcp/db/init.sql`
