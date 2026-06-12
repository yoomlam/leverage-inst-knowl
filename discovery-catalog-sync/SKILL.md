---
name: discovery-catalog-sync
description: Sync the Discovery Layer Catalog Confluence page by fetching all Confluence pages tagged with `project-index` and upserting a row for each one. Use whenever someone says "sync the catalog", "update the discovery catalog", "refresh the catalog from Confluence", or asks to add/update catalog entries from the Project Index Directory. The catalog is at Confluence page ID 3224961120 in personal space ~911381386.
---

# Discovery Layer Catalog Sync

Syncs the **Discovery Layer Catalog** Confluence page with all pages tagged `project-index`. The catalog lives at:
`https://navasage.atlassian.net/wiki/spaces/~911381386/pages/3224961120/Discovery+Layer+Catalog`

## What to do

### Step 1 — Fetch all project-index pages from Confluence

Call `searchConfluenceUsingCql` with:
- cloudId: `navasage.atlassian.net`
- cql: `label = "project-index" AND type = page`
- limit: 250

For each result, collect:
- `title` → **Name**
- `webUrl` → **URL**
- `space.name` → **Space**
- `summary` → **Description** (trim to 200 chars)
- `lastModified` → **Last Modified**
- `author.displayName` → **Author**

### Step 2 — Read the current catalog page

Use the `confluence-editor` skill to safely read and update the catalog page. Follow its workflow:

Call `getConfluencePage` with:
- cloudId: `navasage.atlassian.net`
- pageId: `3224961120`
- contentFormat: `storage`

Parse the response body to extract the existing table rows. Build an in-memory map keyed by **URL** (the `href` of each row's first link) so you can detect new vs. existing rows. Note the current version number — you'll need it for the update.

### Step 3 — Build the updated table

For each page from Confluence:
- If a row with the same URL already exists → update it with fresh values.
- If no row exists → append a new row.

Preserve any rows not returned by the Confluence query (manually added entries).

The table has columns: **Name** (as a hyperlink), **Space**, **Description**, **Last Modified**, **Author**.

Build the full updated table as HTML:
```html
<table><tbody>
<tr><th>Name</th><th>Space</th><th>Description</th><th>Last Modified</th><th>Author</th></tr>
<!-- one <tr> per project -->
</tbody></table>
```

### Step 4 — Write the updated page

Use the `confluence-editor` skill's `updateConfluencePage` workflow to push the changes in-place.

Call `updateConfluencePage` with:
- cloudId: `navasage.atlassian.net`
- pageId: `3224961120`
- contentFormat: `html`
- body: the full page content — intro paragraph + updated table
- version: current version number + 1
- title: `Discovery Layer Catalog`

The intro paragraph should always be:
```html
<p>Auto-synced from Confluence pages tagged <code>project-index</code>. Run the <strong>discovery-catalog-sync</strong> skill to refresh.</p>
```

### Step 5 — Summary

Respond with:
```
Synced N pages from Confluence into the Discovery Layer Catalog.
  • X new rows added
  • Y rows updated
  • Z rows unchanged

Catalog: https://navasage.atlassian.net/wiki/spaces/~911381386/pages/3224961120/Discovery+Layer+Catalog
```

## Notes

- The `label = "project-index"` CQL is the canonical source of truth — it matches exactly what the Project Index Directory renders via its Page Properties Report macro.
- Always use the `confluence-editor` skill's workflow for `updateConfluencePage` — never call it directly without fetching the current version first, as it replaces the entire page body.
- If the search returns 0 results, verify the user has permission to view project index spaces and that the label is spelled correctly.
- Trim Description to 200 characters to keep the table readable.
