# Known Limitations

## Confluence MCP: Page Version Number Not Available

The Confluence MCP connector (`01fd8586-e417-4e54-ae66-45006d1e08b1`) does not expose a page **version number**. Neither `getConfluencePage` nor `searchConfluenceUsingCql` (with `expand=version`) returns a version field in the response body.

**What this rules out:** staleness checks that compare a stored version *number* against the live page's version number. That specific mechanism cannot work.

**What it does NOT rule out:** detecting whether a page's content has *changed* since DL last saw it. A version number is only one way to detect change — it is not the only one. Two content-state signals remain available:

- **Content hash (always available).** DL fetches the page body on each sync, so it can hash the body and compare hashes. Change detection = `stored hash ≠ current hash`. This needs zero MCP capability.
- **`lastModified` timestamp (conditional — unverified).** If the connector returns a `lastModified` / `version.when` field in the response body, it is a cheaper signal than hashing. **Unverified:** being a CQL-queryable field (`WHERE lastmodified > X`) does not guarantee it appears in the response object. Confirm with a live `getConfluencePage` call against this connector before relying on it.

**Design impact:** confirmations and `catalog.source_refs[]` anchor to an opaque content-state marker compared by equality, not to a version number. See [docs/brainstorms/2026-06-25-02-confirmation-content-state-marker-requirements.md](docs/brainstorms/2026-06-25-02-confirmation-content-state-marker-requirements.md). The marker is populated from `lastModified` when available, otherwise a content hash — so change detection is not blocked by the missing version number.
