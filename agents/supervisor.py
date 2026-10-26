import json
from langchain_core.messages import AIMessage
from state import TravelState
from .helpers import _llm_text, _json_from_llm, safe_print

# with guardrail
def supervisor_agent(state: TravelState):
    query = state["user_query"]
            
    # INPUT GUARDRAIL
    guardrail_prompt = f"""
    Determine whether the following request is a valid travel planning request.

    Return only JSON in this format:

    {{
        "allowed": true,
        "reason": ""
    }}

    User request:
    {query}
    """

    guardrail_raw = _llm_text(
        "You are an input validation guardrail. Return strict JSON only.",
        guardrail_prompt,
    )

    print("\n========== GUARDRAIL RAW RESPONSE ==========")
    safe_print(guardrail_raw)
    print("============================================\n")

    guardrail_result = _json_from_llm(guardrail_raw)

    print("\n========== GUARDRAIL PARSED RESPONSE ==========")
    safe_print(json.dumps(guardrail_result, indent=2))
    print("================================================\n")

    if not guardrail_result.get("allowed", False):
        reason = guardrail_result.get(
            "reason",
            "This request does not appear to be related to travel planning."
        )

        friendly_message = (
            "**Travel Planning Assistant**\n\n"
            "I'm specialized exclusively in helping you plan trips, find flights, recommend hotels, check weather, and build itineraries.\n\n"
            f"[INFO] *{reason}*\n\n"
            "*Please ask a travel-related request to get started!*"
        )

        return {
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": friendly_message,
            "final_response": friendly_message,
            "messages": [
                AIMessage(content=friendly_message)
            ],
            "llm_calls": state.get("llm_calls", 0) + 1,
        }


    # supervisor logic is starting from here:

    prompt = f"""
You are the supervisor of a real-world multi-agent travel planning system.

Decide which specialist agents are needed for this user request.

Available agents:
- flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed
- hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed
- weather_agent: use when weather, climate, season, packing, or forecast is useful
- budget_agent: use when budget, affordability, cost, or price constraints are mentioned
- itinerary_agent: almost always needed to produce the travel plan

Return only JSON with this schema:
{{
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {{
    "destination": "",
    "origin": "",
    "duration": "",
    "budget": "",
    "travel_style": "",
    "special_preferences": []
  }},
  "reasoning": ""
}}

User request:
{query}
"""

 
    raw = _llm_text(
        "You route work to specialist agents. Return strict JSON only.",
        prompt,
    )

    print("\n========== RAW LLM RESPONSE ==========")
    safe_print(raw)
    print("======================================\n")

    parsed = _json_from_llm(raw)
   
    print("\n========== PARSED JSON ==========")
    safe_print(json.dumps(parsed, indent=2))
    print("=================================\n")
    
    selected = parsed["selected_agents"]    

    return {
        "selected_agents": selected,
        "trip_constraints": parsed["trip_constraints"],
        "supervisor_reasoning": parsed["reasoning"],
        "messages": [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
