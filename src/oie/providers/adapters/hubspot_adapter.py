from __future__ import annotations

import os
from typing import Any, Dict

import requests
from requests import Response

from oie.providers.base import ProviderClient


class HubSpotAdapter(ProviderClient):
    provider_name = "hubspot"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        cfg = self.config or {}
        api_key_env = cfg.get("api_key_env", "HUBSPOT_BEARER_TOKEN")

        raw_api_key = cfg.get("api_key")
        if raw_api_key is None:
            raw_api_key = os.getenv(api_key_env)

        # Explicit: this is a Bearer token (Private App Token)
        self.api_key = str(raw_api_key or "").strip()
        self.base_url = str(cfg.get("base_url") or "https://api.hubapi.com").rstrip("/")
        self.timeout = float(cfg.get("timeout_seconds", 20))
        self.api_key_env = api_key_env

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "accept": "application/json",
        }
        if not self.api_key:
            raise ValueError(
                f"Missing HubSpot Bearer token. Set {self.api_key_env} in .env"
            )

        headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(f"Missing HubSpot Bearer token. Set {self.api_key_env} in .env")

        response = requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _post_raw(self, path: str, payload: Dict[str, Any]) -> Response:
        if not self.api_key:
            raise ValueError(f"Missing HubSpot Bearer token. Set {self.api_key_env} in .env")

        return requests.post(
            f"{self.base_url}{path}",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )

    def _search_contact_by_email(self, email: str) -> Dict[str, Any] | None:
        normalized_email = str(email or "").strip().lower()
        if not normalized_email:
            return None

        response = self._post_raw(
            "/crm/v3/objects/contacts/search",
            {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "email",
                                "operator": "EQ",
                                "value": normalized_email,
                            }
                        ]
                    }
                ],
                "properties": ["email", "firstname", "lastname", "jobtitle"],
                "limit": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or []
        if not results:
            return None
        return results[0]

    def search_contact_by_email(self, email: str) -> Dict[str, Any] | None:
        return self._search_contact_by_email(email)

    def search_company_by_domain(self, domain: str) -> Dict[str, Any] | None:
        normalized_domain = str(domain or "").strip().lower()
        if not normalized_domain:
            return None

        response = self._post_raw(
            "/crm/v3/objects/companies/search",
            {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "domain",
                                "operator": "EQ",
                                "value": normalized_domain,
                            }
                        ]
                    }
                ],
                "properties": ["name", "domain", "website"],
                "limit": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or []
        if not results:
            return None
        return results[0]

    def search_task_by_subject(self, subject: str) -> Dict[str, Any] | None:
        normalized_subject = str(subject or "").strip()
        if not normalized_subject:
            return None

        response = self._post_raw(
            "/crm/v3/objects/tasks/search",
            {
                "filterGroups": [
                    {
                        "filters": [
                            {
                                "propertyName": "hs_task_subject",
                                "operator": "EQ",
                                "value": normalized_subject,
                            }
                        ]
                    }
                ],
                "properties": ["hs_task_subject", "hs_task_status", "hs_timestamp"],
                "limit": 1,
            },
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results") or []
        if not results:
            return None
        return results[0]

    def create_company(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/crm/v3/objects/companies", payload)

    def create_contact(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        properties = payload.get("properties", {}) or {}
        email = str(properties.get("email") or "").strip().lower()

        response = self._post_raw("/crm/v3/objects/contacts", payload)
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError:
            if response.status_code != 409 or not email:
                raise

            existing = self._search_contact_by_email(email)
            if existing:
                return existing
            raise

    def create_task(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/crm/v3/objects/tasks", payload)

    def create_note(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._post("/crm/v3/objects/notes", payload)

    def create_association(
        self,
        from_object_type: str,
        from_object_id: str,
        to_object_type: str,
        to_object_id: str,
        association_type: str = "default",
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError(f"Missing HubSpot Bearer token. Set {self.api_key_env} in .env")

        if association_type != "default":
            raise ValueError(
                f"Unsupported HubSpot association_type={association_type}. Only 'default' is supported."
            )

        path = (
            f"/crm/v4/objects/{from_object_type}/{from_object_id}"
            f"/associations/default/{to_object_type}/{to_object_id}"
        )

        response = requests.put(
            f"{self.base_url}{path}",
            headers=self._headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        return {"status": "associated"}
