from __future__ import annotations

from typing import Any, Dict

from oie.providers.base import ProviderClient


class OpenAIAdapter(ProviderClient):
    provider_name = "openai"

    def classify_company(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Adapter inicial.
        En la siguiente iteración conectaremos aquí el cliente real de LLM.
        """
        company_name = company_payload.get("company_display") or company_payload.get("company") or "unknown"

        return {
            "company_name": company_name,
            "classification": "unknown",
            "confidence": 0.0,
            "provider": self.provider_name,
            "mode": "stub",
        }
