from oie.orchestration.run_context import RunContext
from oie.services.domain_resolution_service import DomainResolutionService


class _FakeSerpAPISearchService:
    def __init__(self, payload):
        self.payload = payload

    def search_google(self, query: str, num: int = 5):
        return self.payload


def test_non_actionable_company_name_is_skipped():
    ctx = RunContext.create(config={})
    service = DomainResolutionService(ctx, provider_control_service=None)

    result = service.resolve_domains(
        [
            {
                "company_display": "Confidencial",
                "apply_url": "https://jobgether.com/job/x",
                "url": None,
            }
        ]
    )

    assert result[0]["resolved_domain"] is None
    assert result[0]["domain_validation_status"] == "rejected"
    assert ctx.metrics["domain_resolution_skipped_non_actionable_company_name"] == 1


def test_aggregator_apply_url_does_not_become_final_domain_when_company_is_actionable():
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
                    "link": "https://www.tenaris.com/",
                    "title": "Tenaris - Official Website",
                    "snippet": "Official site of Tenaris",
                }
            ]
        }
    )

    result = service.resolve_domains(
        [
            {
                "company_display": "Tenaris",
                "apply_url": "https://jobgether.com/offer/123",
                "url": None,
            }
        ]
    )

    assert result[0]["domain_candidate"] == "tenaris.com"
    assert result[0]["resolved_domain"] == "tenaris.com"
    assert result[0]["domain_source"] == "serpapi_fallback"
    assert result[0]["domain_validation_status"] == "accepted"
