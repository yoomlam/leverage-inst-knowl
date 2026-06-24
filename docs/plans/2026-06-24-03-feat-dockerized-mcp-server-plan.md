---
title: "feat: Dockerized HTTP MCP server for Claude Desktop testing"
type: feat
status: completed
date: 2026-06-24
origin: docs/brainstorms/2026-06-24-03-dockerized-mcp-server-for-desktop-requirements.md
---

# feat: Dockerized HTTP MCP server for Claude Desktop testing

## Summary

Make the lik-mcp server selectable between stdio and HTTP transport via one env var, default the
container to HTTP, and add it as a service in the existing `docker-compose.yml` so `docker compose up`
brings up Postgres + an HTTP MCP server — no local uv/Python setup. Claude Desktop connects through a
local `mcp-remote` stdio→HTTP bridge (Desktop custom connectors can't reach localhost; see Key
Technical Decisions). The serving path (HTTP transport, DB over the Compose network) matches what a
deploy would use, and the same server is reachable by MCP Inspector / curl for direct testing.

---

## Problem Frame

Testing the Discovery Layer skills in Claude Desktop currently requires installing uv, provisioning
Python, creating `likdb_local`, and hand-editing `claude_desktop_config.json` with absolute paths — a
lot of machine-specific setup. The existing `Dockerfile` runs stdio + `LIK_ENV=prod`, so it boots inert
and never exercises the HTTP transport a real deploy would serve over. See origin for the full pain and
scope narrative.

---

## Requirements

- R1. Server runs as a long-lived HTTP service (streamable-http). Claude Desktop connects to it through a local `mcp-remote` stdio→HTTP bridge — *not* a direct connector URL, which Desktop routes via Anthropic's cloud and cannot reach on localhost (origin R1, adjusted by Desktop-connector verification).
- R2. Transport is runtime-selectable: container serves HTTP; plain `uv run python -m lik_mcp` stays stdio. (origin R2)
- R3. Container binds localhost-only and runs `LIK_ENV=local` (StubVerifier) — same trust posture as local testing today. (origin R3)
- R4. Server is a service in the existing `docker-compose.yml` next to Postgres; one `docker compose up` runs both; server reaches Postgres over the Compose network. (origin R4)
- R5. Server points at the persistent `likdb_local`, not `likdb_test`. (origin R5)
- R6. README Claude Desktop section is rewritten to the URL/connector flow, replacing the absolute-path `uv` config. (origin R6)
- R7. Same image + HTTP transport are usable for a future deploy — `local` vs `prod` is an env override, not a separate build. (origin R7)

**Origin actors:** A1 (tester/teammate), A2 (Claude Desktop), A3 (lik-mcp server container), A4 (Postgres container)
**Origin flows:** F1 (stand up and connect), F2 (populate then query)

---

## Scope Boundaries

- Real Google OIDC / fail-closed prod auth — stays deferred; this container is local-test only. (origin)
- TLS/HTTPS, cloud hosting, the actual deployed deployment.
- Group→role RLS, real citation resolution, governed-writer controls.
- Redesigning the `likdb_local` DB strategy or the skills themselves.

### Deferred to Follow-Up Work

- Bumping the Dockerfile base image to Python 3.14 to match local dev: out of scope; the project requires `>=3.11` and `python:3.12-slim` satisfies it. Revisit only if 3.14-only syntax lands.

---

## Context & Research

### Relevant Code and Patterns

- `src/lik_mcp/settings.py` — `Settings(BaseSettings)`, env prefix `LIK_`. New transport field lands here, mirroring existing `env` field.
- `src/lik_mcp/__main__.py` — `make_server().run()`; the call site that selects transport.
- `src/lik_mcp/server.py` — `build_server()` returns the `FastMCP("lik-mcp")` instance; unchanged.
- `Dockerfile` — currently `python:3.12-slim`, `pip install .`, `ENV LIK_ENV=prod`, stdio CMD. Updated in U2.
- `docker-compose.yml` — Postgres-only today; `init.sql` mounted into `docker-entrypoint-initdb.d`, healthcheck present. The `db` service name is the in-network host.
- `db/init.sql` — idempotent schema; `CREATE TABLE IF NOT EXISTS …`. Reused to seed `likdb_local`.
- `tests/test_surface.py`, `tests/conftest.py` — existing async server-fixture test pattern to mirror.

### External References (verified against installed `mcp` package)

