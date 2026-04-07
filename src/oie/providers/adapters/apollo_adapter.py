from __future__ import annotations

import os
from typing import Any, Dict, List

import requests

from oie.providers.base import ProviderClient


class ApolloAdapter(ProviderClient):
    provider_name = "apollo"
    enrich_url = "https://api.apollo.io/api/v1/organizations/enrich"
    people_search_url = "https://api.apollo.io/api/v1/mixed_people/search"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        cfg = self.config or {}
        api_key_env = cfg.get("api_key_env", "APOLLO_API_KEY")
        self.api_key = cfg.get("api_key") or os.getenv(api_key_env)
        self.timeout = float(cfg.get("timeout_seconds", 20))

    def enrich_company_by_domain(self, domain: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Apollo api_key")
        if not domain:
            raise ValueError("Domain is required for Apollo enrichment")

        response = requests.post(
            self.enrich_url,
            json={
                "api_key": self.api_key,
                "domain": domain,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def search_people_by_domain_and_titles(self, domain: str, titles: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Apollo api_key")
        if not domain:
            raise ValueError("Domain is required for Apollo people search")

        response = requests.post(
            self.people_search_url,
            json={
                "api_key": self.api_key,
                "q_organization_domains": [domain],
                "person_titles": titles,
                "page": 1,
                "per_page": 10,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()
