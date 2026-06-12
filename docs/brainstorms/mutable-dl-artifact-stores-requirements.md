---
date: 2026-06-11
topic: mutable-dl-artifact-stores
---

# Writable Stores for Mutable Discovery Layer Artifacts

## Summary

Move the Discovery Layer catalog and other AI-maintained DL artifacts off "Google-Sheet-via-Drive-MCP" to stores whose off-the-shelf connectors support in-place edits — the catalog and human-readable artifacts to Confluence pages — because the Google Drive connector is create-only and the create-new-file workaround breaks the catalog's stable address, version history, and (for confirmation signals) durability.

---

## Problem Frame

The Discovery Layer assumes its producer (the DL skill) can update artifacts in place: the catalog upserts rows every run, summaries are re-derived on a schedule, freshness signals flip over time, and confirmation signals accumulate. But the only off-the-shelf write path available — the Google Drive connector — exposes read and create-file, with **no in-place update**. The existing `discovery-catalog-sync` skill already hit this and works around it by reading the sheet, merging in memory, and creating a *new* spreadsheet each run.

That workaround carries three costs, worst for the catalog: the spreadsheet ID changes every sync, breaking the one property the catalog exists to provide — a stable, well-known address agents know in advance; version history is lost, so the "revert is recovery" and attributed-edit-trail model collapses; and orphaned sheets accumulate to be deleted by hand. For confirmation signals the same workaround risks real data loss, since those are durable and cannot be recomputed.

The constraint is the off-the-shelf connector's, not the architecture's — but the team's standing constraint is to use connectors as they ship, not to build a custom write service. So the fix is to relocate mutable artifacts to stores whose shipped connectors do support updates.

---

## Actors

- A1. DL skill (service identity): the automated producer; reads sources and writes/updates DL artifacts under its own non-user account.
- A2. Named catalog owners: a small human set permitted to edit the catalog directly; everyone else has read-only.
- A3. Consumers (agents and people): resolve the catalog's well-known address, then follow pointers to artifacts.
- A4. Admin: provisions the Google Group ↔ Confluence group sync that backs access control.

---

## Key Flows

- F1. Catalog sync (in place)
  - **Trigger:** scheduled or on-demand catalog refresh.
  - **Actors:** A1 (and A2 for manual edits).
  - **Steps:** read the source project-index pages → read the *current* catalog object → merge, preserving manually-added rows → write the merged result back to the **same** object → report rows added/updated/removed.
  - **Outcome:** the catalog reflects current sources at an address that did not change, with the update captured in version history.
  - **Covered by:** R1, R4, R5, R6.

---

## Requirements

**Store selection**
- R1. The catalog resides in an update-capable off-the-shelf store. Chosen store: a **Confluence page**, updated in place via the Atlassian connector.
- R2. Human-readable DL artifacts (summaries, digests, curated indexes — strategy §2.1) that are re-derived over time reside in **Confluence pages**, not Google Docs reached through the Drive connector.
- R3. The strategy's default "start in a Google Sheet, promote to a database later" pattern is revised: any artifact that is *mutated over time* starts in an update-capable store from the outset. Human-facing/catalog → Confluence; machine signals → an update-capable store (not a Drive-connector Sheet).

**In-place update behavior**
- R4. The catalog keeps a **stable address** across updates — the Confluence page identifier and URL are invariant under edits, so consumers can resolve it a priori.
- R5. Catalog and summary updates are **upserts to the same object**: read current → merge (preserving manual rows) → write back to the same object. A new object is never created to represent an update.
- R6. The chosen stores provide **version history on the same object**, supplying attribution and revert for the catalog and human-readable artifacts.

