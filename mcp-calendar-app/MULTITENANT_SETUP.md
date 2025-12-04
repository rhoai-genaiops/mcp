# Multi-Tenant Calendar Application Setup Guide

This guide explains how the calendar application has been configured for multi-tenancy on OpenShift.

## Overview

The calendar application now supports multiple users, with each user seeing only their own calendar events. This is achieved through:

1. **User Identification**: OpenShift OAuth proxy authenticates users and passes their username to the application
2. **Data Isolation**: Database schema includes `user_id` column to segregate user data
3. **API Enforcement**: All API endpoints filter events by the authenticated user
4. **MCP Server Support**: The MCP server can be configured with a user ID for AI agent integration

## Architecture Changes

### Database Schema
- Added `user_id TEXT` column to the `calendar` table
- All events are now associated with a specific user
- Queries automatically filter by user_id when authenticated

### API Layer
The Calendar API (`calendar-api/server.py`) now:
- Extracts user ID from HTTP headers set by OAuth proxy
- Supports three header formats (in priority order):
  1. `X-Forwarded-User` - Set by OpenShift OAuth proxy
  2. `X-User-ID` - Custom header for development/testing
  3. `X-Remote-User` - Alternative auth header
- Automatically filters all CRUD operations by user_id
- Ensures users can only access their own events

### Frontend
The React frontend:
- Deployed behind OAuth proxy for authentication
- Nginx proxy passes user headers to backend API
- Users are automatically redirected to OpenShift login

### MCP Server
The MCP server:
- Accepts `USER_ID` environment variable for user context
- Passes user ID in `X-User-ID` header to API requests
- Enables personalized AI agent interactions per user

## Deployment

### Prerequisites
- OpenShift cluster with OAuth configured
- Users provisioned via htpasswd (user0-user49 as in your deploy-lab)
- Helm 3.x installed

### Step 1: Migrate Existing Database (if applicable)

If you have existing calendar data:

```bash
cd calendar-api
python migrate_multitenant.py --db-path /path/to/CalendarDB.db --default-user admin
```

This will:
- Add `user_id` column to existing events
- Assign a default user to pre-existing events

### Step 2: Build Container Images

```bash
# Build API image with multi-tenant support
cd calendar-api
podman build -t quay.io/rhoai-genaiops/calendar-api:v3-multitenant .
podman push quay.io/rhoai-genaiops/calendar-api:v3-multitenant

# Build MCP server image
cd ../calendar-mcp-server
podman build -t quay.io/rhoai-genaiops/calendar-mcp-server:v3-multitenant .
podman push quay.io/rhoai-genaiops/calendar-mcp-server:v3-multitenant

# Build frontend image (updated nginx config)
cd ../calendar-frontend
podman build -t quay.io/rhoai-genaiops/calendar-frontend:v2-multitenant .
podman push quay.io/rhoai-genaiops/calendar-frontend:v2-multitenant
```

### Step 3: Deploy with Helm

Update `values.yaml` or use command-line overrides:

```bash
cd helm

# Deploy with OAuth enabled
helm upgrade --install mcp-calendar . \
  --set oauth.enabled=true \
  --set calendarApi.image.tag=v3-multitenant \
  --set calendarMcpServer.image.tag=v3-multitenant \
  --set calendarFrontend.image.tag=v2-multitenant \
  --namespace calendar-system \
  --create-namespace
```

### Step 4: Verify Deployment

```bash
# Check pods are running
oc get pods -n calendar-system

# Get the frontend route
oc get route -n calendar-system

# Access the application
# Users will be redirected to OpenShift login
# Each user (user0-user49) will see only their own events
```

## User Experience

### Web Interface
1. User navigates to the calendar frontend URL
2. OAuth proxy redirects to OpenShift login
3. User logs in with credentials (e.g., user0/openshift)
4. User sees only their own calendar events
5. All create/update/delete operations are scoped to their user ID

### MCP Server Access

For AI agents to access a specific user's calendar:

```bash
# Deploy per-user MCP server instance (optional)
oc create deployment calendar-mcp-user0 \
  --image=quay.io/rhoai-genaiops/calendar-mcp-server:v3-multitenant \
  -n calendar-system

oc set env deployment/calendar-mcp-user0 \
  USER_ID=user0 \
  CALENDAR_API_BASE_URL=http://mcp-calendar-canopy-mcp-calendar-api:8000
```

