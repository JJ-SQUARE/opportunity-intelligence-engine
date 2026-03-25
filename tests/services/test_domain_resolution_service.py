from oie.orchestration.run_context import RunContext
from oie.services.domain_resolution_service import DomainResolutionService


class _FakeSerpAPISearchService:
    def __init__(self, payload):
        self.payload = payload

    def search_google(self, query: str, num: int = 5):
        return self.payload


def test_resolve_domain_from_apply_url_without_serpapi():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx, provider_control_service=None)

    companies = [
        {
            "company_display": "Tekton Labs",
            "apply_url": "https://tektonlabs.com/careers/backend-engineer",
            "url": None,
        }
    ]

    result = service.resolve_domains(companies)

    assert result[0]["resolved_domain"] == "tektonlabs.com"
    assert result[0]["domain_source"] == "apply_url"
    assert result[0]["domain_confidence"] > 0.45


def test_resolve_domain_via_serpapi_fallback_when_direct_url_missing():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "serpapi_fallback_limit": 25,
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=object())
    service.serpapi_search_service = _FakeSerpAPISearchService(
        {
            "organic_results": [
                {
                    "link": "https://www.tektonlabs.com/",
                    "title": "Tekton Labs - Official Website",
                    "snippet": "Official software development company site.",
                }
            ]
        }
    )

    companies = [
        {
            "company_display": "Tekton Labs",
            "apply_url": None,
            "url": None,
        }
    ]

    result = service.resolve_domains(companies)

    assert result[0]["resolved_domain"] == "tektonlabs.com"
    assert result[0]["domain_source"] == "serpapi_fallback"
    assert result[0]["domain_confidence"] >= 0.45


def test_reject_suspicious_serpapi_domain_for_generic_name():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "serpapi_fallback_limit": 25,
                "review_threshold": 0.45,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=object())
    service.serpapi_search_service = _FakeSerpAPISearchService(
        {
            "organic_results": [
                {
                    "link": "https://www.ready.gov/",
                    "title": "READY.gov official site",
                    "snippet": "Preparedness information",
                }
            ]
        }
    )

    companies = [
        {
            "company_display": "Join ready",
            "apply_url": None,
            "url": None,
        }
    ]

    result = service.resolve_domains(companies)

    assert result[0]["resolved_domain"] is None
    assert result[0]["domain_source"] is None
    assert result[0]["domain_confidence"] == 0.0