**Affected-output coverage**
- R7. The decision explicitly covers every AI-updated DL output that needs in-place edit: the catalog (upsert + stable address), re-derived human-readable artifacts (§2.1), freshness/obsolescence signals (§2.2) at any small-scale stage, and confirmation signals (§2.3).
- R8. Confirmation signals (§2.3), being **durable and non-recomputable**, must never use a create-new-object workaround. They **start as a Confluence-page table** (updatable in place, with version-history revert and Google-Group access) and **promote to a service-fronted store** (Postgres + app) at scale when hard write-time enforcement is needed — never a Drive-connector Sheet.
- R9. Create-new-object (the connector's `create_file`) remains acceptable **only** for an artifact that is fully recomputed each run, needs no stable address, and needs no cross-run version lineage — which excludes the artifacts in R7.

**Access model preservation**
- R10. The chosen stores preserve the existing Google SSO + Groups access model: Confluence page/space restrictions synced from Google Groups (Atlassian Access / SCIM). Catalog reads stay open within the org for transparency; writes are restricted to the DL skill service account (A1) and named owners (A2).

---

## Acceptance Examples

- AE1. **Covers R4, R5.** Given a catalog already published at a known address, when the sync runs again, then the catalog's page identifier and URL are unchanged and the rows reflect current sources.
- AE2. **Covers R5.** Given a source page that was deleted since the last run, when the sync runs, then its row is removed or flagged in the same catalog page rather than left dangling.
- AE3. **Covers R6, R10.** Given a named owner makes a bad manual edit to the catalog, when it is noticed, then the prior version is restorable from page history and the edit is attributed to that owner.
- AE4. **Covers R2, R6.** Given a human-verified summary, when the DL skill re-derives it, then the update lands on the same page, preserving its catalog pointer and prior version lineage.

---

## Success Criteria

- The catalog has exactly one stable address that consumers resolve in advance, and re-syncs never change it.
- No DL artifact depends on create-new-object semantics to record a change; orphaned-file accumulation is eliminated.
- Access control is still expressed entirely in Google Groups — no second permission model is introduced.
- `ce-plan` can rewrite the `discovery-catalog-sync` skill against an in-place Confluence update without having to choose the store or invent the access model.

---

## Scope Boundaries

- Not building a custom MCP write service (e.g., native Google Sheets API) — ruled out by the off-the-shelf-only constraint.
- Not moving machine-signal stores to a database *now*; that stays the documented scale-time promotion.
- The GitHub-file option and the database-now option were considered and not chosen for the catalog.
- Rewriting the `discovery-catalog-sync` skill implementation is planning work, not part of this decision.
- Machine-signal stores already at scale in BigQuery/Postgres are unaffected — their clients upsert natively.

---

## Key Decisions

- **Confluence over GitHub for the catalog:** Confluence restrictions map to Google Groups via SCIM (preserving the strategy's one access model) and pages are human-openable for non-technical owners. GitHub would fork access control into repo permissions and is less approachable, despite a stronger git-diff/PR-review story. (GitHub's weaker access fit is partly softened for the catalog specifically, since the catalog stores pointers, not permissions — a bad row can misdirect but never widen access.)
- **Confluence over a database now:** subject count is low (dozens to low-hundreds); a database is the documented promotion target for scale and would cost the human transparency the catalog values.
- **Splitting stores is acceptable:** catalog and human-readable artifacts → Confluence; machine signals → a service-fronted table (DB at scale); confirmation signals → a Confluence-page on-ramp, promoting to a service-fronted store at scale. Each artifact goes where its consumers and write-integrity needs point.
- **Confirmations keep a cheap Confluence-page on-ramp** rather than starting service-fronted: it preserves free version-history revert (their only recovery, since they're non-recomputable), transparency, and Google-Group access, and stays off-the-shelf — accepting softer write-time enforcement until promotion. A page is an awkward home for machine append/de-dup, so promotion to a service-fronted store happens when scale or hard rate-limiting demands it.
- **Co-location bonus:** the catalog's source data (project-index pages) already lives in Confluence, so the sync flow can run through a single connector.

---

## Dependencies / Assumptions

- The connected Atlassian connector exposes an in-place page-update capability (e.g., `updateConfluencePage`). **Confirmed.**
- The Google Group ↔ Confluence group SCIM sync (Atlassian Access / Guard) is provisioned — already a prerequisite called out in strategy §2 access control.
- A Confluence page's identifier and URL remain stable across content edits and title changes.

---

## Outstanding Questions

### Resolve Before Planning

- None. (The Atlassian connector's in-place page-update capability is confirmed, so the Confluence-page direction holds and the GitHub-file fallback is not needed.)

### Deferred to Planning

- [Affects R2][Technical] Catalog content format on a Confluence page (native table macro vs. CSV/structured block) and how consumers parse it in one lookup.
- [Affects R7][Technical] Whether machine-retrieval signals (§2.2) start in a small service-fronted table or a Confluence-page table at the very smallest scale (confirmations resolved to a Confluence-page on-ramp; §2.2 leans service-fronted but the tiny-scale on-ramp is open).
- [Affects R5][Technical] Concurrency handling when the service account and a named owner edit the catalog at the same time.
