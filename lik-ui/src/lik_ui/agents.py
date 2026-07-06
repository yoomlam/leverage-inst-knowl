"""Agent selection and required-connection resolution.

The set of connections a session needs is not hardcoded — it is read from the selected
agent's own definition via the Claude SDK (its declared MCP servers). lik-ui compares that
required set against the credentials already in the user's vault to show connected/missing
status and drive the connect action for each missing source.
"""

from typing import Protocol

from .settings import Settings
from .vault import VaultClient, ensure_user_vault


class AgentsClient(Protocol):
    def declared_servers(self, agent_id: str) -> list[dict]:
        """Return the agent's declared MCP servers as ``[{"name", "url"}, ...]``."""
        ...


class AnthropicAgentsClient:
    """Real ``AgentsClient`` backed by the Anthropic SDK's Managed Agents API."""

    def __init__(self, api_key: str):
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)

    def declared_servers(self, agent_id: str) -> list[dict]:
        agent = self._client.beta.agents.retrieve(agent_id)
        return [{"name": s.name, "url": s.url} for s in (agent.mcp_servers or [])]


def build_agents_client(settings: Settings) -> AgentsClient | None:
    if settings.is_stub:
        return None
    return AnthropicAgentsClient(settings.anthropic_api_key)


def resolve_connections(
    agents_client: AgentsClient, vault_client: VaultClient | None, agent_id: str, vault_id: str
) -> list[dict]:
    """For each server the agent declares, mark whether the user's vault already has a
    matching credential (exact URL match, as the platform requires)."""
    declared = agents_client.declared_servers(agent_id)
    connected = vault_client.list_credential_urls(vault_id) if vault_client else set()
    return [{"name": d["name"], "url": d["url"], "connected": d["url"] in connected} for d in declared]


def register_agent_routes(app) -> None:
    from fastapi import Request
    from fastapi.responses import HTMLResponse

    from .app import templates
    from .app_auth import require_user

    @app.get("/connections", response_class=HTMLResponse)
    async def connections(request: Request, agent_id: str):
        user = require_user(request)
        settings: Settings = request.app.state.settings
        agent = next((a for a in settings.agents if a.agent_id == agent_id), None)
        if not agent:
            return HTMLResponse("Unknown agent.", status_code=404)

        try:
            vault_id = ensure_user_vault(request.app.state.store, request.app.state.vault_client, user)
            conns = resolve_connections(
                request.app.state.agents_client, request.app.state.vault_client, agent_id, vault_id
            )
        except Exception as exc:  # noqa: BLE001 - surface SDK/agent/vault errors as a page, not a 500
            return HTMLResponse(f"Could not load the agent's required connections: {exc}", status_code=502)

        return templates.TemplateResponse(request, "connections.html", {"agent": agent, "connections": conns})
