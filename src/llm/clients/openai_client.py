import json
import os
from typing import Any, Dict

from openai import OpenAI


def openai_json(model: str, prompt: str, temperature: float = 0.2) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY env var")

    client = OpenAI(api_key=api_key)

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=temperature,
    )

    content = resp.choices[0].message.content.strip()
    return json.loads(content)