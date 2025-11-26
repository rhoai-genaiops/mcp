# Redwood Digital University Calendar MCP Server

This directory contains a custom Model Context Protocol (MCP) server that integrates with the Redwood Digital University academic calendar system,
providing AI agents with comprehensive access to university scheduling, events, and academic activities.

## Overview

The Calendar MCP server (`server.py`) provides comprehensive academic calendar functionality including:
- **Event Management**: Create, read, update, and delete academic events
- **Schedule Queries**: Search and filter events by various criteria
- **Academic Planning**: View upcoming events and calendar statistics
- **University Integration**: Seamless integration with Redwood Digital University systems

## Transport Modes

The MCP server uses **FastMCP** and supports both transport modes with a single codebase:

### 1. **Local Mode (stdio)** - Default
Best for local development with AI clients like Claude Desktop.
- Uses stdin/stdout for JSON-RPC communication
- No network ports required
- Direct process-to-process communication

**Usage:**
```bash
python server.py
# Or explicitly:
MCP_TRANSPORT=stdio python server.py
```

### 2. **Remote Mode (HTTP/SSE)**
Best for deployment as a remote service in Kubernetes/OpenShift.
- Uses Server-Sent Events (SSE) for streaming
- Accessible over the network
- Suitable for production deployments

**Usage:**
```bash
MCP_TRANSPORT=sse python server.py
# With custom configuration:
MCP_TRANSPORT=sse MCP_PORT=8080 MCP_HOST=0.0.0.0 python server.py
```

**SSE Endpoint:**
- Connect to: `http://your-host:8080/sse`
- FastMCP handles all MCP protocol details automatically

## Key Features

- Integrates with the Calendar API via REST calls
- Supports all major calendar operations through 9 specialized tools
- Handles academic event categories (Lectures, Labs, Assignments, etc.)
- Provides detailed error handling and logging
- Optimized for university academic workflows

## Prerequisites

Before using the Calendar MCP server, make sure you have deployed the Calendar API:

```bash
# Start the Calendar API backend
cd calendar-api/src
uv run uvicorn server:app --reload --host 127.0.0.1 --port 8000
```

### Test locally

```bash
# Make the server executable
chmod +x server.py

# Set environment variables for local Calendar API
export CALENDAR_API_BASE_URL="http://127.0.0.1:8000"

# Make sure Calendar API is running first
cd ../calendar-api/src
uv run uvicorn server:app --reload --host 127.0.0.1 --port 8000 &
cd ../../calendar-mcp-server

# Run the MCP server directly (it will wait for JSON-RPC input)
python server.py

# Expected output:
# 🎓 Starting Redwood Digital University Calendar MCP Server
# 📡 Calendar API URL: http://127.0.0.1:8000
# ✅ Calendar API connection successful: {'app_name': 'calendar'}
# 🔄 MCP Server ready - waiting for JSON-RPC connections...
```

### Understanding MCP Server Logs

The MCP server now shows helpful logs:
- **🎓 Startup message** - Server is starting
- **📡 API URL** - Shows which Calendar API it's connecting to
- **✅ Connection test** - Confirms API is accessible
- **🔄 Ready status** - Server is waiting for AI agent connections
- **🔧 Tool calls** - Shows when AI agents use tools (when connected)

## Available Tools

The Calendar MCP server provides **9 tools** for AI agents:

### Core Calendar Operations
1. **get_all_events** - Get all events with optional filtering by category or status
2. **get_event** - Get detailed information about a specific event by ID
3. **create_event** - Create a new academic event in the calendar
4. **update_event** - Update an existing event (name, content, status, times, etc.)
5. **delete_event** - Remove an event from the calendar

### Advanced Queries
6. **get_upcoming_events** - Get upcoming events within specified days (1-30)
7. **get_events_by_date** - Get all events for a specific date (YYYY-MM-DD)
8. **search_events** - Search events by name or content
9. **get_calendar_statistics** - Get calendar overview and statistics by period

### Academic Event Categories
- **Lecture** - Class lectures and presentations
- **Lab** - Laboratory sessions and practical work
- **Meeting** - Faculty meetings and administrative sessions
- **Office Hours** - Student consultation times
- **Assignment** - Due dates and deadlines
- **Defense** - Thesis and project defenses
- **Workshop** - Academic workshops and training
- **Study Group** - Student study sessions
- **Seminar** - Research seminars and talks
- **Grading** - Assessment and grading periods
- **Advising** - Academic advising sessions

## Testing with AI Agents

Once deployed, you can test the Calendar MCP server with various queries:

### Sample Queries
- "Show me all upcoming lectures this week"
- "Create a new lab session for CS 301 on Friday at 2 PM"
- "What events are scheduled for tomorrow?"
- "Search for all machine learning related events"
- "Update the status of assignment due-001 to completed"
- "Show me calendar statistics for this month"
- "What are the office hours for Dr. Chen?"
- "Delete the canceled workshop event"

### Example API Calls
```bash
# Get all events
curl -X GET "http://127.0.0.1:8000/schedules"

# Get specific event
curl -X GET "http://127.0.0.1:8000/schedules/event-123"

# Create new event
curl -X POST "http://127.0.0.1:8000/schedules" \\
  -H "Content-Type: application/json" \\
  -d '{
    "sid": "new-event-123",
    "name": "CS 401: Advanced AI",
    "content": "Deep learning applications",
    "category": "Lecture",
    "level": 3,
    "status": 0.0,
    "creation_time": "2025-07-03 12:00:00",
    "start_time": "2025-07-04 10:00:00",
    "end_time": "2025-07-04 11:30:00"
  }'
```

## Configuration

The Calendar MCP server uses the following environment variables:

### Core Configuration
- `CALENDAR_API_BASE_URL` - Base URL for the Calendar API (default: "http://127.0.0.1:8000")

### Transport Configuration
- `MCP_TRANSPORT` - Transport mode: `stdio` (default) or `sse`
- `MCP_PORT` - Port for SSE mode (default: 8080)
- `MCP_HOST` - Host binding for SSE mode (default: "0.0.0.0")

### Examples

**Local development with Claude Desktop:**
```bash
export CALENDAR_API_BASE_URL="http://127.0.0.1:8000"
python server.py
```

**Remote deployment in Kubernetes:**
```bash
export CALENDAR_API_BASE_URL="http://calendar-api:8000"
export MCP_TRANSPORT=sse
export MCP_PORT=8080
python server.py
```

**Docker/Container Configuration:**
```bash
# Local mode (stdio)
docker run -e CALENDAR_API_BASE_URL="http://calendar-api:8000" \
           calendar-mcp-server:latest

# Remote mode (SSE) - for Kubernetes deployment
docker run -e CALENDAR_API_BASE_URL="http://calendar-api:8000" \
           -e MCP_TRANSPORT=sse \
           -p 8080:8080 \
           calendar-mcp-server:latest

# The same server.py handles both transports based on MCP_TRANSPORT env var
```