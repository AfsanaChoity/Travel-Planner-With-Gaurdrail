from langchain_core.messages import AIMessage
from state import TravelState
from .helpers import _llm_text, safe_print

def budget_agent(state: TravelState):

    safe_print("\n========== BUDGET AGENT INPUT ==========")
    safe_print("Trip Constraints:")
    safe_print(str(state.get("trip_constraints")))
    safe_print("\nFlight Results:")
    safe_print(str(state.get("flight_results")))
    safe_print("\nHotel Results:")
    safe_print(str(state.get("hotel_results")))
    safe_print("\nWeather Results:")
    safe_print(str(state.get("weather_results")))
    safe_print("=========================================\n")

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
    safe_print(result)
    print("=========================================\n")

    return {
        "budget_results": result,
        "messages": [AIMessage(content="Budget agent completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
