"""MCP (Model Context Protocol) stdio server for the Obsidian Vault Agent.

This server exposes a minimal set of tools for interacting with a mounted vault
via the existing `VaultService`, without going through the HTTP API.
"""

import os
from pathlib import Path
from typing import Any

import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.routing import Mount

from app.mcp.oauth import (
    OAuthMiddleware,
    TokenStore,
    create_oauth_metadata_endpoint,
    create_token_endpoint,
)
from app.vault.service import VaultService

# NOTE: For Cloudflare Quick Tunnel the public hostname changes often, which
# clashes with DNS rebinding protection allowlists. We'll disable it for now.
mcp = FastMCP(
    name="ObsidianVaultAgent",
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


def _get_vault_service() -> VaultService:
    vault_path = os.getenv("VAULT_PATH", "/vault")
    if not Path(vault_path).exists():
        raise ValueError("vault path is not configured or does not exist")
    return VaultService(vault_path=vault_path)


def _safe_error_message(exc: Exception) -> str:
    # Avoid leaking absolute filesystem paths in error messages.
    if isinstance(exc, FileNotFoundError):
        return "path not found"
    if isinstance(exc, NotADirectoryError):
        return "path is not a directory"
    if isinstance(exc, IsADirectoryError):
        return "path is a directory"
    if isinstance(exc, ValueError):
        return str(exc)
    return "unexpected error"


@mcp.tool()
def vault_ls(path: str) -> dict[str, Any]:
    """List directories and markdown files inside the vault.

    Args:
        path: Relative path inside vault (empty string for root)
    """
    svc = _get_vault_service()
    try:
        return {"entries": svc.ls(path=path)}
    except Exception as e:  # noqa: BLE001
        raise ValueError(_safe_error_message(e)) from None


@mcp.tool()
def vault_read(path: str) -> dict[str, str]:
    """Read a markdown file inside the vault and return its content."""
    svc = _get_vault_service()
    try:
        return {"content": svc.read(path=path)}
    except Exception as e:  # noqa: BLE001
        raise ValueError(_safe_error_message(e)) from None


@mcp.tool()
def vault_write(path: str, content: str) -> dict[str, bool]:
    """Create or overwrite a markdown file inside the vault."""
    svc = _get_vault_service()
    try:
        svc.write(path=path, content=content)
        return {"ok": True}
    except Exception as e:  # noqa: BLE001
        raise ValueError(_safe_error_message(e)) from None


if __name__ == "__main__":
    import sys

    # Check environment variable to determine transport mode
    transport_mode = os.getenv("MCP_TRANSPORT", "sse")

    if transport_mode == "stdio":
        # stdio mode for direct MCP client connection
        mcp.run(transport="stdio")
    else:
        # SSE mode for network access (default for Docker)
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "8001"))
        use_oauth = os.getenv("MCP_OAUTH_ENABLED", "false").lower() == "true"

        # Create SSE app
        mcp_app = mcp.sse_app()

        if use_oauth:
            # OAuth 2.0 mode
            client_id = os.getenv("MCP_OAUTH_CLIENT_ID")
            client_secret = os.getenv("MCP_OAUTH_CLIENT_SECRET")
            issuer = os.getenv("MCP_OAUTH_ISSUER", f"http://localhost:{port}")

            if not client_id or not client_secret:
                print(
                    "ERROR: MCP_OAUTH_CLIENT_ID and MCP_OAUTH_CLIENT_SECRET must be set when OAuth is enabled",
                    file=sys.stderr,
                    flush=True,
                )
                sys.exit(1)

            # Create token store and OAuth endpoints
            token_store = TokenStore()

            # Create main app with OAuth endpoints
            app = Starlette(
                routes=[
                    create_oauth_metadata_endpoint(issuer),
                    create_token_endpoint(token_store, client_id, client_secret),
                    Mount("/", app=mcp_app),
                ],
                middleware=[
                    Middleware(
                        OAuthMiddleware,
                        token_store=token_store,
                        protected_paths=["/sse", "/messages"],
                    )
                ],
            )

            print("OAuth 2.0 authentication enabled for SSE server", file=sys.stderr, flush=True)
            print(f"OAuth issuer: {issuer}", file=sys.stderr, flush=True)
            print(f"Token endpoint: {issuer}/oauth/token", file=sys.stderr, flush=True)
            print(f"Metadata endpoint: {issuer}/.well-known/oauth-authorization-server", file=sys.stderr, flush=True)
        else:
            # No authentication mode
            app = mcp_app
            print(
                "WARNING: OAuth is disabled - SSE server running without authentication",
                file=sys.stderr,
                flush=True,
            )

        print(f"Starting MCP SSE server on {host}:{port}", file=sys.stderr, flush=True)
        uvicorn.run(app, host=host, port=port, log_level="info")


