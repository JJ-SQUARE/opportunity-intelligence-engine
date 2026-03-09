from __future__ import annotations

from typing import Any, Dict

import requests

from oie.providers.base import ProviderClient


class ApolloAdapter(ProviderClient):
    provider_name = "apollo"
    base_url = "https://api.apollo.io/api/v1/organizations/enrich"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        self.api_key = (self.config or {}).get("api_key")
        self.timeout = float((self.config or {}).get("timeout_seconds", 20))

    def enrich_company_by_domain(self, domain: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Apollo api_key")
        if not domain:
            raise ValueError("Domain is required for Apollo enrichment")

        response = requests.post(
            self.base_url,
            json={
                "api_key": self.api_key,
                "domain": domain,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
