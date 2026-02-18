from typing import Any, Dict

from llm.clients.openai_client import openai_json
from llm.clients.gemini_client import gemini_json


def llm_json(provider: str, model: str, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
    provider = (provider or "").lower().strip()

    if provider == "openai":
        return openai_json(model=model, prompt=prompt, temperature=temperature)

    if provider == "gemini":
        return gemini_json(model=model, prompt=prompt, temperature=temperature)

    raise ValueError(f"Unsupported LLM provider: {provider}")