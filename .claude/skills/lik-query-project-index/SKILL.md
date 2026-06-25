---
name: lik-query-project-index
description: Answer questions about Nava's projects using the Discovery Layer Catalog in Postgres (the lik-mcp service) and the project-index pages it points to. Use whenever someone asks about past work, project capabilities, agencies Nava has worked with, technologies used, or anything answerable from vetted project-index pages. Triggers on questions like "what has Nava done with X?", "find projects related to Y", "which projects involve Z agency", "tell me about the <name> project". Do NOT use for HR/policy questions or general web research.
---

# Query Project Index

Answers a project question from the **Catalog** (the lik-mcp service over Postgres), following
its pointers to the project-index pages in Confluence. It escalates through three levels and
**asks the user before widening scope** at each step, so the Catalog stays the primary path and
a broad Confluence search is only a last resort.

It also surfaces and accumulates **confirmation signals**: it shows how vouched-for each cited
source is (`read_confirmations`) and offers to record the user's confirmation (`confirm_source`).

## Prerequisites

- The **lik-mcp** MCP service is connected (pointed at `likdb_local` for manual testing) and the
  Catalog has been populated by the `lik-sync-catalog-from-project-indexes` skill.
- The Atlassian (Confluence) MCP tools are available (for reading pages and the Level 3 fallback).

Use the text the user passes to this skill as their question.

## Errors

If any tool call fails or a required tool is unavailable, **stop immediately**. Do not fall
through to the next level. Present:
1. The error or missing tool name
2. Likely root causes (e.g. server not running, tool not yet deployed, MCP session stale)
3. Remedies (e.g. restart the server, reconnect MCP, redeploy)

## Level 1 — exact Catalog lookup, then fuzzy lookup

If the question names a specific project, derive `subject = "project: <name>"` and call
`lookup_catalog_entry` with `entry_type = "index"` and that `subject`.

- **Hit:** follow the row — `getConfluencePage` at its `locator` (page ID) or `location` (URL) —
  read the page, and answer from it. Go to **Rank & present**.
- **Miss**, or the question doesn't name a single project exactly: call
  `search_catalog_entries` with `entry_type = "index"` and the question's key terms as
  `query`. This catches partial names, typos, and reordered words.
  - **Candidate hit(s):** follow the top candidate's pointer (`getConfluencePage` at its
    `locator`/`location`), read the page, and answer. Go to **Rank & present**.
  - **No candidates:** go to **Level 2 (ask first)**.

`search_catalog_entries` is a **targeted, bounded keyed lookup** — top-N ranked candidates,
not a full read — so it runs **without** the "ask before widening" prompt that Levels 2 and 3
require. It stays part of the primary Catalog path.

## Level 2 — list and scan (ask the user first)

On a Level 1 miss, **pause and ask the user** (let them pick a single letter):

> No exact Catalog match. How should I widen the search?
> **(a)** List all project-index entries from the Catalog and scan them, or
> **(b)** Skip to a Confluence search over project-index pages.

If **(a)**: call `list_catalog_entries` with `entry_type = "index"`. Scan the returned rows
(match the question's terms against each `subject` and `category`), pick the most relevant ones,
`getConfluencePage` their pointers, and answer. Then go to **Rank & present**.

If the scan finds nothing relevant, ask again before Level 3. If **(b)**: go to **Level 3**.

## Level 3 — Confluence fallback (ask the user first)

Only with the user's go-ahead, call `searchConfluenceUsingCql` with:
- cloudId: `navasage.atlassian.net`
- cql: `label = "project-index" AND text ~ "<key terms>"`

Read the top matches and answer, noting that this answer came from a **bounded Confluence search**,
not the Catalog. Then go to **Rank & present**.

A Catalog miss or a broken pointer is never an error — it's a cache miss that degrades to the next
level.

## Rank & present (every level)

For each page you're about to cite, build a citation:
- `store_kind`: `"confluence"`
- `location`: the page URL
- `locator`: the page ID
- `source_state`: the live page's content-state marker — the **SHA-256 hex digest of its
  markdown body** (from the `getConfluencePage` you already ran to read the page). Compute it
  exactly as the marker recipe below specifies.

**Content-state marker recipe (shared with `lik-sync-catalog-from-project-indexes`).** Take the
`body` field **verbatim** from `getConfluencePage(pageId, contentFormat: "markdown")`, write it
to a file (no added trailing newline, no normalization), and hash it: `shasum -a 256 FILE | cut
-d' ' -f1` (or `sha256sum FILE | cut -d' ' -f1`). The sync skill stores `source_state` this
identical way, so a live marker matches the stored one whenever content is unchanged. The
Confluence connector exposes no stable native signal (no version number; `lastModified` is only
a relative string like `"about 5 hours ago"`), so a body hash is the only reliable marker — see
[../../../limitations.md](../../../limitations.md).

**Response integrity guard (required).** The Confluence MCP connector can return the **wrong
page** when `getConfluencePage` / `searchConfluenceUsingCql` calls run concurrently — a response
silently carries another in-flight request's body, with no error (see
[../../../limitations.md](../../../limitations.md)). Hashing a mismatched body yields a
`source_state` for the wrong page, so confirmations and `edited_since` checks compare against the
wrong content. Before you hash or cite any page, assert the returned object's `id` equals the
`pageId` you requested (and that each CQL result belongs to the query you sent); on mismatch,
re-issue that single call serially until the `id` matches. Parallel fetches are fine as long as
each response passes this check first.