- `FastMCP.run(transport='stdio'|'sse'|'streamable-http')` — confirmed in the installed version. [Certain]
- FastMCP settings read env with prefix `FASTMCP_`: `FASTMCP_HOST` (default `127.0.0.1`), `FASTMCP_PORT` (default `8000`), `FASTMCP_STREAMABLE_HTTP_PATH` (default `/mcp`). So host/port/path are env-tunable with no code change. [Certain]
- With no `auth_server_provider`/`token_verifier` passed to `FastMCP`, the HTTP transport requires no connection-level auth — the per-tool `token` arg still flows to the StubVerifier. [Certain]

---

## Key Technical Decisions

- **Transport via `LIK_TRANSPORT` env (default `stdio`)**: keeps the existing `LIK_`-prefixed settings convention; stdio stays the no-Docker default so `uv run python -m lik_mcp` and the test fixtures are unaffected. The container sets it to `streamable-http`.
- **Bind `0.0.0.0` in-container, publish `127.0.0.1:8000` on host**: a container process must bind `0.0.0.0` to be reachable through a published port; the localhost-only guarantee (R3) comes from the host-side port mapping, not the in-container bind. Set via `FASTMCP_HOST=0.0.0.0` env in Compose — no code.
- **`LIK_ENV` not baked into the image**: U2 removes the hardcoded `ENV LIK_ENV=prod`; environment is supplied at run time (Compose sets `local`). This is what lets one image serve both local testing and a future `prod` deploy (R7).
- **Auto-create `likdb_local` on first volume init** via a `docker-entrypoint-initdb.d` script reusing `db/init.sql`: aligns with the "less setup" goal. Caveat: entrypoint scripts run only on a fresh data volume — documented, with the existing manual `createdb` path as the recovery for pre-existing volumes.
- **No connection-level auth on the HTTP server**: matches R3's local-test posture; the per-tool token (email) is the only identity, exactly as today over stdio.
- **Desktop connects via `mcp-remote`, not a custom connector URL** *(verified 2026-06-24)*: Claude Desktop custom connectors hand the URL to Anthropic's cloud, which opens the connection from its own IPs — a `localhost` URL is unreachable. The supported local mechanism is `claude_desktop_config.json`, which is stdio-only; `mcp-remote` runs there as a stdio server and bridges to the local HTTP listener over loopback. The HTTP container is kept (deploy-shape + Inspector/curl testing); the bridge is the Desktop-specific adapter. Public-tunnel (ngrok/Cloudflare) is rejected — it would expose the no-auth StubVerifier server to the internet.
- **DNS-rebinding mitigation for the HTTP listener**: the container must bind `0.0.0.0` (a `127.0.0.1`-bound process is unreachable through Docker port mapping), so loopback-binding alone can't be the guard. The host-side `127.0.0.1:8000` publish limits exposure; additionally set FastMCP transport security (allowed/trusted hosts) so the listener rejects spoofed `Host` headers.

---

## Open Questions

### Resolved During Planning

- How is transport selected, and what port/path? → `LIK_TRANSPORT` env for transport; `FASTMCP_*` env for host/port/path (defaults `8000` / `/mcp`).
- Does Desktop need auth to connect to a self-hosted HTTP MCP server? → N/A — Desktop can't reach a localhost HTTP server as a custom connector (verified). It connects via the `mcp-remote` stdio bridge instead; no connection-level auth, and the skills' token arg drives StubVerifier at the tool layer.
- Should `likdb_local` creation be automated? → Yes, via a first-volume init script (U4), with the manual path documented for existing volumes.

### Deferred to Implementation

- Exact field name/type for the transport setting (`transport: str` vs a `Literal`) — settle when editing `settings.py`; a plain `str` passed to `.run()` is sufficient since FastMCP validates the value.
- Whether `tests/conftest.py` needs any change for the transport field — confirm the server fixture still constructs cleanly (it should; `build_server` is untouched).

---

## Implementation Units

- U1. **Runtime-selectable transport**

**Goal:** Add a `LIK_TRANSPORT` setting and pass it to `FastMCP.run()`, defaulting to stdio.

**Requirements:** R2, R7

**Dependencies:** None

**Files:**
- Modify: `src/lik_mcp/settings.py`
- Modify: `src/lik_mcp/__main__.py`
- Test: `tests/test_surface.py` (or a new `tests/test_settings.py`)

**Approach:**
- Add `transport: str = "stdio"` to `Settings` (reads `LIK_TRANSPORT`).
- In `__main__.py`, read settings once and call `make_server().run(settings.transport)`. Avoid constructing `Settings()` twice — have `make_server` return/accept settings or read transport from the same instance.

**Patterns to follow:**
- The existing `env: str = "local"` field and its docstring in `settings.py`.

