"""OAuth 2.1 token validation for MCP Server.

This module validates tokens FROM clients (Jupyter, VS Code, etc.) using Keycloak
token introspection. The MCP server is a protected resource that requires clients
to present valid bearer tokens.
"""
import os
import httpx
import logging
from typing import Optional

logger = logging.getLogger(__name__)

### Configuration
class Config:
    """OAuth configuration from environment variables."""

    # MCP Server settings
    HOST = os.getenv("HOST", "localhost")
    PORT = int(os.getenv("PORT", 3000))  # Matches .env.example default

    # Keycloak settings
    AUTH_HOST = os.getenv("AUTH_HOST", "localhost")
    AUTH_PORT = int(os.getenv("AUTH_PORT", 8080))
    AUTH_REALM = os.getenv("AUTH_REALM", "master")

    # OAuth server credentials (for token introspection)
    OAUTH_CLIENT_ID = os.getenv("OAUTH_CLIENT_ID", "mcp-server")
    OAUTH_CLIENT_SECRET = os.getenv("OAUTH_CLIENT_SECRET", "")

    # MCP scope
    MCP_SCOPE = os.getenv("MCP_SCOPE", "mcp:tools")

    @property
    def server_url(self):
        """MCP server URL (the protected resource)."""
        return f"http://{self.HOST}:{self.PORT}"

    @property
    def auth_base_url(self):
        """Keycloak base URL."""
        return f"http://{self.AUTH_HOST}:{self.AUTH_PORT}/realms/{self.AUTH_REALM}/"

    @property
    def introspection_endpoint(self):
        """Token introspection endpoint (RFC 7662)."""
        return f"{self.auth_base_url}protocol/openid-connect/token/introspect"

    @property
    def authorization_endpoint(self):
        """Authorization endpoint."""
        return f"{self.auth_base_url}protocol/openid-connect/auth"

    @property
    def token_endpoint(self):
        """Token endpoint."""
        return f"{self.auth_base_url}protocol/openid-connect/token"


config = Config()

### Token Validation

class AccessToken:
    """Validated access token."""

    def __init__(
        self,
        token: str,
        client_id: str,
        scopes: list[str],
        subject: str,
        expires_at: Optional[int] = None
    ):
        """Initialize AccessToken with validated data.

        Args:
            token: The access token string
            client_id: Client ID that owns the token
            scopes: List of granted scopes
            subject: Subject (user) identifier
            expires_at: Optional expiration timestamp
        """
        self.token = token
        self.client_id = client_id
        self.scopes = scopes
        self.subject = subject
        self.expires_at = expires_at

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"AccessToken(token='{self.token[:20]}...', "
            f"client_id='{self.client_id}', "
            f"scopes={self.scopes}, "
            f"subject='{self.subject}', "
            f"expires_at={self.expires_at})"
        )

    def __eq__(self, other) -> bool:
        """Check equality with another AccessToken."""
        if not isinstance(other, AccessToken):
            return NotImplemented
        return (
            self.token == other.token and
            self.client_id == other.client_id and
            self.scopes == other.scopes and
            self.subject == other.subject and
            self.expires_at == other.expires_at
        )

    def __hash__(self) -> int:
        """Make AccessToken hashable for use in sets/dicts."""
        return hash((
            self.token,
            self.client_id,
            tuple(self.scopes),
            self.subject,
            self.expires_at
        ))

    def has_scope(self, scope: str) -> bool:
        """Check if token has a specific scope."""
        return scope in self.scopes


async def validate_token(token: str) -> Optional[AccessToken]:
    """
    Validate token via Keycloak introspection (RFC 7662).

    This validates that:
    1. The token is active
    2. The token has the required scope
    3. The token was issued for this MCP server (audience validation)

    Args:
        token: Bearer token from client's Authorization header

    Returns:
        AccessToken if valid, None otherwise
    """

    # Security: only allow localhost HTTP in development
    if not config.introspection_endpoint.startswith(
        ("https://", "http://localhost", "http://127.0.0.1")
    ):
        logger.error("Introspection endpoint must use HTTPS in production")
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                config.introspection_endpoint,
                data={
                    "token": token,
                    "client_id": config.OAUTH_CLIENT_ID,
                    "client_secret": config.OAUTH_CLIENT_SECRET,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if response.status_code != 200:
                logger.error(f"Introspection failed: {response.status_code}")
                return None

            data = response.json()

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
            server_url = config.server_url.rstrip("/")

            if not any(a.rstrip("/") == server_url for a in audiences):
                logger.error(f"Audience mismatch. Expected {server_url}, got {audiences}")
                return None

            # Extract scopes
            scopes_str = data.get("scope", "")
            scopes = scopes_str.split() if scopes_str else []

            # Check required scope
            if config.MCP_SCOPE not in scopes:
                logger.error(f"Token missing required scope: {config.MCP_SCOPE}")
                return None

            # Return validated token
            return AccessToken(
                token=token,
                client_id=data.get("client_id", "unknown"),
                scopes=scopes,
                subject=data.get("sub", "unknown"),
                expires_at=data.get("exp"),
            )

    except Exception as e:
        logger.error(f"Token validation error: {e}")
        return None


### Protected Resource Metadata (RFC 9728)

def get_protected_resource_metadata() -> dict:
    """
    Return RFC 9728 Protected Resource Metadata.

    This tells MCP clients:
    - What this resource is
    - Where to get authorization
    - What scopes are supported
    - How to send bearer tokens
    """
    return {
        "resource": config.server_url,
        "authorization_servers": [config.auth_base_url.rstrip("/")],
        "scopes_supported": [config.MCP_SCOPE],
        "bearer_methods_supported": ["header"],
    }


def get_www_authenticate_header() -> str:
    """
    Return WWW-Authenticate header for 401 responses.

    This tells clients:
    - Authentication is required
    - Where to find protected resource metadata
    """
    metadata_url = f"{config.server_url}/.well-known/oauth-protected-resource"
    return f'Bearer realm="mcp", resource_metadata="{metadata_url}"'
