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


def test_resolve_domain_rejects_hireline_as_job_board_domain():
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
                    "link": "https://hireline.com/",
                    "title": "Hireline México - Empleos de tecnología",
                    "snippet": "Vacantes tech y bolsa de trabajo",
                }
            ]
        }
    )

    companies = [
        {
            "company_display": "HIRELINE",
            "apply_url": "https://hireline.io/mx/empleos/desarrollador-fullstack-sr/113370",
            "url": None,
        }
    ]

    result = service.resolve_domains(companies)

    assert result[0]["resolved_domain"] is None
    assert result[0]["domain_candidate"] is None or result[0]["domain_candidate"] == "hireline.com"
    assert result[0]["domain_validation_status"] == "rejected"


def test_resolve_domain_sends_beta_subdomain_to_review_not_accept():
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
                    "link": "https://beta.rimutee.com/",
                    "title": "Rimutee - Official Website",
                    "snippet": "Remote talent platform",
                }
            ]
        }
    )

    companies = [
        {
            "company_display": "Rimutee",
            "apply_url": "https://www.google.com/search?ibp=htl;jobs&q=test",
            "url": None,
        }
    ]

    result = service.resolve_domains(companies)

    assert result[0]["resolved_domain"] is None
    assert result[0]["domain_candidate"] == "beta.rimutee.com"
    assert result[0]["domain_validation_status"] == "review"
    assert result[0]["domain_review_required"] == 1
