import logging

from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl

from .auth import Authenticator, ContextAuthenticator, GoogleOIDCVerifier, StubAuthenticator
from .citations import ShapeResolver
from .db import Database
from .server import build_server
from .settings import Settings

logger = logging.getLogger("lik_mcp")


def make_server(settings: Settings | None = None) -> FastMCP:
    settings = settings or Settings()
    logger.info("starting lik-mcp with LIK_ENV=%r", settings.env)
    db = Database(settings.conninfo)

    authenticator: Authenticator
    token_verifier = None
    auth_settings = None
    if settings.env in {"local", "test"}:
        # No real identity check: the local container is loopback-only and stdio has no
        # Authorization header. The stub provides a fixed caller so tools have an identity.
        authenticator = StubAuthenticator()
    else:
        # Real deployment (incl. a cloud `dev`): enforce a verified Google token on every
        # request. Refuse to start if unconfigured rather than silently running open.
        if not settings.oauth_client_id or not settings.resource_server_url:
            raise RuntimeError(
                f"LIK_ENV={settings.env!r} requires LIK_OAUTH_CLIENT_ID and "
                "LIK_RESOURCE_SERVER_URL to be set. Refusing to start without real auth."
            )
        token_verifier = GoogleOIDCVerifier(
            client_id=settings.oauth_client_id,
            tokeninfo_url=settings.oauth_tokeninfo_url,
        )
        auth_settings = AuthSettings(
            issuer_url=AnyHttpUrl(settings.oauth_issuer_url),
            resource_server_url=AnyHttpUrl(settings.resource_server_url),
            required_scopes=settings.required_scopes,
        )
        # Identity comes from the verified token the bearer middleware put on the context.
        authenticator = ContextAuthenticator()

    return build_server(
        db,
        authenticator,
        ShapeResolver(),
        host=settings.http_host,
        port=settings.http_port,
        allowed_hosts=settings.allowed_hosts,
        token_verifier=token_verifier,
        auth_settings=auth_settings,
    )


if __name__ == "__main__":
    # Configure logging before make_server so the startup line (and other module logs
    # emitted during setup) are visible — FastMCP only configures logging inside run().
    logging.basicConfig(level=logging.INFO)
    # Read settings once so the transport selection and the server share one config.
    settings = Settings()
    make_server(settings).run(settings.transport)
