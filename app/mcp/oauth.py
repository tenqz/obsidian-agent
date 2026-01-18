"""OAuth 2.1 Authorization Code + PKCE implementation for ChatGPT MCP.

Implements:
- RFC 8414 (Authorization Server Metadata)
- RFC 9728 (Protected Resource Metadata)
- RFC 7591 (Dynamic Client Registration)
- OAuth 2.1 with PKCE (S256)
- RFC 6750 (WWW-Authenticate header)

This is specifically designed for ChatGPT MCP integration and follows
OpenAI's MCP OAuth requirements.
"""

import hashlib
import secrets
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import parse_qs, urlencode, urlparse

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from starlette.routing import Route
from starlette.types import ASGIApp


@dataclass
class DynamicClient:
    """Dynamically registered OAuth client."""

    client_id: str
    client_secret: str
    redirect_uris: list[str]
    created_at: float


@dataclass
class AuthorizationCode:
    """Authorization code with PKCE challenge."""

    code: str
    client_id: str
    redirect_uri: str
    code_challenge: str
    code_challenge_method: str
    scope: str
    expires_at: float
    resource: str | None = None


@dataclass
class AccessToken:
    """Access token with metadata."""

    token: str
    client_id: str
    scope: str
    expires_at: float
    resource: str | None = None


class OAuthStore:
    """In-memory storage for OAuth data."""

    def __init__(self, allow_any_client: bool = False) -> None:
        self._clients: dict[str, DynamicClient] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._tokens: dict[str, AccessToken] = {}
        self.allow_any_client = allow_any_client

    def register_client(self, redirect_uris: list[str]) -> DynamicClient:
        """Register new OAuth client (DCR)."""
        client_id = f"mcp_{secrets.token_urlsafe(16)}"
        client_secret = secrets.token_urlsafe(32)
        client = DynamicClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uris=redirect_uris,
            created_at=time.time(),
        )
        self._clients[client_id] = client
        return client

    def get_client(self, client_id: str) -> DynamicClient | None:
        """Get registered client or accept any if allow_any_client=True."""
        client = self._clients.get(client_id)
        if client:
            return client
        
        # If allow_any_client is True, create a virtual client for unregistered clients
        if self.allow_any_client:
            # Create a virtual client that accepts standard ChatGPT redirect URIs
            return DynamicClient(
                client_id=client_id,
                client_secret="",  # No secret verification for virtual clients
                redirect_uris=[
                    "https://chatgpt.com/connector_platform_oauth_redirect",
                    "https://platform.openai.com/apps-manage/oauth",
                ],
                created_at=time.time(),
            )
        return None

    def create_authorization_code(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        scope: str,
        resource: str | None,
        ttl_seconds: int = 600,
    ) -> str:
        """Create authorization code."""
        code = secrets.token_urlsafe(32)
        expires_at = time.time() + ttl_seconds
        self._codes[code] = AuthorizationCode(
            code=code,
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope,
            expires_at=expires_at,
            resource=resource,
        )
        self._cleanup_expired_codes()
        return code

    def consume_authorization_code(self, code: str) -> AuthorizationCode | None:
        """Consume authorization code (one-time use)."""
        self._cleanup_expired_codes()
        return self._codes.pop(code, None)

    def create_access_token(
        self, client_id: str, scope: str, resource: str | None, ttl_seconds: int = 3600
    ) -> str:
        """Create access token."""
        token = secrets.token_urlsafe(32)
        expires_at = time.time() + ttl_seconds
        self._tokens[token] = AccessToken(
            token=token,
            client_id=client_id,
            scope=scope,
            expires_at=expires_at,
            resource=resource,
        )
        self._cleanup_expired_tokens()
        return token

    def validate_token(self, token: str) -> AccessToken | None:
        """Validate access token."""
        self._cleanup_expired_tokens()
        return self._tokens.get(token)

    def _cleanup_expired_codes(self) -> None:
        """Remove expired authorization codes."""
        now = time.time()
        expired = [c for c, data in self._codes.items() if data.expires_at < now]
        for code in expired:
            del self._codes[code]

    def _cleanup_expired_tokens(self) -> None:
        """Remove expired access tokens."""
        now = time.time()
        expired = [t for t, data in self._tokens.items() if data.expires_at < now]
        for token in expired:
            del self._tokens[token]


