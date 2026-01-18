#!/usr/bin/env python3
"""
Redwood Digital University Calendar MCP Server with OAuth 2.1 Authentication.
Supports both stdio (local) and SSE (remote) transports.

For STDIO mode: Runs locally, auth handled by the transport layer
For SSE mode: Full OAuth 2.1 with Keycloak token validation

Usage:
  Local/stdio mode (default):  python server.py
  Remote/SSE mode:             MCP_TRANSPORT=sse python server.py
"""

import logging
import os
from typing import Literal, Optional
from fastmcp import FastMCP
import aiohttp
from datetime import datetime, timedelta

# Configure logging first
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("calendar-mcp-server-auth")

# Also enable debug logging for token_verifier
logging.getLogger("token_verifier").setLevel(logging.DEBUG)

# OAuth imports (only used in SSE mode)
# Import local auth modules
try:
    from auth import get_protected_resource_metadata, get_www_authenticate_header, config as auth_config
    from token_verifier import IntrospectionTokenVerifier
    LOCAL_AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Local OAuth modules not available: {e}")
    LOCAL_AUTH_AVAILABLE = False
    auth_config = None
    IntrospectionTokenVerifier = None
    get_protected_resource_metadata = None
    get_www_authenticate_header = None

# Import FastMCP auth modules (required for SSE mode)
# Note: We only need the TokenVerifier protocol, which is already imported via token_verifier.py
try:
    from mcp.server.auth.provider import TokenVerifier
    FASTMCP_AUTH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"FastMCP auth modules not available: {e}")
    FASTMCP_AUTH_AVAILABLE = False
    TokenVerifier = None

# OAuth is available if both local and FastMCP auth modules are present
OAUTH_AVAILABLE = LOCAL_AUTH_AVAILABLE and FASTMCP_AUTH_AVAILABLE

# Configuration
MCP_TRANSPORT = os.getenv("MCP_TRANSPORT", "stdio")  # "stdio" or "sse"
MCP_PORT = int(os.getenv("MCP_PORT", "3000"))
MCP_HOST = os.getenv("MCP_HOST", "0.0.0.0")
CALENDAR_API_BASE_URL = os.getenv("CALENDAR_API_BASE_URL", "http://127.0.0.1:8000")

# Type definitions for enum validation
CategoryType = Literal["Lecture", "Lab", "Meeting", "Office Hours", "Assignment",
                       "Defense", "Workshop", "Study Group", "Seminar", "Grading", "Advising"]
StatusType = Literal["not_started", "in_progress", "completed"]
PeriodType = Literal["week", "month", "semester"]

# Create FastMCP server with OAuth support for SSE mode
# Note: For STDIO transport, OAuth is handled by the client
# For SSE transport, we initialize with token verification
if MCP_TRANSPORT.lower() == "sse" and OAUTH_AVAILABLE and auth_config:
    # SSE mode with full OAuth 2.1 protection
    # Create custom token verifier for Keycloak introspection
    token_verifier = IntrospectionTokenVerifier(
        introspection_endpoint=auth_config.introspection_endpoint,
        server_url=auth_config.server_url,
        client_id=auth_config.OAUTH_CLIENT_ID,
        client_secret=auth_config.OAUTH_CLIENT_SECRET,
        required_scope=auth_config.MCP_SCOPE,
    )

    # Pass the token verifier as the auth provider
    logger.info(f"✅ Token verifier created: {token_verifier}")
    logger.info(f"   Introspection endpoint: {auth_config.introspection_endpoint}")
    logger.info(f"   Server URL: {auth_config.server_url}")
    logger.info(f"   Required scope: {auth_config.MCP_SCOPE}")

    mcp = FastMCP(
        "calendar-mcp-server-auth",
        auth=token_verifier,
    )
    logger.info(f"✅ FastMCP initialized with auth provider")
else:
    # STDIO mode (local, auth handled by client)
    mcp = FastMCP("calendar-mcp-server-auth")

async def make_calendar_api_request(method: str, endpoint: str, data: dict = None):
    """Make a request to the Calendar API (internal, trusted service - no auth needed).
    Returns dict with 'success' and either 'data' or 'error'."""
    url = f"{CALENDAR_API_BASE_URL}{endpoint}"

    headers = {
        "Content-Type": "application/json"
    }

    try:
        async with aiohttp.ClientSession() as session:
            if method.upper() == "GET":
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        return {"success": True, "data": await response.json()}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API request failed with status {response.status}: {error_text}"}
            elif method.upper() == "POST":
                async with session.post(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        return {"success": True, "data": await response.json()}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API request failed with status {response.status}: {error_text}"}
            elif method.upper() == "PUT":
                async with session.put(url, headers=headers, json=data) as response:
                    if response.status == 200:
                        return {"success": True, "data": await response.json()}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API request failed with status {response.status}: {error_text}"}
            elif method.upper() == "DELETE":
                async with session.delete(url, headers=headers) as response:
                    if response.status == 200:
                        return {"success": True, "data": await response.json()}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"API request failed with status {response.status}: {error_text}"}
    except Exception as e:
        logger.error(f"Calendar API request failed: {e}")
        return {"success": False, "error": f"Calendar API request failed: {str(e)}"}