**Test scenarios:**
- Happy path: `Settings()` with no env → `transport == "stdio"`.
- Happy path: `LIK_TRANSPORT=streamable-http` in env → `Settings().transport == "streamable-http"`.
- Edge case: lowercase/case-insensitivity matches existing `LIK_`-prefixed behavior (pydantic-settings is case-insensitive by default) — assert an env var resolves regardless of case.

**Verification:**
- `uv run python -m lik_mcp` still launches stdio (unchanged default); setting `LIK_TRANSPORT=streamable-http` starts an HTTP listener.

---

- U2. **Container serves HTTP, env-driven**

**Goal:** Update the `Dockerfile` so the image serves HTTP by default and takes environment at run time.

**Requirements:** R1, R3, R7

**Dependencies:** U1

**Files:**
- Modify: `Dockerfile`

**Approach:**
- Remove the hardcoded `ENV LIK_ENV=prod` (environment is supplied at run/compose time).
- Set `ENV LIK_TRANSPORT=streamable-http` and `ENV FASTMCP_HOST=0.0.0.0` as the container defaults.
- `EXPOSE 8000`. Keep `CMD ["python", "-m", "lik_mcp"]` (transport now comes from env, not the command).
- Keep `python:3.12-slim` and `pip install .` (base-image bump is deferred).
- Configure FastMCP transport security (allowed/trusted hosts) so the `0.0.0.0`-bound listener rejects spoofed `Host` headers (DNS-rebinding guard); this is a `build_server` / settings concern if the default doesn't already restrict to loopback + the Compose service name. Confirm the installed FastMCP default during implementation before adding config.

**Patterns to follow:**
- Existing `Dockerfile` layering and comments.

**Test scenarios:**
- Test expectation: none — Dockerfile change with no Python behavior; covered by the U3 end-to-end `docker compose up` verification.

**Verification:**
- `docker build` succeeds; a container run with `LIK_ENV=local` + DB env reachable starts an HTTP server on `:8000` and responds at `/mcp`.

---

- U3. **Compose service for the MCP server**

**Goal:** Add a `lik-mcp` service to `docker-compose.yml` wired to Postgres and published on localhost.

**Requirements:** R1, R3, R4, R5

**Dependencies:** U2

**Files:**
- Modify: `docker-compose.yml`

**Approach:**
- New `lik-mcp` service: `build: .`, `depends_on: db` with `condition: service_healthy` (healthcheck already exists).
- Environment: `LIK_ENV=local`, `LIK_DB_HOST=db`, `LIK_DB_NAME=likdb_local`, `LIK_TRANSPORT=streamable-http`, `FASTMCP_HOST=0.0.0.0` (host/port also baked in U2 as defaults — Compose makes them explicit/overridable).
- Ports: `"127.0.0.1:8000:8000"` — localhost-only publish (R3).

**Patterns to follow:**
- The existing `db` service block, its env style, and the `likdata` volume / healthcheck conventions.

**Test scenarios:**
- Integration: `docker compose up` brings up `db` (healthy) then `lik-mcp`; the server logs a successful DB connection to `likdb_local` and listens on `:8000`.
- Integration: from the host, the published port is reachable at `127.0.0.1:8000` and the MCP endpoint responds at `/mcp`.
- Edge case: the server starts only after the DB healthcheck passes (no connection-refused race) — verify `depends_on` condition holds on a cold `up`.

**Verification:**
- A cold `docker compose up` on a fresh checkout yields a reachable HTTP MCP server backed by `likdb_local`.

---

- U4. **Auto-create `likdb_local` on first volume init**

**Goal:** Seed the persistent `likdb_local` database with the schema when the Postgres volume initializes, so the server's target DB exists without a manual step.

**Requirements:** R5

**Dependencies:** None (independent of U1–U3; ordered before a working `up`)

**Files:**
- Create: `db/init-local.sh`
- Modify: `docker-compose.yml` (mount the script + reuse `init.sql` into the local DB)

**Approach:**
- `init-local.sh` runs inside the Postgres entrypoint: create `likdb_local` if absent (`createdb -U "$POSTGRES_USER" likdb_local` or `psql … -c 'CREATE DATABASE …'`), then apply the existing `db/init.sql` against it (`psql -d likdb_local -f /docker-entrypoint-initdb.d/01-init.sql`).
- Mount it as `02-init-local.sh` so it runs after `01-init.sql` (entrypoint runs files in lexical order).
- Note in the script header: entrypoint scripts run only on a fresh data volume; for an existing volume, the README's manual `createdb` path applies.

**Patterns to follow:**
- The existing `init.sql` mount into `/docker-entrypoint-initdb.d/` in `docker-compose.yml`.
- `db/init.sql`'s idempotent, comment-documented style.