Call `read_confirmations` with that citation **and** `current_source_state` set to the same live
body hash. It returns one row per user who voted on the source, each carrying:
- `confirmed_by`,
- `vote` — `up` (the source was right) or `down` (wrong),
- `reason` — for a down vote, `bad-retrieval` (poor/irrelevant result) or `wrong-content`
  (factually wrong); `null` for an up vote,
- `comment` — an optional free-text note (present mainly on `wrong-content` downs), and
- `edited_since` — `true` if that user voted on content that has since changed (their stored
  marker ≠ the live marker), `false` if their vote still matches the live content, `null` if
  unknown.

The signal is **signed**: up votes boost, down votes **soft-demote** — never hide. Rank a source
lower when down votes outweigh up, but still return it. Weigh `edited_since = false` votes more
heavily than `edited_since = true` ones (a vote on since-changed content — including a
wrong-content flag whose source was since corrected — applies only weakly). Annotate every cited
source:
- positives, e.g. *"(3 confirmations, 1 on a since-edited version)"*;
- when a source carries down votes, **explain the demotion** — show the reason kind and, when a
  `comment` is present, the note, e.g. *"(demoted — flagged by 2: wrong content — 'states the
  2019 rate, superseded in 2022')"*.

## Feedback (after answering)

Offer signed feedback with the least typing:

> *"Was a cited source right or wrong? Reply with its number to vouch it was right (e.g. `2`),
> or the number with a trailing `-` to flag it was wrong (e.g. `2-`)."*

A bare number (or a trailing `+`) is a thumbs-**up**; a trailing `-` is a thumbs-**down**.

**On a down**, ask one quick pick — *bad retrieval* (a poor or irrelevant result) or *wrong
content* (the source is factually wrong):
- **bad retrieval** → record it straight away, no further prompt (`vote="down"`,
  `reason="bad-retrieval"`).
- **wrong content** → ask *"What's wrong with it?"*, capture the reply as the `comment`
  (`vote="down"`, `reason="wrong-content"`), **and** offer the correction path: help the user fix
  the underlying source record under their own login (e.g. edit the Confluence page directly).
  The feedback is logged regardless of whether they take the correction.

Then call `confirm_source` with the **same citation** (the live body hash as `source_state`),
the chosen `vote`/`reason`/`comment`, and the user's email as the token so `confirmed_by` is the
real person, not the service account. A user holds **one current vote per source** — re-voting
(flipping up↔down or changing the reason) replaces their prior vote, and re-voting updates their
stored marker to the current content. Report the result:
- `recorded` — vote saved (or replaced, if they had voted before).
- `rejected` — the vote didn't go through (e.g. the citation didn't resolve, or a down vote
  arrived without a valid reason); say so and don't retry.

## Notes

- Compute the body-hash `source_state` once per page within a run and reuse it for both the
  `current_source_state` you read with and the citation you confirm with, so they line up.
- This skill is self-contained — it does not fetch instructions from Confluence.
- Reads are open; writes (confirmations) are attributed to the verified caller.
