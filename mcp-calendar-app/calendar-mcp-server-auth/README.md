# OAuth-Protected MCP Calendar Server

Minimal OAuth 2.1 implementation following the [MCP Authorization specification](https://modelcontextprotocol.io/docs/tutorials/security/authorization).

**The MCP server is a protected resource that validates bearer tokens FROM clients** (Jupyter notebooks, VS Code, etc.).

## Architecture Overview

```
┌──────────────────┐     Bearer Token      ┌─────────────────┐
│  MCP Client      │────────────────────►  │  MCP Server     │
│  (Jupyter/VSCode)│                        │  (protected)    │
└──────────────────┘                        └─────────────────┘
         │                                           │
         │                                           │
         │ 1. Get Token                              │ 2. Validate Token
         │                                           │    (introspection)
         ▼                                           ▼
   ┌─────────────────────────────────────────────────────┐
   │             Keycloak (Authorization Server)         │
   │  - Issues tokens to clients                         │
   │  - Validates tokens for MCP server                  │
   └─────────────────────────────────────────────────────┘

                                                          │
                                                          │ 3. Call API
                                                          │    (no auth)
                                                          ▼
                                                   ┌──────────────┐
                                                   │ Calendar API │
                                                   │  (internal)  │
                                                   └──────────────┘
```

**Key points:**
- ✅ MCP server = Protected resource (validates incoming tokens)
- ✅ Calendar API = Internal service (no auth needed)
- ✅ Clients get tokens from Keycloak
- ✅ MCP server validates tokens via introspection

## Transport Modes

### STDIO Mode (Local Development)
- **Default mode** for local testing with MCP Inspector or IDE extensions
- OAuth is handled by the MCP client (VS Code, etc.)
- No network exposure, runs as subprocess
- Start with: `python server.py`

### SSE Mode (Network Deployment)
- **Full OAuth 2.1 protection** for network-accessible deployments
- Server validates bearer tokens via Keycloak introspection
- Requires client registration and token management
- Start with: `MCP_TRANSPORT=sse python server.py`

## Files

### 1. [auth.py](auth.py:1) (~200 lines)
**OAuth token validation module**
- `validate_token()` - Validates bearer tokens via Keycloak introspection (RFC 7662)
- `get_protected_resource_metadata()` - Returns RFC 9728 metadata
- `get_www_authenticate_header()` - Returns 401 challenge header
- `AccessToken` - Validated token dataclass
- `Config` - Environment-based configuration

### 2. [token_verifier.py](token_verifier.py:1) (~125 lines)
**Token verifier for FastMCP integration**
- `IntrospectionTokenVerifier` - Implements FastMCP's `TokenVerifier` protocol
- Integrates OAuth validation with FastMCP's auth system
- Used automatically in SSE mode for token validation

### 3. [server.py](server.py:1) (~475 lines)
**OAuth-protected MCP server**
- FastMCP server with 9 calendar tools
- **STDIO mode**: Auth handled by client (default)
- **SSE mode**: Full OAuth 2.1 with token introspection
- Calls Calendar API without authentication (internal service)
- Serves Protected Resource Metadata as MCP resource

## Quick Start

### 1. Set Up Keycloak

Follow [KEYCLOAK_SETUP.md](KEYCLOAK_SETUP.md) for complete instructions.

**Quick version:**
```bash
# Start Keycloak
docker run -p 127.0.0.1:8080:8080 \
  -e KC_BOOTSTRAP_ADMIN_USERNAME=admin \
  -e KC_BOOTSTRAP_ADMIN_PASSWORD=admin \
  quay.io/keycloak/keycloak:latest start-dev

# Access: http://localhost:8080 (admin/admin)
# Create:
# - mcp:tools scope with audience mapper (http://localhost:3000)
# - mcp-server client (for MCP server token introspection)
# - testuser (for testing)
```

### 2. Configure Environment

```bash
cd calendar-mcp-server-auth
cp .env.example .env
# Edit .env and add your OAUTH_CLIENT_SECRET from Keycloak
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Protected MCP Server

**STDIO Mode (default - local development):**
```bash
export $(cat .env | xargs)
python server.py
```

**SSE Mode (network deployment with full OAuth):**
```bash
export $(cat .env | xargs)
export MCP_TRANSPORT=sse
export MCP_HOST=0.0.0.0
export MCP_PORT=3000
python server.py
```

The server will automatically:
- STDIO mode: Run as subprocess, auth handled by client
- SSE mode: Start HTTP server with OAuth token validation

## How It Works

### Token Validation Flow (SSE Mode)

When a client connects to the SSE server:

1. **Initial handshake** - Server returns 401 with `WWW-Authenticate` header
2. **Metadata discovery** - Client fetches OAuth metadata via MCP resource
3. **Authorization** - Client gets token from Keycloak
4. **Authenticated request** - Client sends `Authorization: Bearer <token>`
5. **Token validation** - FastMCP calls `IntrospectionTokenVerifier.verify_token()`
6. **Introspection** - Token verified via Keycloak introspection endpoint
7. **Access granted** - If valid, server processes the MCP request

### IntrospectionTokenVerifier (token_verifier.py)

The `IntrospectionTokenVerifier` class implements FastMCP's `TokenVerifier` protocol:

```python
from token_verifier import IntrospectionTokenVerifier
from fastmcp import FastMCP

# Create verifier for SSE mode
token_verifier = IntrospectionTokenVerifier(
    introspection_endpoint=auth_config.introspection_endpoint,
    server_url=auth_config.server_url,
    client_id=auth_config.OAUTH_CLIENT_ID,
    client_secret=auth_config.OAUTH_CLIENT_SECRET,
    required_scope=auth_config.MCP_SCOPE,
)

# Pass token verifier as auth provider to FastMCP
mcp = FastMCP("calendar-mcp-server-auth", auth=token_verifier)

# FastMCP automatically calls verify_token() for each request
# Returns: AccessToken(token, client_id, scopes, expires_at, resource)
```

### Token Introspection (auth.py)

Low-level validation function (used by token_verifier.py):

```python
from auth import validate_token

# Validate bearer token from client
access_token = await validate_token("eyJhbGciOiJSUzI1NiIs...")

if access_token:
    # Token is valid
    print(f"Client: {access_token.client_id}")
    print(f"Scopes: {access_token.scopes}")
    print(f"User: {access_token.subject}")
else:
    # Token is invalid, expired, or missing required scope/audience
    return 401
```

**Validation checks:**
1. ✅ Token is active
2. ✅ Audience matches MCP server URL (`http://localhost:3000`)
3. ✅ Token has required scope (`mcp:tools`)
4. ✅ Token is not expired

### Protected Resource Metadata (RFC 9728)

```bash
curl http://localhost:3000/.well-known/oauth-protected-resource | jq
```

Expected response:
```json
{
  "resource": "http://localhost:3000",
  "authorization_servers": ["http://localhost:8080/realms/master"],
  "scopes_supported": ["mcp:tools"],
  "bearer_methods_supported": ["header"]
}
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `HOST` | `localhost` | MCP server host |
| `PORT` | `3000` | MCP server port |
| `MCP_TRANSPORT` | `stdio` | Transport mode (`stdio` or `sse`) |
| `CALENDAR_API_BASE_URL` | `http://127.0.0.1:8000` | Calendar API URL (internal) |
| `AUTH_HOST` | `localhost` | Keycloak host |
| `AUTH_PORT` | `8080` | Keycloak port |
| `AUTH_REALM` | `master` | Keycloak realm |
| `OAUTH_CLIENT_ID` | `mcp-server` | MCP server client ID (for introspection) |
| `OAUTH_CLIENT_SECRET` | (required) | MCP server client secret |
| `MCP_SCOPE` | `mcp:tools` | Required OAuth scope |

## Testing

### 1. Test Metadata Endpoint

```bash
curl http://localhost:3000/.well-known/oauth-protected-resource | jq
```

### 2. Test Unauthorized Access

```bash
curl -v http://localhost:3000/
```

Expected: `401 Unauthorized` with `WWW-Authenticate: Bearer realm="mcp", resource_metadata="..."`

### 3. Test with Valid Token

```bash
# Get token from Keycloak (as a client would)
TOKEN=$(curl -X POST http://localhost:8080/realms/master/protocol/openid-connect/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=test-client" \
  -d "client_secret=YOUR_CLIENT_SECRET" \
  -d "username=testuser" \
  -d "password=testpassword" \
  -d "scope=mcp:tools" | jq -r '.access_token')

# Use token to access MCP server
curl -H "Authorization: Bearer $TOKEN" http://localhost:3000/
```

### 4. Test with MCP Inspector

See [TESTING_WITH_INSPECTOR.md](TESTING_WITH_INSPECTOR.md) for complete testing guide.

```bash
export $(cat .env | xargs)
npx @modelcontextprotocol/inspector python server.py
```

## Troubleshooting

### "Introspection failed: 401"

**Cause:** Invalid MCP server credentials

**Fix:**
1. Verify `OAUTH_CLIENT_SECRET` matches Keycloak
2. Ensure `mcp-server` client has authentication enabled in Keycloak

### "Token is inactive"

**Cause:** Token expired or invalid

**Fix:**
1. Get a new token (default lifetime: 5 minutes)
2. Check token was obtained correctly

### "Audience mismatch"

**Cause:** Token audience doesn't match MCP server URL

**Fix:**
1. Verify audience mapper in `mcp:tools` scope
2. Check `Included Custom Audience` = `http://localhost:3000`
3. Ensure `HOST` and `PORT` in `.env` are correct

### "Missing required scope: mcp:tools"

**Cause:** Token doesn't have required scope

**Fix:**
1. Request `scope=mcp:tools` when getting token
2. Verify `mcp:tools` is a **Default** scope in Keycloak

## Production Recommendations

### Security

1. **Use HTTPS** - All production OAuth MUST use HTTPS
2. **Secure Secrets** - Use vault for client secrets
3. **Short Token Lifetimes** - 5-15 minutes for access tokens
4. **Audit Logging** - Log all authentication events

### Performance

1. **Cache Introspection** - Cache validation results with TTL
2. **Connection Pooling** - Reuse HTTP connections to Keycloak
3. **JWT Validation** - Consider using JWT validation instead of introspection

### Monitoring

1. Track 401/403 responses
2. Monitor introspection latency
3. Alert on validation failures

## File Structure

```
calendar-mcp-server-auth/
├── server.py                    # OAuth-protected MCP server (STDIO + SSE modes)
├── token_verifier.py            # IntrospectionTokenVerifier for FastMCP
├── auth.py                      # Token validation utilities
├── requirements.txt             # Dependencies
├── .env.example                # Environment template
├── KEYCLOAK_SETUP.md           # Keycloak configuration guide
├── TESTING_WITH_INSPECTOR.md   # MCP Inspector testing guide
└── README.md                   # This file
```

## Summary

**Complete OAuth 2.1 protection following MCP specification:**

✅ **auth.py** - Token validation utilities via Keycloak introspection
✅ **token_verifier.py** - FastMCP TokenVerifier implementation
✅ **server.py** - Dual-mode MCP server (STDIO + SSE with OAuth)

**Total:** ~800 lines of clean, spec-compliant code

**Features:**
- ✅ **Dual transport modes**: STDIO (local) + SSE (network)
- ✅ **RFC 7662** token introspection with Keycloak
- ✅ **RFC 9728** protected resource metadata
- ✅ **Scope enforcement** (`mcp:tools`)
- ✅ **Audience validation** for MCP server URL
- ✅ **FastMCP integration** via TokenVerifier protocol
- ✅ **MCP authorization specification compliant**

**Production-ready OAuth 2.1 protection for MCP servers!**
