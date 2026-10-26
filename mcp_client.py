import os

from langchain_mcp_adapters.client import MultiServerMCPClient

import config
from config import (
    AVIATION_STACK_API_KEY,
    OPENWEATHER_API_KEY,
    TAVILY_API_KEY,
)
from gaurdrails.tier1_security import process_tool_guardrail

# Create MCP Client
client = MultiServerMCPClient(
    {
        # Remote MCP
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY}"
        },

        # Local MCP
        "aviationstack": {
            "transport": "stdio",
            "command": r"C:\Users\User\Desktop\Multi_Agent_System\Travel_Planner_Agent\aviationstack-mcp\.venv\Scripts\python.exe",
            "args": [
                "-m",
                "aviationstack_mcp",
                "mcp",
                "run"
            ],
            "env": {
                "AVIATION_STACK_API_KEY": AVIATION_STACK_API_KEY
            }
        }   ,

        # Custom MCP
        "weather": {
            "transport": "stdio",
            "command": r"C:\Users\User\Desktop\Multi_Agent_System\Travel_Planner_Agent\.venv\Scripts\python.exe",
            "args": [
                r"C:\Users\User\Desktop\Multi_Agent_System\Travel_Planner_Agent\weather_mcp_server.py"
            ],
            "env": {
                "OPENWEATHER_API_KEY": OPENWEATHER_API_KEY
            }
        }


    }
)


# Cache tools so we don't load them repeatedly
_tools_cache = None


async def get_tools():
    global _tools_cache

    if _tools_cache is None:
        try:
            _tools_cache = await client.get_tools()

        except Exception as e:
            print("\n========== FULL ERROR ==========")
            print(type(e))
            print(repr(e))

            if hasattr(e, "exceptions"):
                print("\nSUB EXCEPTIONS:")
                for i, sub in enumerate(e.exceptions):
                    print(f"\n--- Exception {i+1} ---")
                    print(type(sub))
                    print(repr(sub))

            raise

    return _tools_cache

async def call_tool(
    tool_name: str,
    args: dict = None,
    simulate_evo_attack: bool = None,
    enable_tool_guard: bool = None,
):
    tools = await get_tools()

    tool = next(
        (tool for tool in tools if tool.name == tool_name),
        None,
    )

    if tool is None:
        raise ValueError(f"Tool '{tool_name}' not found")

    raw_output = await tool.ainvoke(args or {})

    # Pass raw output through Tier-1 Tool Return HMAC Guardrail
    sim_attack = config.SIMULATE_EVO_ATTACK if simulate_evo_attack is None else simulate_evo_attack
    guard_active = config.ENABLE_TOOL_HMAC_GUARD if enable_tool_guard is None else enable_tool_guard

    return process_tool_guardrail(
        raw_tool_output=raw_output,
        tool_name=tool_name,
        simulate_attack=sim_attack,
        defense_enabled=guard_active,
    )


# ------------------------
# Tavily MCP Tools
# ------------------------



async def tavily_search(query: str):
    return await call_tool("tavily_search", {"query": query})


async def list_airports(search: str = "", limit: int = 10):
    return await call_tool("list_airports", {"search": search, "limit": limit, "offset": 0})


async def list_airlines(search: str = "", limit: int = 10):
    return await call_tool("list_airlines", {"search": search, "limit": limit, "offset": 0})


async def current_weather(city: str):
    return await call_tool("get_current_weather", {"city": city})


async def forecast(city: str):
    return await call_tool("get_forecast", {"city": city})
