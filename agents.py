import asyncio
import json
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.types import interrupt

from config import get_llm
from mcp_client import current_weather, forecast, list_airlines, list_airports, tavily_search
from state import TravelState

llm = get_llm()

def _llm_text(system: str, prompt: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
    )
    return response.content

def _json_from_llm(text: str) -> dict:
    print("\n========== RAW LLM RESPONSE ==========")
    print(text)
    print("======================================\n")

    start = text.index("{")
    end = text.rindex("}") + 1

    json_text = text[start:end]

    print("\n========== EXTRACTED JSON ==========")
    print(json_text)
    print("====================================\n")

    return json.loads(json_text)


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
    print(guardrail_raw)
    print("============================================\n")

    guardrail_result = _json_from_llm(guardrail_raw)

    print("\n========== GUARDRAIL PARSED RESPONSE ==========")
    print(json.dumps(guardrail_result, indent=2))
    print("================================================\n")

    if not guardrail_result.get("allowed", False):
        reason = guardrail_result.get(
            "reason",
            "Request rejected by input guardrail."
        )

        return {
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": reason,
            "final_response": reason,
            "messages": [
                AIMessage(content=f"Guardrail blocked request: {reason}")
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
    print(raw)
    print("======================================\n")

    parsed = _json_from_llm(raw)
   
    #parsed = json.loads(raw)
    
    print("\n========== PARSED JSON ==========")
    print(json.dumps(parsed, indent=2))
    print("=================================\n")
    
    '''
    At first glance they look the same, but they're not:

    raw → string returned by the LLM
    parsed → Python dictionary created from that string

    If you really want to demonstrate the difference, add:

    print(type(raw))
    print(type(parsed))
    Output:

    <class 'str'>
    <class 'dict'>
    Yes, you can get output from a string, but it's much harder and less reliable.
    '''
    
    selected = parsed["selected_agents"]    

    return {
        "selected_agents": selected,
        "trip_constraints": parsed["trip_constraints"],
        "supervisor_reasoning": parsed["reasoning"],
        "messages": [AIMessage(content="Supervisor created the agent plan.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }






# without guardrail

# def supervisor_agent(state: TravelState):
#     query = state["user_query"]
#     prompt = f"""
# You are the supervisor of a real-world multi-agent travel planning system.

# Decide which specialist agents are needed for this user request.

# Available agents:
# - flight_agent: use when flights, airports, airlines, routes, or airfare guidance are needed
# - hotel_agent: use when hotels, stays, neighborhoods, or accommodation are needed
# - weather_agent: use when weather, climate, season, packing, or forecast is useful
# - budget_agent: use when budget, affordability, cost, or price constraints are mentioned
# - itinerary_agent: almost always needed to produce the travel plan

# Return only JSON with this schema:
# {{
#   "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
#   "trip_constraints": {{
#     "destination": "",
#     "origin": "",
#     "duration": "",
#     "budget": "",
#     "travel_style": "",
#     "special_preferences": []
#   }},
#   "reasoning": ""
# }}

# User request:
# {query}
# """
    
#     raw = _llm_text(
#         "You route work to specialist agents. Return strict JSON only.",
#         prompt,
#     )

#     print("\n========== RAW LLM RESPONSE ==========")
#     print(raw)
#     print("======================================\n")

#     parsed = _json_from_llm(raw)
#     print("\n========== PARSED JSON ==========")
#     print(json.dumps(parsed, indent=2))
#     print("=================================\n")

#     print(type(raw))
#     print(type(parsed))

#     selected = parsed["selected_agents"]       

#     return {
#         "selected_agents": selected,
#         "trip_constraints": parsed["trip_constraints"],
#         "supervisor_reasoning": parsed["reasoning"],
#         "messages": [AIMessage(content="Supervisor created the agent plan.")],
#         "llm_calls": state.get("llm_calls", 0) + 1,
#     }



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

    print("\n========== AIRPORT MCP DATA ==========")
    print(airports)
    print("======================================\n")

    print("\n========== AIRLINE MCP DATA ==========")
    print(airlines)
    print("======================================\n")

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
    print(result)
    print("=========================================\n")

    return {
        "flight_results": result,
        "messages": [AIMessage(content="Flight agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }




def _format_hotel_results(raw_result: Any) -> str:
    text = ""
    if isinstance(raw_result, list) and len(raw_result) > 0:
        item = raw_result[0]
        if isinstance(item, dict) and "text" in item:
            text = item["text"]
        else:
            text = str(raw_result)
    elif isinstance(raw_result, str):
        text = raw_result
    else:
        text = str(raw_result)

    try:
        data = json.loads(text)
        results = data.get("results", [])
        if results:
            lines = []
            for r in results[:5]:
                title = r.get("title", "Hotel")
                content = r.get("content", "")[:250].strip()
                lines.append(f"- **{title}**: {content}")
            return "\n\n".join(lines)
    except Exception:
        pass

    return text[:2000]


def _format_weather_results(weather_data: Any, forecast_data: Any) -> str:
    def _extract_text(data):
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict) and "text" in data[0]:
            return data[0]["text"]
        return str(data)

    w_text = _extract_text(weather_data)
    f_text = _extract_text(forecast_data)

    try:
        w_json = json.loads(w_text)
        w_summary = f"{w_json.get('city')}: {w_json.get('temperature_c')}°C, {w_json.get('condition')}, humidity {w_json.get('humidity')}%"
    except Exception:
        w_summary = w_text[:500]

    try:
        f_json = json.loads(f_text)
        f_lines = [
            f"- {item.get('datetime')}: {item.get('temperature')}°C, {item.get('weather')}"
            for item in f_json.get("forecast", [])[:5]
        ]
        f_summary = "\n".join(f_lines)
    except Exception:
        f_summary = f_text[:800]

    return f"Current Weather:\n{w_summary}\n\nForecast:\n{f_summary}"


def hotel_agent(state: TravelState):
    query = f"Best hotels and areas to stay for: {state['user_query']}"

    print("\n========== HOTEL AGENT INPUT ==========")
    print(query)
    print("=======================================\n")

    result = asyncio.run(tavily_search(query))
    formatted_result = _format_hotel_results(result)

    print("\n========== HOTEL SEARCH RESULT ==========")
    print(formatted_result)
    print("=========================================\n")

    return {
        "hotel_results": formatted_result,
        "messages": [AIMessage(content="Hotel agent completed.")],
    }


def weather_agent(state: TravelState):
    constraints = state["trip_constraints"]
    city = constraints.get("destination", "")

    print("\n========== WEATHER AGENT INPUT ==========")
    print("City:", city)
    print("=========================================\n")

    weather_data = asyncio.run(current_weather(city))
    forecast_data = asyncio.run(forecast(city))

    result = _format_weather_results(weather_data, forecast_data)

    print("\n========== WEATHER AGENT OUTPUT ==========")
    print(result)
    print("==========================================\n")

    return {
        "weather_results": result,
        "messages": [AIMessage(content="Weather agent completed.")],
    }



def budget_agent(state: TravelState):

    print("\n========== BUDGET AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))
    print("\nFlight Results:")
    print(state.get("flight_results"))
    print("\nHotel Results:")
    print(state.get("hotel_results"))
    print("\nWeather Results:")
    print(state.get("weather_results"))
    print("=========================================\n")

    prompt = f"""
Analyze whether this trip plan is realistic for the user's budget.

User request:
{state['user_query']}

Constraints:
{state.get('trip_constraints', {})}

Flight results:
{str(state.get('flight_results', ''))[:2000]}

Hotel results:
{str(state.get('hotel_results', ''))[:2000]}

Weather results:
{str(state.get('weather_results', ''))[:1500]}

Return a concise budget assessment with:
1. estimated cost categories
2. risk areas
3. money-saving suggestions
4. whether the plan seems feasible
"""

    result = _llm_text(
        "You are a practical travel budget analyst.",
        prompt,
    )

    print("\n========== BUDGET AGENT OUTPUT ==========")
    print(result)
    print("=========================================\n")

    return {
        "budget_results": result,
        "messages": [AIMessage(content="Budget agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }



def itinerary_agent(state: TravelState):

    print("\n========== ITINERARY AGENT INPUT ==========")
    print("Trip Constraints:")
    print(state.get("trip_constraints"))

    print("\nFlight Results:")
    print(state.get("flight_results"))

    print("\nHotel Results:")
    print(state.get("hotel_results"))

    print("\nWeather Results:")
    print(state.get("weather_results"))

    print("\nBudget Results:")
    print(state.get("budget_results"))
    print("===========================================\n")

    prompt = f"""
Create a clear draft travel itinerary.

User request:
{state['user_query']}

Trip constraints:
{state.get('trip_constraints', {})}

Flight results:
{str(state.get('flight_results', ''))[:2000]}

Hotel results:
{str(state.get('hotel_results', ''))[:2000]}

Weather results:
{str(state.get('weather_results', ''))[:1500]}

Budget results:
{str(state.get('budget_results', ''))[:1500]}

Make the output structured, practical, and ready for human review.
"""

    result = _llm_text(
        "You are an expert itinerary planner.",
        prompt,
    )

    print("\n========== ITINERARY OUTPUT ==========")
    print(result)
    print("======================================\n")

    approval_request = f"""
Please review this draft travel plan.

{result}

Reply with approval or feedback.
"""

    return {
        "itinerary": result,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


def human_approval_agent(state: TravelState):
    feedback = interrupt(
        {
            "question": "Do you approve this itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "approval_request": state.get("approval_request", ""),
            "expected_response": {
                "approved": True,
                "feedback": "Optional feedback for revision",
            },
        }
    )

    approved = feedback["approved"]
    human_feedback = feedback["feedback"]

    return {
        "approved": approved,
        "human_feedback": human_feedback,
        "messages": [AIMessage(content="Human approval step completed.")],
    }



def final_response_agent(state: TravelState):

    print("\n========== FINAL AGENT INPUT ==========")
    print("Approved:", state.get("approved"))
    print("Feedback:", state.get("human_feedback"))
    print("=======================================\n")

    if state["approved"]:
        prompt = f"""
The human approved this draft itinerary.

Produce the final polished travel plan.

Draft itinerary:
{str(state.get('itinerary', ''))[:3000]}

Budget notes:
{str(state.get('budget_results', ''))[:1500]}
"""
    else:
        prompt = f"""
The human did not approve the draft.

Original user request:
{state['user_query']}

Draft itinerary:
{str(state.get('itinerary', ''))[:3000]}

Human feedback:
{state.get('human_feedback', '')}

Budget notes:
{str(state.get('budget_results', ''))[:1500]}
"""

    result = _llm_text(
        "You produce final user-ready travel plans.",
        prompt,
    )

    print("\n========== FINAL RESPONSE ==========")
    print(result)
    print("====================================\n")

    return {
        "final_response": result,
        "messages": [AIMessage(content=result)],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }