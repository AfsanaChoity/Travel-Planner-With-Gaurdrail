import time
import uuid

import streamlit as st
from langchain_core.messages import HumanMessage
from langgraph.types import Command

import config
from config import HMAC_SECRET_KEY, ENABLE_TIER1_GUARDRAIL, ENABLE_TOOL_HMAC_GUARD, SIMULATE_EVO_ATTACK
from gaurdrails import generate_signature
from graph import app


st.set_page_config(page_title="Real-World Multi-Agent Travel Planner", layout="wide")

st.title("Real-World Multi-Agent Travel Planner")

with st.sidebar:
    st.subheader("Session & Security")
    user_id = st.text_input("User ID", value="demo_user")
    
    st.markdown("---")
    st.caption("**Tier 1: User Input HMAC Guardrail**")
    enable_user_defense = st.checkbox(
        "Enable User Input Defense",
        value=ENABLE_TIER1_GUARDRAIL,
        help="Verifies HMAC signatures on user requests to prevent tampering & replay attacks.",
    )
    simulate_user_tamper = st.checkbox("Simulate Tampered Request Signature", value=False, help="Corrupts user signature to test Tier 1 rejection")
    simulate_user_expired = st.checkbox("Simulate Expired Timestamp (Replay)", value=False, help="Sends stale timestamp to test replay protection")

    st.markdown("---")
    st.caption("**Tier 1: Tool Return HMAC Defense (Evo-Attacker)**")
    enable_tool_defense = st.checkbox(
        "Enable Tool Output Defense",
        value=ENABLE_TOOL_HMAC_GUARD,
        help="Verifies HMAC signatures on raw tool returns (weather, hotel, flight) to prevent adversarial poisoning.",
    )
    simulate_evo = st.checkbox(
        "Simulate Evo-Attacker Tool Interception",
        value=SIMULATE_EVO_ATTACK,
        help="Simulates Evo-Attacker intercepting tool outputs and subtly altering payloads.",
    )

    st.markdown("---")
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
    if st.button("New Thread"):
        st.session_state.thread_id = f"{user_id}_{uuid.uuid4().hex[:8]}"
        st.session_state.pop("waiting_for_approval", None)
        st.session_state.pop("latest_result", None)
        st.rerun()

    st.caption(f"Thread: {st.session_state.thread_id}")


query = st.text_area(
    "Travel request",
    placeholder="Plan a 7-day Japan trip under 2 lakh BDT. I prefer budget hotels and no overnight flights.",
    height=110,
)

config_graph = {"configurable": {"thread_id": st.session_state.thread_id}}

col_act1, col_act2, _ = st.columns([2, 1, 4])
with col_act1:
    create_draft = st.button("Create Draft Plan", type="primary")
with col_act2:
    if st.button("Reload"):
        st.session_state.clear()
        st.components.v1.html("<script>window.parent.location.reload();</script>", height=0)
        st.rerun()

if create_draft:
    if not query.strip():
        st.warning("Enter a travel request first.")
    else:
        # 1. Update Tool Guardrail & Evo-Attacker settings
        config.ENABLE_TOOL_HMAC_GUARD = enable_tool_defense
        config.SIMULATE_EVO_ATTACK = simulate_evo

        # 2. Generate User Input HMAC signature & timestamp
        current_time = time.time()
        if simulate_user_expired:
            current_time -= 600  # 10 minutes in the past (> 300s allowed)

        signature = generate_signature(query, current_time, HMAC_SECRET_KEY)
        if simulate_user_tamper:
            signature = "tampered_signature_" + signature[18:]

        with st.spinner("Executing agents & monitoring Tier 1 Guardrails (Input + Tool)..."):
            result = app.invoke(
                {
                    "messages": [HumanMessage(content=query)],
                    "user_id": user_id,
                    "user_query": query,
                    "request_signature": signature,
                    "request_timestamp": current_time,
                    "enable_guardrail": enable_user_defense,
                    "is_authenticated": False,
                    "flight_results": "",
                    "hotel_results": "",
                    "weather_results": "",
                    "budget_results": "",
                    "itinerary": "",
                    "final_response": "",
                    "llm_calls": 0,
                },
                config=config_graph,
            )

        st.session_state.latest_result = result
        st.session_state.waiting_for_approval = "__interrupt__" in result


result = st.session_state.get("latest_result")

if result:
    if not result.get("is_authenticated", True):
        st.error(result.get("final_response") or "Request blocked by Tier 1 Security Guardrail.")
    elif "Security Halt" in str(result.get("itinerary", "")):
        st.error(result.get("itinerary"))
    elif not result.get("selected_agents"):
        st.info(result.get("final_response") or result.get("supervisor_reasoning", "Request rejected by input guardrail."))
    else:
        st.subheader("Supervisor Plan")
        st.write(result.get("supervisor_reasoning", ""))
        st.write("Selected agents:", result.get("selected_agents", []))

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Flight")
            st.markdown(result.get("flight_results", ""))
            st.subheader("Weather")
            st.markdown(result.get("weather_results", ""))
        with col2:
            st.subheader("Hotels")
            st.markdown(result.get("hotel_results", ""))
            st.subheader("Budget")
            st.markdown(result.get("budget_results", ""))

        st.subheader("Draft Itinerary")
        if "__interrupt__" in result:
            draft = result["__interrupt__"][0].value.get("draft_itinerary", "")
        else:
            draft = result.get("itinerary", "")
        st.markdown(draft)


if st.session_state.get("waiting_for_approval"):
    st.divider()
    st.subheader("Human Approval")

    approved = st.radio("Approve this draft?", ["Yes", "No, revise it"], horizontal=True)
    feedback = st.text_area("Feedback", disabled=approved == "Yes")

    if st.button("Submit Approval"):
        with st.spinner("Creating final response..."):
            final_result = app.invoke(
                Command(
                    resume={
                        "approved": approved == "Yes",
                        "feedback": feedback,
                    }
                ),
                config=config_graph,
            )
        st.session_state.latest_result = final_result
        st.session_state.waiting_for_approval = False
        st.rerun()


final_result = st.session_state.get("latest_result")
if final_result and final_result.get("selected_agents") and final_result.get("final_response"):
    st.divider()
    st.subheader("Final Travel Plan")
    st.markdown(final_result["final_response"])