def verify_pkce(code_verifier: str, code_challenge: str, method: str) -> bool:
    """Verify PKCE code_verifier against code_challenge."""
    if method == "S256":
        computed = (
            hashlib.sha256(code_verifier.encode()).digest().hex()
        )
        # Base64url without padding
        import base64
        computed_b64 = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).decode().rstrip("=")
        return computed_b64 == code_challenge
    elif method == "plain":
        return code_verifier == code_challenge
    return False


class OAuthMiddleware(BaseHTTPMiddleware):
    """Middleware for OAuth 2.1 access token validation with WWW-Authenticate."""

    def __init__(
        self,
        app: ASGIApp,
        oauth_store: OAuthStore,
        protected_paths: list[str],
        resource_uri: str,
        metadata_uri: str,
    ) -> None:
        super().__init__(app)
        self.oauth_store = oauth_store
        self.protected_paths = protected_paths
        self.resource_uri = resource_uri
        self.metadata_uri = metadata_uri

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        # Skip OAuth check for non-protected paths
        if not any(request.url.path.startswith(path) for path in self.protected_paths):
            return await call_next(request)

        # Extract Bearer token
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return self._unauthorized_response("Bearer token required")

        token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate token
        token_info = self.oauth_store.validate_token(token)
        if not token_info:
            return self._unauthorized_response("Invalid or expired token")

        # Store token info in request state
        request.state.oauth_client_id = token_info.client_id
        request.state.oauth_scope = token_info.scope

        response: Response = await call_next(request)
        return response

    def _unauthorized_response(self, error_description: str) -> Response:
        """Return 401 with WWW-Authenticate header per RFC 6750."""
        www_authenticate = (
            f'Bearer realm="{self.resource_uri}", '
            f'resource_metadata="{self.metadata_uri}", '
            f'scope="mcp", '
            f'error="invalid_token", '
            f'error_description="{error_description}"'
        )
        return JSONResponse(
            {"error": "invalid_token", "error_description": error_description},
            status_code=401,
            headers={"WWW-Authenticate": www_authenticate},
        )


def create_protected_resource_metadata_endpoint(
    resource_uri: str, authorization_server: str
) -> Route:
    """Create Protected Resource Metadata endpoint (RFC 9728)."""

    async def protected_resource_metadata(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "resource": resource_uri,
                "authorization_servers": [authorization_server],
                "scopes_supported": ["mcp"],
                "bearer_methods_supported": ["header"],
                "resource_documentation": f"{resource_uri}/docs",
            }
        )

    return Route("/.well-known/oauth-protected-resource", protected_resource_metadata)


def create_authorization_server_metadata_endpoint(issuer: str) -> Route:
    """Create Authorization Server Metadata endpoint (RFC 8414)."""

    async def authorization_server_metadata(request: Request) -> JSONResponse:
        return JSONResponse(
            {
                "issuer": issuer,
                "authorization_endpoint": f"{issuer}/oauth/authorize",
                "token_endpoint": f"{issuer}/oauth/token",
                "registration_endpoint": f"{issuer}/oauth/register",
                "scopes_supported": ["mcp"],
                "response_types_supported": ["code"],
                "grant_types_supported": ["authorization_code"],
                "code_challenge_methods_supported": ["S256"],
                "token_endpoint_auth_methods_supported": ["client_secret_post"],
            }
        )

    return Route(
        "/.well-known/oauth-authorization-server", authorization_server_metadata
    )


def create_dynamic_client_registration_endpoint(oauth_store: OAuthStore) -> Route:
    """Create Dynamic Client Registration endpoint (RFC 7591)."""

    async def register_client(request: Request) -> JSONResponse:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(
                {"error": "invalid_request", "error_description": "Invalid JSON"},
                status_code=400,
            )

        redirect_uris = body.get("redirect_uris", [])
        if not redirect_uris or not isinstance(redirect_uris, list):
            return JSONResponse(
                {
                    "error": "invalid_redirect_uri",
                    "error_description": "redirect_uris is required and must be an array",
                },
                status_code=400,
            )

        # Register client
        client = oauth_store.register_client(redirect_uris)

        return JSONResponse(
            {
                "client_id": client.client_id,
                "client_secret": client.client_secret,
                "redirect_uris": client.redirect_uris,
                "client_id_issued_at": int(client.created_at),
                "grant_types": ["authorization_code"],
                "response_types": ["code"],
                "token_endpoint_auth_method": "client_secret_post",
            },
            status_code=201,
        )

    return Route("/oauth/register", register_client, methods=["POST"])


