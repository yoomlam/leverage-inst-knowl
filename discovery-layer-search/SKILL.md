---
name: discovery-layer-search
description: Answer questions about Nava's projects by searching only the curated Discovery Layer Catalog and the project pages it links to. Use whenever someone asks about past work, project capabilities, agencies Nava has worked with, technologies used, or anything that can be answered from vetted project information. Do NOT use this for HR/policy questions (use sage-bot) or general web research. Triggers on questions like "what has Nava done with X?", "find projects related to Y", "which projects involve Z agency", "what do we know about X technology at Nava", or any question that can be answered from project history.
---

# Discovery Layer Search

Answers questions using only the curated **Discovery Layer Catalog** and the vetted project pages it links to. Never searches all of Confluence — the catalog is the controlled entry point.

**Catalog:** `https://navasage.atlassian.net/wiki/spaces/~911381386/pages/3224961120/Discovery+Layer+Catalog`
**Catalog page ID:** `3224961120` (cloudId: `navasage.atlassian.net`)

---

## What to do

### Step 1 — Read the catalog

Call `getConfluencePage` with:
- cloudId: `navasage.atlassian.net`
- pageId: `3224961120`
- contentFormat: `html`

Parse the table rows. Each row has: **Name** (with link), **Space**, **Description**, **Last Modified**, **Author**.

Build an in-memory list of all entries with their URLs and descriptions.

### Step 2 — Identify relevant entries

Read the user's question and score each catalog entry for relevance using the Name, Space, and Description fields. Do not fetch any project pages yet.

Select the entries most likely to answer the question. Use judgment — for a narrow factual question, 1–3 entries may be enough; for a broad survey question, fetch up to 8–10. Do not fetch all 110.

If nothing in the catalog looks relevant, tell the user: "Nothing in the Discovery Layer Catalog appears to cover that topic. The catalog only includes vetted Nava project indexes."

### Step 3 — Fetch relevant project pages

For each selected entry, call `getConfluencePage` with:
- cloudId: `navasage.atlassian.net`
- pageId: (extract from the entry's URL — the numeric ID at the end, e.g. `/pages/3224961120/...` → `3224961120`; for space overview URLs like `/spaces/PITIR/overview`, use `searchConfluenceUsingCql` with `label = "project-index" AND space = "PITIR"` to find the homepage ID)
- contentFormat: `html`

Read the content. Follow any **internal links within that page** if they point to deeper content that seems directly relevant (e.g., a "1.2 Contract Details" subpage). Do not follow links that leave the project space.

### Step 4 — Answer from what you found

Synthesize an answer using only the content retrieved in Steps 1–3. Cite each source by name with its Confluence URL.

If the fetched pages don't contain enough information to answer the question fully, say so explicitly — do not supplement with general knowledge or information from outside the catalog.

### Step 5 — Offer to go deeper

After answering, offer: "Want me to look at additional project pages, or check a specific project in more detail?"

---

## Notes

- **Scope boundary:** Only follow links that originate from the catalog or from a project page already fetched. Do not issue `searchConfluenceUsingCql` with open queries — only use CQL to resolve a specific space homepage when a direct page ID isn't available.
- **Space overview URLs** (`/spaces/SPACEKEY/overview`) don't have a page ID in the URL. To get the homepage, call `searchConfluenceUsingCql` with `label = "project-index" AND space = "SPACEKEY"` and use the first result's ID. Never use `ancestor = null` — it's a reserved CQL keyword that causes a 400 error.
- **Citations:** For every source used, include: page title (linked), space, last modified date, and author — so the user can judge freshness and credibility. Format as: _[Page Title](URL) — Space · Last modified: YYYY-MM-DD · Author: Name_
- **No hallucination:** If a project page is sparse or missing, say so. Don't fill gaps from training data.
