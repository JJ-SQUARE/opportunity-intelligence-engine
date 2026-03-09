from oie.orchestration.run_context import RunContext
from oie.services.company_identity_service import CompanyIdentityService


def test_merge_rules_can_disable_same_domain_candidates():
    ctx = RunContext.create(
        config={
            "company_identity": {
                "merge_rules": {
                    "allow_same_domain": False,
                    "allow_same_root": True,
                    "allow_same_normalized": True,
                }
            }
        }
    )
    service = CompanyIdentityService(ctx)

    companies = [
        {
            "company": "Acme One",
            "resolved_domain": "acme.com",
            "sources": ["google_jobs"],
        },
        {
            "company": "Beta Two",
            "resolved_domain": "acme.com",
            "sources": ["linkedin_jobs"],
        },
    ]

    enriched = service.enrich_company_identity(companies)
    candidates = ctx.provider_state.get("company_merge_candidates", [])

    assert len(enriched) == 2
    assert candidates == []
