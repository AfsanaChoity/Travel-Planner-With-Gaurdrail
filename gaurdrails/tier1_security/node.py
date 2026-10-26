from langchain_core.messages import AIMessage
from config import HMAC_SECRET_KEY, ENABLE_TIER1_GUARDRAIL
from state import TravelState
from .hmac_guard import verify_signature


def hmac_guardrail_node(state: TravelState) -> dict:
    """
    Tier 1 Security Guardrail:
    Validates request authenticity, payload integrity, and timestamp freshness.
    Blocks tampered or unauthorized requests before any LLM or specialist agent runs.
    """
    guardrail_enabled = state.get("enable_guardrail", ENABLE_TIER1_GUARDRAIL)
    user_query = state.get("user_query", "")
    signature = state.get("request_signature", "")
    timestamp = state.get("request_timestamp", 0.0)

    print("\n========== TIER 1: HMAC GUARDRAIL ==========")
    print("Guardrail Enabled (Defense Mode):", guardrail_enabled)
    print("User Query:", user_query)
    print("Timestamp:", timestamp)
    print("Signature:", signature)
    print("============================================\n")

    # Research Evaluation Mode: If disabled, bypass check to measure baseline vulnerability
    if not guardrail_enabled:
        print("[RESEARCH BASELINE] Tier 1 Guardrail is DISABLED. Bypassing verification...\n")
        return {
            "is_authenticated": True,
            "messages": [AIMessage(content="[RESEARCH BASELINE] Tier 1 Guardrail disabled. Request passed to agents.")],
        }

    is_valid, reason = verify_signature(
        payload=user_query,
        signature=signature,
        timestamp=timestamp,
        secret_key=HMAC_SECRET_KEY,
    )

    if not is_valid:
        print(f"[ERROR] Tier 1 HMAC Verification Failed: {reason}")
        rejection_message = (
            "### Security Rejection (Tier 1 Guardrail)\n\n"
            f"**Reason:** {reason}\n\n"
            "*Request was blocked before invoking any agents or consuming LLM resources.*"
        )
        return {
            "is_authenticated": False,
            "selected_agents": [],
            "trip_constraints": {},
            "supervisor_reasoning": rejection_message,
            "final_response": rejection_message,
            "messages": [AIMessage(content=rejection_message)],
        }

    print("[SUCCESS] Tier 1 HMAC Verification Succeeded")
    return {
        "is_authenticated": True,
        "messages": [AIMessage(content="Tier 1 HMAC security check passed.")],
    }