Alternatively, configure the MCP server to extract user ID from headers when deployed behind OAuth proxy.

## Security Features

1. **Authentication**: OpenShift OAuth ensures only valid cluster users can access
2. **Authorization**: Each user can only see their own events
3. **Data Isolation**: Database queries are filtered by user_id
4. **No User Spoofing**: User ID is set by trusted OAuth proxy, not client
5. **TLS Encryption**: All traffic encrypted via OpenShift routes

## Integration with OpenShift Users

The application integrates seamlessly with your existing user provisioning:

```yaml
# From deploy-lab/toolings/templates/oauth/htpass-secret.yaml
users:
  - user0
  - user1
  - user2
  ... (user0-user49)
```

Each of these users will have their own isolated calendar when they log in.

## Development and Testing

### Local Testing Without OAuth

For development, you can test multi-tenancy without OAuth:

```bash
# Start API
cd calendar-api
export DATABASE_PATH=/tmp/test-calendar.db
uvicorn server:app --reload --port 8000

# Test with different users
curl -H "X-User-ID: user0" http://localhost:8000/schedules
curl -H "X-User-ID: user1" http://localhost:8000/schedules

# Create event for user0
curl -X POST http://localhost:8000/schedules \
  -H "X-User-ID: user0" \
  -H "Content-Type: application/json" \
  -d '{
    "sid": "test-1",
    "name": "User0 Meeting",
    "content": "Test event",
    "category": "Meeting",
    "level": 2,
    "status": 0.0,
    "creation_time": "2025-12-01 10:00:00",
    "start_time": "2025-12-01 14:00:00",
    "end_time": "2025-12-01 15:00:00"
  }'

# Verify isolation - user1 should NOT see user0's event
curl -H "X-User-ID: user1" http://localhost:8000/schedules
```

### Testing MCP Server

```bash
cd calendar-mcp-server
export USER_ID=user0
export CALENDAR_API_BASE_URL=http://localhost:8000
python server.py

# In another terminal, test with MCP Inspector
npx @modelcontextprotocol/inspector uv --directory . run python server.py
```

## Troubleshooting

### Users See Empty Calendar
- Check that OAuth proxy is properly injecting `X-Forwarded-User` header
- Verify nginx is passing headers to backend API
- Check API logs for user_id being received

### OAuth Redirect Loop
- Verify ServiceAccount has correct OAuth annotations
- Check Route TLS termination is set to `reencrypt` when OAuth is enabled
- Ensure OAuth cookie secret is properly mounted

### Database Errors
- Run migration script if upgrading from non-multi-tenant version
- Check PVC has write permissions
- Verify DATABASE_PATH environment variable is set correctly

### Users See Other Users' Events
- This indicates a security issue - check that:
  - API is extracting user_id from headers
  - Database queries include user_id filter
  - OAuth proxy is properly authenticating users

## Configuration Reference

### Helm Values

```yaml
# Enable OAuth proxy for multi-tenancy
oauth:
  enabled: true
  image:
    repository: openshift/oauth-proxy
    tag: latest

# API configuration
calendarApi:
  image:
    tag: v3-multitenant
  persistence:
    enabled: true
    size: 1Gi

# Frontend configuration
calendarFrontend:
  image:
    tag: v2-multitenant
  route:
    enabled: true
    tls:
      enabled: true

# MCP Server configuration
calendarMcpServer:
  image:
    tag: v3-multitenant
```

### Environment Variables

**Calendar API:**
- `DATABASE_PATH` - Path to SQLite database

**MCP Server:**
- `USER_ID` - User ID for scoping calendar operations
- `CALENDAR_API_BASE_URL` - Backend API URL
- `MCP_TRANSPORT` - Transport mode (stdio or sse)

## Additional Notes

- Each user's calendar is completely isolated
- No admin interface to view all users' calendars (can be added if needed)
- Database is shared but data is logically separated
- For production, consider PostgreSQL instead of SQLite for better concurrency
- OAuth proxy adds minimal latency (<50ms) to requests
