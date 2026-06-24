# Known Limitations

## Confluence MCP: Page Version Not Available

The Confluence MCP connector (`01fd8586-e417-4e54-ae66-45006d1e08b1`) does not expose the current version number of a page. Neither `getConfluencePage` nor `searchConfluenceUsingCql` (with `expand=version`) returns a version field.

**Impact:** The `sync-catalog-from-project-indexes` skill registers Catalog entries with `source_refs[].version` hardcoded to `"1"`. This means staleness checks that compare the stored version against the live page version will not work correctly.

**Workaround:** None available through the current MCP tools. Requires the MCP server to be updated to expose version fields in its responses.
