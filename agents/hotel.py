import asyncio
import json
from typing import Any
from langchain_core.messages import AIMessage
from state import TravelState
from mcp_client import tavily_search
from .helpers import safe_print

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

def hotel_agent(state: TravelState):
    query = f"Best hotels and areas to stay for: {state['user_query']}"

    print("\n========== HOTEL AGENT INPUT ==========")
    print(query)
    print("=======================================\n")

    result = asyncio.run(tavily_search(query))
    formatted_result = _format_hotel_results(result)

    print("\n========== HOTEL SEARCH RESULT ==========")
    safe_print(formatted_result)
    print("=========================================\n")

    return {
        "hotel_results": formatted_result,
        "messages": [AIMessage(content="Hotel agent completed.")],
    }
