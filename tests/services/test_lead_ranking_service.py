from oie.orchestration.run_context import RunContext
from oie.services.lead_ranking_service import LeadRankingService


def test_lead_ranking_service_ranks_and_selects_best_per_company():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "A",
            "contact_title": "CTO",
            "email": "a@acme.com",
            "linkedin_url": "https://linkedin.com/in/a",
            "lead_source": "apollo_people",
        },
        {
            "company_key": "cmp_a",
            "contact_name": "B",
            "contact_title": "Head of Product",
            "email": "",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
        },
    ]

    ranked = service.rank_leads(leads)
    best = service.select_best_lead_per_company(leads)

    assert ranked[0]["contact_name"] == "A"
    assert ranked[0]["lead_relevance_score"] > ranked[1]["lead_relevance_score"]
    assert len(best) == 1
    assert best[0]["contact_name"] == "A"
