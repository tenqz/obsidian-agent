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
    OAuthStore,
    create_authorization_endpoint,
    create_authorization_server_metadata_endpoint,
    create_dynamic_client_registration_endpoint,
    create_protected_resource_metadata_endpoint,
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
            # ChatGPT MCP OAuth 2.1 with PKCE
            issuer = os.getenv("MCP_OAUTH_ISSUER", f"http://localhost:{port}")
            
            print("OAuth 2.1 (Authorization Code + PKCE) for ChatGPT MCP", file=sys.stderr, flush=True)

            # Create OAuth store with allow_any_client for ChatGPT compatibility
            oauth_store = OAuthStore(allow_any_client=True)

            # Resource URI for protected resource metadata
            resource_uri = issuer
            metadata_uri = f"{issuer}/.well-known/oauth-protected-resource"

            # Create main app with OAuth endpoints
            app = Starlette(
                routes=[
                    # Protected Resource Metadata (RFC 9728)
                    create_protected_resource_metadata_endpoint(resource_uri, issuer),
                    # Authorization Server Metadata (RFC 8414)
                    create_authorization_server_metadata_endpoint(issuer),
                    # Dynamic Client Registration (RFC 7591)
                    create_dynamic_client_registration_endpoint(oauth_store),
                    # Authorization endpoint (OAuth 2.1)
                    create_authorization_endpoint(oauth_store),
                    # Token endpoint
                    create_token_endpoint(oauth_store),
                    # MCP SSE endpoint
                    Mount("/", app=mcp_app),
                ],
                middleware=[
                    Middleware(
                        OAuthMiddleware,
                        oauth_store=oauth_store,
                        protected_paths=["/sse", "/messages"],
                        resource_uri=resource_uri,
                        metadata_uri=metadata_uri,
                    )
                ],
            )

            print(f"OAuth issuer: {issuer}", file=sys.stderr, flush=True)
            print(f"Protected Resource: {metadata_uri}", file=sys.stderr, flush=True)
            print(f"Authorization Server: {issuer}/.well-known/oauth-authorization-server", file=sys.stderr, flush=True)
            print(f"Endpoints: /oauth/authorize, /oauth/token, /oauth/register", file=sys.stderr, flush=True)
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


