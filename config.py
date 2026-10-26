import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATION_STACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
DATABASE_URL = os.getenv("DATABASE_URL")
HMAC_SECRET_KEY = os.getenv("HMAC_SECRET_KEY")
ENABLE_TIER1_GUARDRAIL = os.getenv("ENABLE_TIER1_GUARDRAIL", "true").lower() == "true"

def get_llm():
    return ChatGroq(model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"))
