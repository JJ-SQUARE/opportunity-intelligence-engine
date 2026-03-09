# src/enrichment/router.py
from typing import Any, Dict, List

from enrichment.providers.hunter import hunter_domain_search, extract_leads_from_hunter_response
from domain_resolution.google_serpapi import is_blocked_domain


def enrich_company(company_obj: Dict[str, Any], enrichment_cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    providers = enrichment_cfg.get("providers", {})
    hunter_cfg = providers.get("hunter", {})
    leads: List[Dict[str, Any]] = []

    domain = company_obj.get("resolved_domain") or company_obj.get("domain_guess")
    domain = domain.strip().lower() if domain else None
    if domain and is_blocked_domain(domain):
        return []

    if hunter_cfg.get("enabled", False):
        try:
            resp = hunter_domain_search(
                domain=domain,
                api_key_env=hunter_cfg.get("api_key_env", "HUNTER_API_KEY"),
                sleep_s=float(hunter_cfg.get("rate_limit_sleep_s", 1.0)),
                limit=10,
            )
            leads.extend(extract_leads_from_hunter_response(company_obj.get("company"), domain, resp))
        except Exception as e:
            print(
                f"[WARN] Hunter enrichment failed for domain='{domain}' company='{company_obj.get('company')}': {type(e).__name__}: {e}")

    return leads