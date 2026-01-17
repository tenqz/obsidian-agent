"""Minimal OAuth 2.0 Client Credentials implementation for MCP ChatGPT."""

import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp


@dataclass
class AccessToken:
    """Access token with expiration time."""

    token: str
    expires_at: float
    client_id: str


class TokenStore:
    """In-memory storage for access tokens."""

    def __init__(self) -> None:
        self._tokens: dict[str, AccessToken] = {}

    def create_token(self, client_id: str, ttl_seconds: int = 3600) -> str:
        """Create new access token with TTL."""
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + ttl_seconds
        self._tokens[token] = AccessToken(
            token=token, expires_at=expires_at, client_id=client_id
        )
        self._cleanup_expired()
        return token

    def validate_token(self, token: str) -> AccessToken | None:
        """Validate token and return token info if valid."""
        self._cleanup_expired()
        return self._tokens.get(token)

    def _cleanup_expired(self) -> None:
        """Remove expired tokens from store."""
        now = time.time()
        expired = [t for t, data in self._tokens.items() if data.expires_at < now]
        for token in expired:
            del self._tokens[token]


class OAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for OAuth 2.0 access token validation."""

    def __init__(
        self, app: ASGIApp, token_store: TokenStore, protected_paths: list[str]
    ) -> None:
        super().__init__(app)
        self.token_store = token_store
        self.protected_paths = protected_paths

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip OAuth check for non-protected paths
        if not any(request.url.path.startswith(path) for path in self.protected_paths):
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                {"detail": "Authorization header missing"}, status_code=401
            )

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Invalid authorization scheme"}, status_code=401
            )

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token
        token_info = self.token_store.validate_token(token)
        if not token_info:
            return JSONResponse(
                {"detail": "Invalid or expired token"}, status_code=401
            )

        # Store client_id in request state for logging/debugging
        request.state.client_id = token_info.client_id

        response: Response = await call_next(request)
        return response


def create_oauth_metadata_endpoint(issuer: str) -> Route:
    """Create OAuth 2.0 authorization server metadata endpoint."""

    async def oauth_metadata(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "issuer": issuer,
                "token_endpoint": f"{issuer}/oauth/token",
                "grant_types_supported": ["client_credentials"],
                "token_endpoint_auth_methods_supported": ["client_secret_post"],
                "response_types_supported": [],
                "scopes_supported": ["mcp"],
            }
        )

    return Route("/.well-known/oauth-authorization-server", oauth_metadata)


def create_token_endpoint(
    token_store: TokenStore, client_id: str, client_secret: str
) -> Route:
    """Create OAuth 2.0 token endpoint for client credentials flow."""

    async def token_endpoint(request: Request) -> JSONResponse:
        # Parse form data
        try:
            form = await request.form()
        except Exception as e:
            raise HTTPException(status_code=400, detail="Invalid request body") from e

        # Validate grant_type
        grant_type = form.get("grant_type")
        if grant_type != "client_credentials":
            return JSONResponse(
                {"error": "unsupported_grant_type", "error_description": "Only client_credentials grant type is supported"},
                status_code=400,
            )

        # Validate client credentials
        req_client_id = form.get("client_id")
        req_client_secret = form.get("client_secret")

        if not req_client_id or not req_client_secret:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "client_id and client_secret are required"},
                status_code=400,
            )

        # Extract string values from form data
        client_id_str = str(req_client_id) if req_client_id else ""
        client_secret_str = str(req_client_secret) if req_client_secret else ""

        if client_id_str != client_id or client_secret_str != client_secret:
            return JSONResponse(
                {"error": "invalid_client", "error_description": "Invalid client credentials"},
                status_code=401,
            )

        # Create access token
        ttl = 3600  # 1 hour
        access_token = token_store.create_token(client_id=client_id_str, ttl_seconds=ttl)

        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": ttl,
            }
        )

    return Route("/oauth/token", token_endpoint, methods=["POST"])
