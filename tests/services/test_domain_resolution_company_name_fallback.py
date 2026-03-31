from oie.orchestration.run_context import RunContext
from oie.services.domain_resolution_service import DomainResolutionService


class _FakeSerpAPISearchService:
    def __init__(self, payload):
        self.payload = payload
        self.queries = []

    def search_google(self, query: str, num: int = 5):
        self.queries.append(query)
        return self.payload


def test_domain_resolution_uses_extracted_company_name_from_title():
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
    fake_serp = _FakeSerpAPISearchService(
        {
            "organic_results": [
                {
                    "link": "https://www.tenaris.com/",
                    "title": "Tenaris Official Website",
                    "snippet": "Global steel pipe company",
                }
            ]
        }
    )
    service.serpapi_search_service = fake_serp

    result = service.resolve_domains(
        [
            {
                "company_display": "Confidencial",
                "title": "Backend Engineer at Tenaris",
                "snippet": "Remote role",
                "apply_url": "https://jobgether.com/offer/123",
                "url": None,
            }
        ]
    )

    assert fake_serp.queries == ["Tenaris official website"]
    assert result[0]["resolved_domain"] == "tenaris.com"
    assert result[0]["domain_validation_status"] == "accepted"