**Test scenarios:**
- Integration: on a fresh `likdata` volume, after `docker compose up` the `likdb_local` database exists and contains the `catalog` and confirmation tables.
- Edge case: re-running on an already-initialized volume does not error — script is a no-op when `likdb_local` already exists (guard the create).
- Integration: `likdb_test` (the entrypoint default DB) is still created and schema-loaded, so `uv run pytest` is unaffected.

**Verification:**
- Fresh `docker compose up` produces both `likdb_test` and `likdb_local` with schema; the `lik-mcp` service connects to `likdb_local` with no manual `createdb`.

---

- U5. **Rewrite README Claude Desktop section for the `mcp-remote` bridge**

**Goal:** Replace the absolute-path `uv` Desktop config with the `docker compose up` + `mcp-remote` bridge flow, and explain why a direct connector URL doesn't work locally.

**Requirements:** R6

**Dependencies:** U3, U4

**Files:**
- Modify: `lik-mcp/README.md`

**Approach:**
- Under "Local database (for manual testing)" → "Connect the service to your agent": present `docker compose up` as the primary path (Postgres + HTTP server).
- **Claude Desktop:** configure `claude_desktop_config.json` with a server whose `command` is `npx` and args `["-y", "mcp-remote", "http://127.0.0.1:8000/mcp"]`. State the one-line reason a raw `http://127.0.0.1:8000/mcp` custom connector fails (Desktop routes connector URLs through Anthropic's cloud, which can't reach localhost) so a reader doesn't try it and get stuck. Note the `mcp-remote` bridge needs Node/npx.
- **Claude CLI:** keep `claude mcp add`; add the HTTP variant `claude mcp add --transport http lik-mcp http://127.0.0.1:8000/mcp` (the CLI connects from the local machine, so localhost works there).
- **Direct testing:** mention MCP Inspector / curl against `http://127.0.0.1:8000/mcp` as a no-client way to verify the server.
- Keep the stdio/`uv run` path as the no-Docker alternative; drop or relocate the obsolete absolute-`uv`-path JSON block.

**Patterns to follow:**
- The current README's subsection structure and the CLI-vs-Desktop split already in place.

**Test scenarios:**
- Test expectation: none — documentation only.

**Verification:**
- A reader with Docker + Node can follow the section to a Desktop session connected through `mcp-remote`, without installing uv/Python or editing absolute paths, and without attempting the dead-end localhost connector URL.

---

## System-Wide Impact

- **Interaction graph:** New entry point is the HTTP listener; tool registration in `build_server` is unchanged, so tool behavior and auth are identical across transports.
- **API surface parity:** stdio (`uv run`, pytest fixtures) and HTTP (container) expose the same five tools — `tests/test_surface.py` already asserts the tool set and is transport-agnostic.
- **State lifecycle risks:** Auto-create script must be idempotent and must not touch `likdb_test`; getting this wrong could break the test DB or fail on volume reuse (covered by U4 edge-case scenarios).
- **Unchanged invariants:** `LIK_ENV=local|test` still selects StubVerifier; any other env still fails closed. `build_server`, the tool contracts, and the test suite's `_test` guard are untouched.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| Desktop custom connectors can't reach localhost (verified 2026-06-24) — a direct connector URL is a dead end for a local container. | U5 documents the `mcp-remote` stdio bridge as the Desktop path and explains why the URL flow fails, so readers don't hit the dead end. |
| `mcp-remote` bridge requires Node/npx on the tester's machine — a new dependency beyond Docker. | Documented in U5; the CLI HTTP path and MCP Inspector need no Node, and are offered as alternatives. Accepted cost of keeping the HTTP container. |
| Localhost-only is the only access control; an HTTP port is a wider surface than stdio, and the `0.0.0.0` in-container bind invites DNS-rebinding. | `127.0.0.1`-only host publish (U3) + FastMCP transport-security allowed-hosts (U2) + `LIK_ENV=local` documented as test-only; real auth stays out of scope per origin. |
| Entrypoint init script runs only on a fresh volume; existing volumes won't get `likdb_local`. | U4 header note + README manual `createdb` path retained. |
| Constructing `Settings()` separately in `__main__` and `make_server` could read env twice / drift. | U1 reads settings once and threads transport from the same instance. |

---

## Sources & References

- **Origin document:** [docs/brainstorms/2026-06-24-03-dockerized-mcp-server-for-desktop-requirements.md](docs/brainstorms/2026-06-24-03-dockerized-mcp-server-for-desktop-requirements.md)
- Related code: `src/lik_mcp/settings.py`, `src/lik_mcp/__main__.py`, `Dockerfile`, `docker-compose.yml`, `db/init.sql`
- FastMCP transport/run + `FASTMCP_*` settings: verified against the installed `mcp` package.