@mcp.tool()
async def get_all_events(
    category: Optional[CategoryType] = None,
    status: Optional[StatusType] = None
) -> str:
    """Get all events/schedules from the Redwood Digital University calendar.

    Args:
        category (str, optional): Filter by event category (optional)
        status (str, optional): Filter by completion status (optional)
    """
    result = await make_calendar_api_request("GET", "/schedules")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    events = result["data"] if isinstance(result["data"], list) else []

    # Apply filters
    if category:
        events = [e for e in events if e.get("category") == category]
    if status:
        status_map = {"not_started": 0.0, "in_progress": 0.5, "completed": 1.0}
        target_status = status_map.get(status)
        if target_status is not None:
            if target_status == 0.0:
                events = [e for e in events if e.get("status", 0) == 0.0]
            elif target_status == 0.5:
                events = [e for e in events if 0.0 < e.get("status", 0) < 1.0]
            else:
                events = [e for e in events if e.get("status", 0) == 1.0]

    summary = f"Found {len(events)} events in Redwood Digital University calendar\n\n"
    event_list = "\n".join([
        f"• {event['name']} ({event['category']})\n"
        f"  📅 {event['start_time']} - {event['end_time']}\n"
        f"  📋 {event.get('content', 'No description')}\n"
        f"  🎯 Priority: {['', 'Low', 'Medium', 'High'][event.get('level', 1)]}\n"
        f"  ✅ Status: {int(event.get('status', 0) * 100)}% complete\n"
        for event in events[:10]
    ])

    if len(events) > 10:
        event_list += f"\n... and {len(events) - 10} more events"

    return summary + event_list

@mcp.tool()
async def get_event(event_id: str) -> str:
    """Get detailed information about a specific event by ID.

    Args:
        event_id (str): Event ID to retrieve
    """
    result = await make_calendar_api_request("GET", f"/schedules/{event_id}")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    event = result["data"][0] if isinstance(result["data"], list) and result["data"] else result["data"]

    return f"""📚 Redwood Digital University Event Details:

🎓 **{event['name']}**
📋 **Category:** {event['category']}
📝 **Description:** {event.get('content', 'No description provided')}

📅 **Schedule:**
• Start: {event['start_time']}
• End: {event['end_time']}

🎯 **Priority:** {['', 'Low', 'Medium', 'High'][event.get('level', 1)]}
✅ **Status:** {int(event.get('status', 0) * 100)}% complete
🆔 **Event ID:** {event['sid']}
🕐 **Created:** {event.get('creation_time', 'Unknown')}"""

@mcp.tool()
async def create_event(
    name: str,
    category: CategoryType,
    level: int | str,
    start_time: str,
    end_time: str,
    content: str = ""
) -> str:
    """Create a new academic event in the calendar.

    Args:
        name (str): Event name/title (required)
        category (str): Event category (required) - must be one of: Lecture, Lab, Meeting, Office Hours, Assignment, Defense, Workshop, Study Group, Seminar, Grading, Advising
        level (int): Priority level (required) - must be 1 (Low), 2 (Medium), or 3 (High)
        start_time (str): Start time (required) - MUST be in YYYY-MM-DD HH:MM:SS format (e.g., "2024-12-05 14:00:00")
        end_time (str): End time (required) - MUST be in YYYY-MM-DD HH:MM:SS format (e.g., "2024-12-05 15:00:00")
        content (str, optional): Event description/details (optional)

    Note: New events are automatically created with status=0.0 (not started). Do NOT try to set the status parameter.
    """
    # Validate datetime format
    try:
        datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
        datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
    except ValueError as e:
        return f"❌ Error: Invalid datetime format. Please use YYYY-MM-DD HH:MM:SS format. Details: {str(e)}"

    timestamp = int(datetime.now().timestamp() * 1000)
    sid = f"mcp-event-{timestamp}"

    event_data = {
        "sid": sid,
        "name": name,
        "content": content,
        "category": category,
        "level": int(level),
        "status": 0.0,
        "creation_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "start_time": start_time,
        "end_time": end_time
    }

    result = await make_calendar_api_request("POST", "/schedules", event_data)

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    event = result["data"]
    return f"✅ Event created successfully!\n\n🎓 **{event['name']}**\n📋 Category: {event['category']}\n📅 Time: {event['start_time']} - {event['end_time']}\n🆔 Event ID: {event['sid']}"

