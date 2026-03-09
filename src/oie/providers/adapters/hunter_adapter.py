from __future__ import annotations

from typing import Any, Dict

import requests

from oie.providers.base import ProviderClient


class HunterAdapter(ProviderClient):
    provider_name = "hunter"
    base_url = "https://api.hunter.io/v2/domain-search"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.api_key = (self.config or {}).get("api_key")
        self.timeout = float((self.config or {}).get("timeout_seconds", 20))

    def search_domain_contacts(self, domain: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Hunter api_key")
        if not domain:
            raise ValueError("Domain is required for Hunter search")

        response = requests.get(
            self.base_url,
            params={
                "domain": domain,
                "api_key": self.api_key,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
