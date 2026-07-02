from __future__ import annotations

import os
from typing import Any, Dict, Optional

import requests

from oie.providers.base import ProviderClient


class SerpAPIAdapter(ProviderClient):
    provider_name = "serpapi"
    base_url = "https://serpapi.com/search.json"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config=config)

        cfg = self.config or {}
        api_key = cfg.get("api_key")
        api_key_env = cfg.get("api_key_env")

        if not api_key and api_key_env:
            api_key = os.getenv(api_key_env)

        self.api_key = api_key
        self.timeout = float(cfg.get("timeout_seconds", 20))

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def search_google_jobs(
        self,
        query: str,
        location: Optional[str] = None,
        num: int = 10,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing SerpAPI api_key")

        params: Dict[str, Any] = {
            "engine": "google_jobs",
            "q": query,
            "api_key": self.api_key,
            "num": num,
        }
        if location:
            params["location"] = location

        response = requests.get(
            self.base_url,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def search_google(
        self,
        query: str,
        num: int = 10,
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing SerpAPI api_key")

        params: Dict[str, Any] = {
            "engine": "google",
            "q": query,
            "api_key": self.api_key,
            "num": num,
        }

        response = requests.get(
            self.base_url,
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