def create_authorization_endpoint(oauth_store: OAuthStore) -> Route:
    """Create Authorization endpoint for user consent."""

    async def authorize(request: Request) -> Response:
        params = dict(request.query_params)

        # Validate required parameters
        client_id = params.get("client_id")
        redirect_uri = params.get("redirect_uri")
        response_type = params.get("response_type")
        code_challenge = params.get("code_challenge")
        code_challenge_method = params.get("code_challenge_method")
        scope = params.get("scope", "mcp")
        state = params.get("state", "")
        resource = params.get("resource")

        # Validate client
        client = oauth_store.get_client(client_id) if client_id else None
        if not client:
            return JSONResponse(
                {"error": "invalid_client"}, status_code=400
            )

        # Validate redirect_uri
        if redirect_uri not in client.redirect_uris:
            return JSONResponse(
                {"error": "invalid_redirect_uri"}, status_code=400
            )

        # Validate PKCE
        if not code_challenge or code_challenge_method != "S256":
            error_params = {
                "error": "invalid_request",
                "error_description": "code_challenge with S256 method is required",
                "state": state,
            }
            return RedirectResponse(f"{redirect_uri}?{urlencode(error_params)}")

        # Auto-approve (no user interaction for simplicity)
        # In production, show consent screen here
        code = oauth_store.create_authorization_code(
            client_id=client_id,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method=code_challenge_method,
            scope=scope,
            resource=resource,
        )

        # Redirect back with authorization code
        response_params = {"code": code, "state": state}
        return RedirectResponse(f"{redirect_uri}?{urlencode(response_params)}")

    return Route("/oauth/authorize", authorize, methods=["GET"])


def create_token_endpoint(oauth_store: OAuthStore) -> Route:
    """Create Token endpoint for authorization code exchange."""

    async def token_exchange(request: Request) -> JSONResponse:
        try:
            form = await request.form()
        except Exception:
            return JSONResponse(
                {"error": "invalid_request"}, status_code=400
            )

        grant_type = form.get("grant_type")
        if grant_type != "authorization_code":
            return JSONResponse(
                {"error": "unsupported_grant_type"}, status_code=400
            )

        # Extract parameters
        code = str(form.get("code", ""))
        redirect_uri = str(form.get("redirect_uri", ""))
        client_id = str(form.get("client_id", ""))
        client_secret = str(form.get("client_secret", ""))
        code_verifier = str(form.get("code_verifier", ""))

        # Validate client
        client = oauth_store.get_client(client_id)
        if not client:
            return JSONResponse(
                {"error": "invalid_client"}, status_code=401
            )
        
        # For virtual clients (allow_any_client=True), skip secret verification
        # For registered clients, verify secret
        if client.client_secret and client.client_secret != client_secret:
            return JSONResponse(
                {"error": "invalid_client"}, status_code=401
            )

        # Consume authorization code
        auth_code = oauth_store.consume_authorization_code(code)
        if not auth_code:
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "Invalid or expired authorization code"},
                status_code=400,
            )

        # Validate authorization code
        if auth_code.client_id != client_id:
            return JSONResponse(
                {"error": "invalid_grant"}, status_code=400
            )

        if auth_code.redirect_uri != redirect_uri:
            return JSONResponse(
                {"error": "invalid_grant"}, status_code=400
            )

        # Verify PKCE
        if not verify_pkce(
            code_verifier, auth_code.code_challenge, auth_code.code_challenge_method
        ):
            return JSONResponse(
                {"error": "invalid_grant", "error_description": "PKCE verification failed"},
                status_code=400,
            )

        # Create access token
        access_token = oauth_store.create_access_token(
            client_id=client_id, scope=auth_code.scope, resource=auth_code.resource
        )

        return JSONResponse(
            {
                "access_token": access_token,
                "token_type": "Bearer",
                "expires_in": 3600,
                "scope": auth_code.scope,
            }
        )

    return Route("/oauth/token", token_exchange, methods=["POST"])
