# BI Pipeline — Deterministic data pipeline & warehouse

*The deterministic reporting track that runs alongside the Discovery Layer (DL). For the overall design see <u>Architecture</u>; for the phased build plan see <u>Strategy</u>; for stores see <u>Storage</u>.*

## Purpose

Serve operational reporting (BI dashboards) via the **same MCP interface** as everything else. A secondary deterministic pipeline (DSs → pipeline → warehouse → BI dashboards) serves operational reporting with **no AI**.

```
DSs → Deterministic Pipeline → Warehouse → BI Dashboards
```

## Not a fifth step — an independent track

It builds on the same foundations (MCP, SSO, and — once it registers outputs — the Catalog) but isn't gated on completing the levels in sequence; start it whenever BI matters. A **deterministic path, no AI:**

- **Deterministic pipelines** handle known, repeatable transforms (dashboard tables, aggregations, metrics, scheduled extracts), typically in a **warehouse**. They assign each output a sharing group (same fail-closed model as <u>Strategy</u> §2) and register outputs in the Catalog, like the DL-creation skill.
- **The warehouse is exposed via MCP like any other DS.** The Catalog points to warehouse tables (`store_kind = warehouse`, `bq://dataset.table`) just as it points to a Confluence page.

All updates propagate/assign ACL metadata and register location in the Catalog.

*Hardening:* the warehouse is non-versioned, so its writers run under governed-writer controls (<u>Storage</u>). BigQuery honors a Google Group via IAM directly; an admin only provisions a Group for an audience whose source DS isn't already group-based.
