# OAuth-Protected MCP Calendar Server

Minimal OAuth 2.1 implementation following the [MCP Authorization specification](https://modelcontextprotocol.io/docs/tutorials/security/authorization).

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
