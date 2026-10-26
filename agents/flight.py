import asyncio
from langchain_core.messages import AIMessage
from state import TravelState
from mcp_client import list_airports, list_airlines
from .helpers import _llm_text, safe_print

def flight_agent(state: TravelState):
    query = state["user_query"]
    constraints = state["trip_constraints"]
    destination = constraints["destination"]

    print("\n========== FLIGHT AGENT INPUT ==========")
    print("Query:", query)
    print("Constraints:", constraints)
    print("========================================\n")

    airports = asyncio.run(list_airports(destination, limit=10))
    airlines = asyncio.run(list_airlines("", limit=10))

    safe_print("\n========== AIRPORT MCP DATA ==========")
    safe_print(str(airports))
    safe_print("======================================\n")

    safe_print("\n========== AIRLINE MCP DATA ==========")
    safe_print(str(airlines))
    safe_print("======================================\n")

    if "TIER-1 SECURITY ALERT" in str(airports) or "TIER-1 SECURITY ALERT" in str(airlines):
        alert_text = (
            "[TIER-1 SECURITY ALERT: Flight tool output was intercepted and tampered with by external adversary. "
            "The payload was safely dropped by Tier-1 Tool HMAC Guardrail.]"
        )
        return {
            "flight_results": alert_text,
            "messages": [AIMessage(content="Flight tool blocked due to Tier-1 HMAC signature mismatch.")],
            "llm_calls": state.get("llm_calls", 0),
        }

    prompt = f"""
Create flight guidance for this trip.

User request:
{query}

Trip constraints:
{constraints}

Airport MCP data:
{str(airports)[:3000]}

Airline MCP data:
{str(airlines)[:3000]}

Include likely departure/arrival airports, relevant airlines,
estimated duration, fare range, peak season warning,
and booking advice.
"""

    result = _llm_text(
        "You are a flight planning specialist.",
        prompt,
    )

    print("\n========== FLIGHT AGENT OUTPUT ==========")
    safe_print(result)
    print("=========================================\n")

    return {
        "flight_results": result,
        "messages": [AIMessage(content="Flight agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
