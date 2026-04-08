from __future__ import annotations

import os
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests

from oie.providers.base import ProviderClient


class ApolloAdapter(ProviderClient):
    provider_name = "apollo"
    enrich_url = "https://api.apollo.io/api/v1/organizations/enrich"
    people_search_url = "https://api.apollo.io/api/v1/mixed_people/api_search"

    def __init__(self, config: Dict[str, Any] | None = None) -> None:
        super().__init__(config=config)
        cfg = self.config or {}
        api_key_env = cfg.get("api_key_env", "APOLLO_API_KEY")
        raw_api_key = cfg.get("api_key")
        if raw_api_key is None:
            raw_api_key = os.getenv(api_key_env)

        self.api_key = str(raw_api_key or "").strip()
        self.timeout = float(cfg.get("timeout_seconds", 20))
        self.api_key_env = api_key_env

    def _headers(self) -> Dict[str, str]:
        headers = {
            "accept": "application/json",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key
        return headers

    def _normalize_domain(self, domain: str) -> str:
        value = (domain or "").strip().lower()
        if not value:
            return ""

        if value.startswith("@"):
            value = value[1:]

        if "://" not in value:
            value = f"https://{value}"

        parsed = urlparse(value)
        host = (parsed.netloc or parsed.path or "").strip().lower()

        if host.startswith("www."):
            host = host[4:]

        host = host.split("/", 1)[0].strip(".")
        return host

    def _sanitized_auth_debug(self, headers: Dict[str, str]) -> Dict[str, Any]:
        key = self.api_key or ""
        return {
            "api_key_env": self.api_key_env,
            "api_key_present": bool(key),
            "api_key_length": len(key),
            "api_key_prefix": key[:4] if len(key) >= 4 else key,
            "api_key_suffix": key[-4:] if len(key) >= 4 else key,
            "header_names": sorted(list(headers.keys())),
            "has_x_api_key_header": "X-Api-Key" in headers,
        }

    def _raise_with_apollo_context(
        self,
        exc: requests.exceptions.HTTPError,
        *,
        operation: str,
        domain: str,
        headers: Dict[str, str],
        request_kind: str,
        payload_shape: Dict[str, Any] | None = None,
    ) -> None:
        response = getattr(exc, "response", None)
        status_code = getattr(response, "status_code", None)

        prepared_headers = {}
        prepared_url = None
        if response is not None and getattr(response, "request", None) is not None:
            prepared = response.request
            prepared_headers = dict(getattr(prepared, "headers", {}) or {})
            prepared_url = getattr(prepared, "url", None)

        context = {
            "operation": operation,
            "request_kind": request_kind,
            "domain": domain,
            "status_code": status_code,
            "adapter_auth_debug": self._sanitized_auth_debug(headers),
            "prepared_header_names": sorted(list(prepared_headers.keys())),
            "prepared_has_x_api_key_header": "X-Api-Key" in prepared_headers,
            "prepared_url": prepared_url,
            "payload_shape": payload_shape or {},
        }

        raise requests.exceptions.HTTPError(
            f"{exc} | apollo_debug={context}",
            response=response,
        ) from exc

    def enrich_company_by_domain(self, domain: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Apollo api_key")

        normalized_domain = self._normalize_domain(domain)
        if not normalized_domain:
            raise ValueError("Domain is required for Apollo enrichment")

        headers = self._headers()
        response = requests.get(
            self.enrich_url,
            params={
                "domain": normalized_domain,
            },
            headers=headers,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            self._raise_with_apollo_context(
                exc,
                operation="enrich_company_by_domain",
                domain=normalized_domain,
                headers=headers,
                request_kind="GET",
                payload_shape={"params_keys": ["domain"]},
            )
        return response.json()

    def search_people_by_domain_and_titles(self, domain: str, titles: List[str]) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("Missing Apollo api_key")

        normalized_domain = self._normalize_domain(domain)
        if not normalized_domain:
            raise ValueError("Domain is required for Apollo people search")

        cleaned_titles = [str(title).strip() for title in (titles or []) if str(title).strip()]

        headers = {
            **self._headers(),
            "Content-Type": "application/json",
        }
        json_payload = {
            "q_organization_domains_list": [normalized_domain],
            "person_titles": cleaned_titles,
            "page": 1,
            "per_page": 10,
        }

        response = requests.post(
            self.people_search_url,
            json=json_payload,
            headers=headers,
            timeout=self.timeout,
        )
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            self._raise_with_apollo_context(
                exc,
                operation="search_people_by_domain_and_titles",
                domain=normalized_domain,
                headers=headers,
                request_kind="POST",
                payload_shape={
                    "json_keys": sorted(list(json_payload.keys())),
                    "titles_count": len(cleaned_titles),
                },
            )
        return response.json()
