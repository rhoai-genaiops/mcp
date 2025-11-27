#!/usr/bin/env python3
"""
Simple MCP client for testing the Calendar MCP Server over SSE.
"""

import asyncio
import json
import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client


async def test_calendar_mcp():
    """Test the Calendar MCP server."""

    # Server URL - change this to your service URL
    server_url = "http://mcp-calendar-canopy-mcp-calendar-mcp-server.ai501.svc.cluster.local:8080/sse"

    print(f"🔗 Connecting to MCP server at {server_url}")

    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the session
            await session.initialize()
            print("✅ Connected and initialized!")

            # List available tools
            print("\n📋 Listing available tools...")
            tools = await session.list_tools()
            print(f"Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")

            # Test 1: Get all events
            print("\n🗓️  Test 1: Getting all events...")
            result = await session.call_tool("get_all_events", arguments={})
            print("Result:")
            for content in result.content:
                print(content.text)

            # Test 2: Search for lectures
            print("\n🔍 Test 2: Searching for 'lecture'...")
            result = await session.call_tool("search_events", arguments={"query": "lecture"})
            print("Result:")
            for content in result.content:
                print(content.text)

            # Test 3: Get upcoming events
            print("\n📅 Test 3: Getting upcoming events (next 7 days)...")
            result = await session.call_tool("get_upcoming_events", arguments={"days": 7})
            print("Result:")
            for content in result.content:
                print(content.text)

            # Test 4: Get calendar statistics
            print("\n📊 Test 4: Getting calendar statistics...")
            result = await session.call_tool("get_calendar_statistics", arguments={"period": "month"})
            print("Result:")
            for content in result.content:
                print(content.text)

            # Test 5: Create a new event
            print("\n➕ Test 5: Creating a new event...")
            result = await session.call_tool(
                "create_event",
                arguments={
                    "name": "Test MCP Event",
                    "category": "Meeting",
                    "level": 2,
                    "start_time": "2025-12-01 14:00:00",
                    "end_time": "2025-12-01 15:00:00",
                    "content": "Testing MCP server integration"
                }
            )
            print("Result:")
            for content in result.content:
                print(content.text)

            print("\n✅ All tests completed successfully!")


async def interactive_mode():
    """Interactive mode to manually call tools."""

    server_url = "http://mcp-calendar-canopy-mcp-calendar-mcp-server.ai501.svc.cluster.local:8080/sse"

    print(f"🔗 Connecting to MCP server at {server_url}")

    async with sse_client(server_url) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("✅ Connected!\n")

            # List tools
            tools = await session.list_tools()
            print("Available tools:")
            for i, tool in enumerate(tools.tools, 1):
                print(f"{i}. {tool.name}")

            print("\nInteractive MCP Client")
            print("Commands:")
            print("  list - List all events")
            print("  search <query> - Search events")
            print("  upcoming [days] - Get upcoming events")
            print("  stats - Get calendar statistics")
            print("  quit - Exit")

            while True:
                try:
                    cmd = input("\n> ").strip().split()
                    if not cmd:
                        continue

                    if cmd[0] == "quit":
                        break

                    elif cmd[0] == "list":
                        result = await session.call_tool("get_all_events", arguments={})
                        for content in result.content:
                            print(content.text)

                    elif cmd[0] == "search" and len(cmd) > 1:
                        query = " ".join(cmd[1:])
                        result = await session.call_tool("search_events", arguments={"query": query})
                        for content in result.content:
                            print(content.text)

                    elif cmd[0] == "upcoming":
                        days = int(cmd[1]) if len(cmd) > 1 else 7
                        result = await session.call_tool("get_upcoming_events", arguments={"days": days})
                        for content in result.content:
                            print(content.text)

                    elif cmd[0] == "stats":
                        result = await session.call_tool("get_calendar_statistics", arguments={})
                        for content in result.content:
                            print(content.text)

                    else:
                        print("Unknown command")

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")

            print("\n👋 Goodbye!")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "interactive":
        asyncio.run(interactive_mode())
    else:
        asyncio.run(test_calendar_mcp())
