import json
import os
from typing import Any, Dict, Optional

from llm.router import llm_json


def _load_cache(cache_path: str) -> Dict[str, Any]:
    if os.path.exists(cache_path):
        with open(cache_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def _save_cache(cache_path: str, cache: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def classify_company_with_llm(
    company: str,
    context: Dict[str, Any],
    provider: str,
    model: str,
    temperature: float = 0.2,
    cache_path: str = "data/processed/company_ai_cache.json",
) -> Dict[str, Any]:
    """
    Company-level AI classifier using a pluggable LLM provider (OpenAI/Gemini).
    Uses a JSON cache keyed by company name.
    Returns a dict with:
      - company_type
      - industry
      - vendor_acceptance_probability
      - nearshore_friendly
      - remote_friendly
      - notes
    """
    cache = _load_cache(cache_path)
    key = company.strip().lower()

    if key in cache:
        return cache[key]

    titles = context.get("titles", [])[:8]
    locations = context.get("locations", [])[:8]
    sample_desc = (context.get("sample_description") or "")[:1500]
    via = context.get("via_sources", [])[:5]
    domain_guess = context.get("domain_guess")

    prompt = f"""
Return ONLY valid JSON. No markdown.

You are a B2B sales intelligence assistant for a software consultancy selling staff augmentation (nearshore).
Given the hiring signals below, infer:

- company_type: one of ["product_company","consulting","staffing_agency","marketplace","unknown"]
- industry: short label (e.g., "fintech", "healthcare", "ecommerce", "energy", "SaaS", "logistics", "gov", etc.)
- vendor_acceptance_probability: integer 0-100
- nearshore_friendly: boolean
- remote_friendly: boolean
- notes: array of short bullets (max 5). Use ONLY provided context; do NOT browse.

Context:
Company: {company}
Domain guess: {domain_guess}
Job titles: {titles}
Locations: {locations}
Sources (via): {via}
Sample description snippet:
{sample_desc}
"""

    try:
        data = llm_json(
            provider=provider,
            model=model,
            prompt=prompt,
            temperature=temperature,
        )
    except Exception as e:
        data = {
            "company_type": "unknown",
            "industry": "unknown",
            "vendor_acceptance_probability": 50,
            "nearshore_friendly": None,
            "remote_friendly": None,
            "notes": [f"LLM call failed: {type(e).__name__}"],
        }

    # Guardrails por si el modelo regresa algo raro
    if not isinstance(data, dict):
        data = {
            "company_type": "unknown",
            "industry": "unknown",
            "vendor_acceptance_probability": 50,
            "nearshore_friendly": None,
            "remote_friendly": None,
            "notes": ["LLM returned non-dict JSON."],
            "raw": data,
        }

    cache[key] = data
    _save_cache(cache_path, cache)
    return data