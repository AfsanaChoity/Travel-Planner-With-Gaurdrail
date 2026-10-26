from langchain_core.messages import AIMessage
from state import TravelState
from .helpers import _llm_text, safe_print

def final_response_agent(state: TravelState):

    print("\n========== FINAL AGENT INPUT ==========")
    print("Approved:", state.get("approved"))
    print("Feedback:", state.get("human_feedback"))
    print("=======================================\n")

    if "Security Halt" in state.get("final_response", ""):
        return {
            "final_response": state["final_response"],
            "messages": [AIMessage(content=state["final_response"])],
        }

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
    safe_print(result)
    print("====================================\n")

    return {
        "final_response": result,
        "messages": [AIMessage(content=result)],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }
