FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

# Serve the long-lived HTTP transport by default; bind all interfaces so the listener
# is reachable through Docker's published port (the host side publishes 127.0.0.1 only,
# and the server restricts the accepted Host header to loopback — see server.py).
ENV LIK_TRANSPORT=streamable-http
ENV LIK_HTTP_HOST=0.0.0.0

# Default to the fail-closed env so an unconfigured run of this image rejects every
# call (real Google OIDC isn't built yet — see auth.py). docker compose overrides this
# to LIK_ENV=local for testing; a deploy keeps prod until OIDC lands. One image, env
# supplied at run time.
ENV LIK_ENV=prod

EXPOSE 8000
CMD ["python", "-m", "lik_mcp"]
