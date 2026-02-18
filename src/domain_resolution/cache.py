import json
import os
from typing import Any, Dict, Optional

DEFAULT_PATH = "data/processed/domain_cache.json"

def load_cache(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_cache(cache: Dict[str, Any], path: str = DEFAULT_PATH) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

def get_cached_domain(company: str, path: str = DEFAULT_PATH) -> Optional[str]:
    cache = load_cache(path)
    return cache.get(company.strip().lower())

def set_cached_domain(company: str, domain: str, path: str = DEFAULT_PATH) -> None:
    cache = load_cache(path)
    cache[company.strip().lower()] = domain
    save_cache(cache, path)