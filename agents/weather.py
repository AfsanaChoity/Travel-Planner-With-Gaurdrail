import asyncio
import json
from typing import Any
from langchain_core.messages import AIMessage
from state import TravelState
from mcp_client import current_weather, forecast
from .helpers import safe_print

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
    safe_print(result)
    print("==========================================\n")

    return {
        "weather_results": result,
        "messages": [AIMessage(content="Weather agent completed.")],
    }
