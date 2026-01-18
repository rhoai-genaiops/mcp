"""Token verifier implementation for Keycloak introspection (RFC 7662).

This module provides the IntrospectionTokenVerifier class that integrates with
FastMCP's OAuth support for validating bearer tokens in SSE mode.
"""
import logging
from typing import Optional
import httpx
from mcp.server.auth.provider import AccessToken
from fastmcp.server.http import AuthProvider

logger = logging.getLogger(__name__)

# Shared HTTP client for connection pooling (improves performance)
_http_client: Optional[httpx.AsyncClient] = None


async def get_http_client() -> httpx.AsyncClient:
    """Get or create shared HTTP client with connection pooling.

    This reuses connections to the Keycloak introspection endpoint,
    significantly improving performance (50-200ms vs 100-500ms per request).
    """
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            timeout=10.0,
            limits=httpx.Limits(
                max_keepalive_connections=5,
                max_connections=10,
                keepalive_expiry=30.0,
            ),
        )
        logger.debug("Created shared HTTP client with connection pooling")
    return _http_client


class IntrospectionTokenVerifier(AuthProvider):
    """Token verifier that validates tokens via Keycloak introspection endpoint.

    This implements the AuthProvider interface required by FastMCP for OAuth support.
    It validates bearer tokens by calling Keycloak's introspection endpoint (RFC 7662)
    and checking:
    - Token is active
    - Audience matches the MCP server URL
    - Token has required scopes
    """

    def __init__(
        self,
        introspection_endpoint: str,
        server_url: str,
        client_id: str,
        client_secret: str,
        required_scope: str = "mcp:tools",
    ):
        """Initialize the token verifier.

        Args:
            introspection_endpoint: Keycloak introspection URL
            server_url: MCP server URL (for audience validation)
            client_id: OAuth client ID for introspection
            client_secret: OAuth client secret for introspection
            required_scope: Required OAuth scope (default: mcp:tools)
        """
        super().__init__()
        self.introspection_endpoint = introspection_endpoint
        self.server_url = server_url.rstrip("/")
        self.client_id = client_id
        self.client_secret = client_secret
        self.required_scope = required_scope
        self._mcp_path: Optional[str] = None

    async def verify_token(self, token: str) -> Optional[AccessToken]:
        """Verify a bearer token via Keycloak introspection.

        Args:
            token: Bearer token from Authorization header

        Returns:
            AccessToken if valid, None otherwise
        """
        logger.info(f"🔍 verify_token called with token: {token[:40]}...")
        print(f"DEBUG: verify_token called with token: {token[:40]}...", flush=True)

        # Security: only allow localhost HTTP in development
        if not self.introspection_endpoint.startswith(
            ("https://", "http://localhost", "http://127.0.0.1")
        ):
            logger.error("Introspection endpoint must use HTTPS in production")
            return None

        try:
            # Use shared HTTP client for connection pooling
            client = await get_http_client()
            response = await client.post(
                self.introspection_endpoint,
                data={
                    "token": token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Introspection failed: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return None

            data = response.json()
            logger.info(f"Introspection response: active={data.get('active')}, client_id={data.get('client_id')}, aud={data.get('aud')}, scope={data.get('scope')}")

            # Check if token is active
            if not data.get("active", False):
                logger.warning("Token is inactive or expired")
                return None

            # Validate audience (token must be for this MCP server)
            aud = data.get("aud")
            if not aud:
                logger.error("Missing audience claim in token")
                return None

            audiences = [aud] if isinstance(aud, str) else aud
            if not any(a.rstrip("/") == self.server_url for a in audiences):
                logger.error(
                    f"Audience mismatch. Expected {self.server_url}, got {audiences}"
                )
                return None

            # Extract and validate scopes
            scopes_str = data.get("scope", "")
            scopes = scopes_str.split() if scopes_str else []

            if self.required_scope not in scopes:
                logger.error(f"Token missing required scope: {self.required_scope}")
                return None

            # Return validated AccessToken for FastMCP
            logger.info(
                f"Token validated for client={data.get('client_id')}, "
                f"user={data.get('sub')}, scopes={scopes}"
            )

            return AccessToken(
                token=token,
                client_id=data.get("client_id", "unknown"),
                scopes=scopes,
                expires_at=data.get("exp"),
                resource=self.server_url,
            )

        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None

    def set_mcp_path(self, mcp_path: Optional[str]) -> None:
        """Set the MCP endpoint path.

        Args:
            mcp_path: The MCP endpoint path
        """
        self._mcp_path = mcp_path

    # Inherit get_middleware() from parent AuthProvider class
    # which provides the standard bearer auth middleware implementation

    def get_routes(self, mcp_path: Optional[str] = None) -> list:
        """Get authentication routes.

        Returns the RFC 9728 Protected Resource Metadata endpoint.
        FastMCP will mount these routes automatically.

        Args:
            mcp_path: The MCP endpoint path

        Returns:
            List containing the /.well-known/oauth-protected-resource route
        """
        # Return well-known routes as part of get_routes
        # FastMCP calls get_routes() but not get_well_known_routes()
        return self.get_well_known_routes(mcp_path)

    def get_well_known_routes(self, mcp_path: Optional[str] = None) -> list:
        """Get well-known discovery routes.

        Returns RFC 9728 Protected Resource Metadata endpoint that allows
        MCP clients to discover OAuth requirements.

        Args:
            mcp_path: The MCP endpoint path (unused for well-known routes)

        Returns:
            List containing the /.well-known/oauth-protected-resource route
        """
        from fastmcp.server.http import Route
        from auth import get_protected_resource_metadata
        from starlette.responses import JSONResponse

        async def protected_resource_metadata_endpoint(request):
            """Serve RFC 9728 Protected Resource Metadata."""
            return JSONResponse(get_protected_resource_metadata())

        return [
            Route(
                path="/.well-known/oauth-protected-resource",
                endpoint=protected_resource_metadata_endpoint,
                methods=["GET"],
                name="oauth_protected_resource_metadata",
            )
        ]
