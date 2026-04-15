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
            "lead_confidence": 0.9,
            "email_quality_score": 95,
            "lead_capture_reason": "apollo_match | title:CTO | email_quality:95",
        },
        {
            "company_key": "cmp_a",
            "contact_name": "B",
            "contact_title": "Head of Product",
            "email": "",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.5,
            "email_quality_score": 0,
            "lead_capture_reason": "hunter_match | title:Head of Product",
        },
    ]

    ranked = service.rank_leads(leads)
    best = service.select_best_lead_per_company(leads)
    top_leads = service.build_top_leads(leads, limit=10)

    assert ranked[0]["contact_name"] == "A"
    assert ranked[0]["lead_relevance_score"] > ranked[1]["lead_relevance_score"]
    assert len(best) == 1
    assert best[0]["contact_name"] == "A"

    assert len(top_leads) == 2
    assert top_leads[0]["contact_name"] == "A"
    assert top_leads[0]["lead_score_title"] == 100
    assert top_leads[0]["lead_score_source"] == 30
    assert top_leads[0]["lead_score_email"] == 20
    assert top_leads[0]["lead_score_linkedin"] == 10
    assert top_leads[0]["lead_score_email_quality"] == 19
    assert top_leads[0]["lead_score_confidence"] == 18
    assert top_leads[0]["email_quality_score"] == 95
    assert "apollo_match" in top_leads[0]["lead_capture_reason"]


def test_lead_ranking_service_prefers_higher_email_quality_when_relevance_ties():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Lower Quality",
            "contact_title": "VP Engineering",
            "email": "low@acme.com",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.5,
            "email_quality_score": 60,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Higher Quality",
            "contact_title": "VP Engineering",
            "email": "high@acme.com",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.5,
            "email_quality_score": 90,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Higher Quality"
    assert ranked[0]["lead_relevance_score"] >= ranked[1]["lead_relevance_score"]

def test_lead_ranking_service_handles_string_numeric_fields_in_sort():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Alpha",
            "contact_title": "VP Engineering",
            "email": "alpha@acme.com",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": "0.5",
            "email_quality_score": "70",
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Beta",
            "contact_title": "VP Engineering",
            "email": "beta@acme.com",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": "0.5",
            "email_quality_score": "90",
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Beta"
    assert ranked[1]["contact_name"] == "Alpha"



def test_lead_ranking_service_penalizes_non_technical_titles():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Technical",
            "contact_title": "Director of Engineering",
            "email": "tech@acme.com",
            "linkedin_url": "https://linkedin.com/in/tech",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 100,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Non Technical",
            "contact_title": "Compliance Director",
            "email": "compliance@acme.com",
            "linkedin_url": "https://linkedin.com/in/compliance",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 100,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Technical"
    assert ranked[0]["lead_score_title"] > ranked[1]["lead_score_title"]
    assert ranked[0]["lead_relevance_score"] > ranked[1]["lead_relevance_score"]

def test_lead_ranking_service_penalizes_contacts_without_email_and_linkedin():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Weak CEO",
            "contact_title": "CEO",
            "email": "",
            "linkedin_url": "",
            "lead_source": "apollo_people",
            "lead_confidence": 0.9,
            "email_quality_score": 0,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Strong Director",
            "contact_title": "Director of Engineering",
            "email": "director@acme.com",
            "linkedin_url": "https://linkedin.com/in/director",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 100,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Strong Director"
    assert ranked[1]["contact_name"] == "Weak CEO"
    assert ranked[1]["lead_score_completeness_penalty"] < 0


def test_lead_ranking_service_penalizes_generic_director_against_technical_director():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Generic",
            "contact_title": "Director",
            "email": "generic@acme.com",
            "linkedin_url": "https://linkedin.com/in/generic",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 100,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Technical",
            "contact_title": "Director of Engineering",
            "email": "technical@acme.com",
            "linkedin_url": "https://linkedin.com/in/technical",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 100,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Technical"
    assert ranked[0]["lead_score_title"] > ranked[1]["lead_score_title"]
