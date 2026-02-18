import json
import os
from typing import Any, Dict, Optional

from openai import OpenAI

CACHE_PATH = "data/processed/company_ai_cache.json"

def _load_cache() -> Dict[str, Any]:
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def _save_cache(cache: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def classify_company_with_openai(
    company: str,
    context: Dict[str, Any],
    model: str = "gpt-4.1-mini",
) -> Dict[str, Any]:
    """
    context: aggregated data for a company (titles, locations, sample descriptions, etc.)
    Returns structured fields for sales intelligence.
    Uses local JSON cache keyed by company name.
    """
    cache = _load_cache()
    key = company.strip().lower()
    if key in cache:
        return cache[key]

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Missing OPENAI_API_KEY env var")

    titles = context.get("titles", [])[:8]
    locations = context.get("locations", [])[:8]
    sample_desc = (context.get("sample_description") or "")[:1500]
    via = context.get("via_sources", [])[:5]
    domain_guess = context.get("domain_guess")

    prompt = f"""
You are a B2B sales intelligence assistant for a software consultancy selling staff augmentation (nearshore).
Given a company hiring signal, infer:
- company_type: one of [product_company, consulting, staffing_agency, marketplace, unknown]
- industry: short label (e.g., fintech, healthcare, ecommerce, energy, SaaS, logistics, gov, etc.)
- vendor_acceptance_probability: integer 0-100 (likelihood they will accept an external vendor / nearshore augmentation)
- nearshore_friendly: boolean
- remote_friendly: boolean
- notes: short bullets (max 5) explaining the reasoning based only on provided context (no web browsing)

Context:
Company: {company}
Domain guess: {domain_guess}
Job titles: {titles}
Locations: {locations}
Sources (via): {via}
Sample description snippet:
{sample_desc}
"""

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "Return ONLY valid JSON. No markdown."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )

    content = resp.choices[0].message.content.strip()

    try:
        data = json.loads(content)
    except Exception:
        # fallback minimal if model returns unexpected format
        data = {
            "company_type": "unknown",
            "industry": "unknown",
            "vendor_acceptance_probability": 50,
            "nearshore_friendly": None,
            "remote_friendly": None,
            "notes": ["AI response could not be parsed as JSON."],
            "raw": content,
        }

    cache[key] = data
    _save_cache(cache)
    return data