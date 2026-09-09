import os
from dotenv import load_dotenv
from agent.llm_agent import LLMAgent
from agent.fallback_agent import FallbackAgent

load_dotenv()

def get_agent():
    mode = os.getenv("AGENT_MODE", "fallback").lower()

    if mode == "llm":
        return LLMAgent()

    if mode == "fallback":
        return FallbackAgent()

    raise ValueError(
        f"Unsupported AGENT_MODE: {mode}. "
        "Use 'llm' or 'fallback'."
    )