from langchain_core.messages import AIMessage
from state import TravelState
from .helpers import _llm_text, safe_print

def itinerary_agent(state: TravelState):

    safe_print("\n========== ITINERARY AGENT INPUT ==========")
    safe_print("Trip Constraints:")
    safe_print(str(state.get("trip_constraints")))

    safe_print("\nFlight Results:")
    safe_print(str(state.get("flight_results")))

    safe_print("\nHotel Results:")
    safe_print(str(state.get("hotel_results")))

    safe_print("\nWeather Results:")
    safe_print(str(state.get("weather_results")))

    safe_print("\nBudget Results:")
    safe_print(str(state.get("budget_results")))
    safe_print("===========================================\n")

    # Check if any tool return was blocked by Tier-1 Tool HMAC Guardrail
    compromised_tools = [
        k for k in ["flight_results", "hotel_results", "weather_results"]
        if "TIER-1 SECURITY ALERT" in str(state.get(k, ""))
    ]

    if compromised_tools:
        alert_msg = (
            "[SECURITY ALERT] **Security Halt (Tier-1 Tool Guardrail)**\n\n"
            f"An external adversary (**Evo-Attacker**) attempted to intercept and tamper with tool return data: `{', '.join(compromised_tools)}`.\n\n"
            "**Defense Status:** The **Tier-1 Tool Return HMAC Guardrail** successfully detected the cryptographic signature mismatch and dropped the poisoned payloads before they could corrupt the system.\n\n"
            "**Action Taken:** Itinerary generation was safely halted to prevent cascading failure and protect the user from fraudulent recommendations."
        )
        print("\n========== ITINERARY HALTED (SECURITY ATTACK DETECTED) ==========")
        safe_print(alert_msg)
        print("=================================================================\n")

        return {
            "itinerary": alert_msg,
            "approval_request": alert_msg,
            "final_response": alert_msg,
            "messages": [AIMessage(content=alert_msg)],
            "llm_calls": state.get("llm_calls", 0),
        }

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
    safe_print(result)
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