@mcp.tool()
async def update_event(
    event_id: str,
    name: Optional[str] = None,
    content: Optional[str] = None,
    category: Optional[CategoryType] = None,
    level: Optional[Literal[1, 2, 3]] = None,
    status: Optional[float] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> str:
    """Update an existing event in the calendar.

    Args:
        event_id (str): Event ID to update
        name (str, optional): Event name/title (optional)
        content (str, optional): Event description/details (optional)
        category (str, optional): Event category (optional)
        level (int, optional): Priority level 1-3 (optional)
        status (float, optional): Completion status 0.0-1.0 (optional)
        start_time (str, optional): Start time in YYYY-MM-DD HH:MM:SS format (optional)
        end_time (str, optional): End time in YYYY-MM-DD HH:MM:SS format (optional)
    """
    # Get current event data first
    current_result = await make_calendar_api_request("GET", f"/schedules/{event_id}")

    if not current_result["success"]:
        return f"❌ Error: {current_result['error']}"

    current_event = current_result["data"]
    if isinstance(current_event, list) and current_event:
        current_event = current_event[0]

    # Prepare update data (merge with current data)
    update_data = {
        "sid": event_id,
        "name": name if name is not None else current_event["name"],
        "content": content if content is not None else current_event.get("content", ""),
        "category": category if category is not None else current_event["category"],
        "level": level if level is not None else current_event["level"],
        "status": status if status is not None else current_event.get("status", 0.0),
        "creation_time": current_event.get("creation_time"),
        "start_time": start_time if start_time is not None else current_event["start_time"],
        "end_time": end_time if end_time is not None else current_event["end_time"]
    }

    result = await make_calendar_api_request("PUT", f"/schedules/{event_id}", update_data)

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    event = result["data"]
    return f"✅ Event updated successfully!\n\n🎓 **{event['name']}**\n📋 Category: {event['category']}\n✅ Status: {int(event.get('status', 0) * 100)}% complete"

@mcp.tool()
async def delete_event(event_id: str) -> str:
    """Delete an event from the calendar.

    Args:
        event_id (str): Event ID to delete
    """
    result = await make_calendar_api_request("DELETE", f"/schedules/{event_id}")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    return f"🗑️ Event deleted successfully: {event_id}"

@mcp.tool()
async def search_events(query: str) -> str:
    """Search events by name or content.

    Args:
        query (str): Search query to match against event names and descriptions
    """
    result = await make_calendar_api_request("GET", "/schedules")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    all_events = result["data"]

    matching_events = []
    for event in all_events:
        if (query.lower() in event["name"].lower() or
            query.lower() in event.get("content", "").lower()):
            matching_events.append(event)

    summary = f"🔍 Search results for '{query}': {len(matching_events)} events found\n\n"
    event_list = "\n".join([
        f"• {event['name']} ({event['category']})\n  📅 {event['start_time']}"
        for event in matching_events[:10]
    ])

    return summary + (event_list if event_list else "No events match your search query.")

@mcp.tool()
async def get_upcoming_events(
    days: int = 7,
    category: Optional[CategoryType] = None
) -> str:
    """Get upcoming events within a specified number of days.

    Args:
        days (int): Number of days to look ahead (1-30, default: 7)
        category (str, optional): Filter by event category (optional)
    """
    result = await make_calendar_api_request("GET", "/schedules")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    all_events = result["data"]

    now = datetime.now()
    future_date = now + timedelta(days=days)

    upcoming_events = []
    for event in all_events:
        try:
            event_start = datetime.strptime(event["start_time"], "%Y-%m-%d %H:%M:%S")
            if now <= event_start <= future_date:
                if not category or event.get("category") == category:
                    upcoming_events.append(event)
        except:
            continue

    upcoming_events.sort(key=lambda x: x["start_time"])

    summary = f"📅 Upcoming events in next {days} day{'s' if days != 1 else ''}"
    if category:
        summary += f" (filtered by {category})"
    summary += f": {len(upcoming_events)} found\n\n"

    event_list = "\n".join([
        f"• {event['name']} ({event['category']})\n  📅 {event['start_time']}"
        for event in upcoming_events[:10]
    ])

    return summary + event_list

@mcp.tool()
async def get_events_by_date(date: str) -> str:
    """Get all events for a specific date.

    Args:
        date (str): Date in YYYY-MM-DD format
    """
    result = await make_calendar_api_request("GET", "/schedules")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    all_events = result["data"]

    date_events = []
    for event in all_events:
        try:
            event_date = event["start_time"].split()[0]  # Extract date part
            if event_date == date:
                date_events.append(event)
        except:
            continue

    summary = f"📅 Events on {date}: {len(date_events)} found\n\n"

    event_list = "\n".join([
        f"• {event['name']} ({event['category']})\n  🕐 {event['start_time'].split()[1]} - {event['end_time'].split()[1]}"
        for event in date_events
    ])

    return summary + (event_list if event_list else "No events scheduled for this date.")

@mcp.resource("oauth-protected-resource://metadata")
async def get_oauth_metadata() -> str:
    """Get OAuth Protected Resource Metadata (RFC 9728).

    Returns metadata about this OAuth-protected MCP server including:
    - Resource URL
    - Authorization server(s)
    - Supported scopes
    - Bearer token methods

    This endpoint is used by MCP clients to discover OAuth configuration.
    """
    if OAUTH_AVAILABLE and auth_config:
        metadata = get_protected_resource_metadata()
        import json
        return json.dumps(metadata, indent=2)
    else:
        return '{"error": "OAuth not available in this configuration"}'

@mcp.tool()
async def get_calendar_statistics(period: PeriodType = "month") -> str:
    """Get calendar statistics and overview.

    Args:
        period (str): Time period for statistics
    """
    result = await make_calendar_api_request("GET", "/schedules")

    if not result["success"]:
        return f"❌ Error: {result['error']}"

    all_events = result["data"]

    total_events = len(all_events)
    completed_events = len([e for e in all_events if e.get("status", 0) == 1.0])
    in_progress_events = len([e for e in all_events if 0 < e.get("status", 0) < 1.0])
    pending_events = len([e for e in all_events if e.get("status", 0) == 0.0])

    categories = {}
    for event in all_events:
        cat = event.get("category", "Unknown")
        categories[cat] = categories.get(cat, 0) + 1

    category_breakdown = "\n".join([
        f"• {cat}: {count} events"
        for cat, count in sorted(categories.items())
    ])

    completion_rate = (completed_events / total_events * 100) if total_events > 0 else 0

    return f"""📊 Redwood Digital University Calendar Statistics ({period})

📈 **Overview:**
• Total Events: {total_events}
• Completed: {completed_events} ({completion_rate:.1f}%)
• In Progress: {in_progress_events}
• Pending: {pending_events}

📋 **By Category:**
{category_breakdown}

🎯 **Academic Activity Level:** {'High' if total_events > 50 else 'Medium' if total_events > 20 else 'Low'}"""

if __name__ == "__main__":
    logger.info("🎓 Starting Redwood Digital University Calendar MCP Server")
    logger.info(f"📡 Calendar API URL: {CALENDAR_API_BASE_URL}")
    logger.info(f"🚀 Transport mode: {MCP_TRANSPORT}")

    if MCP_TRANSPORT.lower() == "sse":
        logger.info(f"🔐 OAuth 2.1 enabled for SSE transport")

        # Validate OAuth configuration for SSE mode
        if not OAUTH_AVAILABLE:
            logger.error("SSE mode requires OAuth modules (mcp.server.auth)")
            logger.error("   Install with: pip install 'mcp[auth]'")
            raise RuntimeError("OAuth modules not available for SSE mode")

        if not auth_config:
            logger.error("SSE mode requires auth configuration")
            raise RuntimeError("Auth configuration not available for SSE mode")

        # Validate client secret is configured
        if not auth_config.OAUTH_CLIENT_SECRET:
            logger.error("OAUTH_CLIENT_SECRET must be set for SSE mode")
            logger.error("   Set environment variable: export OAUTH_CLIENT_SECRET=your-secret-here")
            raise ValueError("OAUTH_CLIENT_SECRET is required for SSE mode")

        logger.info(f"🔑 Authorization Server: {auth_config.auth_base_url}")
        logger.info(f"🎯 Required Scope: {auth_config.MCP_SCOPE}")
        logger.info(f"📄 Metadata available via MCP resource: oauth-protected-resource://metadata")
        logger.info(f"🔄 Starting SSE server on {MCP_HOST}:{MCP_PORT}...")
        mcp.run(transport="sse", host=MCP_HOST, port=MCP_PORT)
    else:
        logger.info("🔄 Starting stdio server (local mode - auth handled by client)...")
        logger.info("ℹ️  In stdio mode, OAuth is managed by the MCP client (VS Code, etc.)")
        mcp.run(transport="stdio")
