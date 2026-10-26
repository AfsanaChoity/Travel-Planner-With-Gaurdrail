import json
from langchain_core.messages import HumanMessage, SystemMessage
from config import get_llm

import sys

llm = get_llm()

def safe_print(*args, **kwargs):
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        safe_args = [
            str(arg).encode(encoding, errors="replace").decode(encoding, errors="replace")
            for arg in args
        ]
        print(*safe_args, **kwargs)

def _llm_text(system: str, prompt: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(content=system),
            HumanMessage(content=prompt),
        ]
    )
    return response.content

def _json_from_llm(text: str) -> dict:
    safe_print("\n========== RAW LLM RESPONSE ==========")
    safe_print(text)
    safe_print("======================================\n")

    start = text.index("{")
    end = text.rindex("}") + 1

    json_text = text[start:end]

    safe_print("\n========== EXTRACTED JSON ==========")
    safe_print(json_text)
    safe_print("====================================\n")

    return json.loads(json_text)
