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
    assert ctx.metrics["leads_useful"] == 1

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


def test_lead_ranking_service_uses_llm_shape_when_available():
    captured = {}

    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_lead(self, payload):
                    captured["payload"] = payload
                    return {
                        "lead_relevance_score": 88,
                        "lead_priority_label": "high",
                        "lead_decision_maker_score": 34,
                        "lead_icp_fit_score": 28,
                        "lead_contact_completeness_score": 18,
                        "lead_penalty_negative_title": 0,
                        "lead_score_reason": "Strong technical decision-maker with reachable channel.",
                        "lead_role_type": "primary_decision_maker",
                        "why_selected": "Owns technology strategy and delivery.",
                        "outreach_angle": "Discuss engineering capacity and delivery acceleration.",
                        "expected_relevance": "high",
                        "risk_or_uncertainty": "No explicit budget authority confirmed.",
                        "lead_scoring_provider": "openai",
                        "lead_scoring_model": "gpt-4.1-mini",
                        "lead_scoring_mode": "live_api",
                    }
            return DummyOpenAIClient()

    class DummyProviderControlService:
        def __init__(self):
            self.registry = DummyRegistry()

    class DummyProviderExecutionService:
        def execute(self, provider_name, operation_name, func, *args, **kwargs):
            return func(*args)

    ctx = RunContext.create(config={}, flags={})
    control = DummyProviderControlService()
    service = LeadRankingService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    leads = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme BFSI",
            "industry": "Banking and Financial Services",
            "resolved_domain": "acme.com",
            "company_type_ai": "end_client",
            "opportunity_score": 82,
            "contact_name": "Jane Doe",
            "contact_title": "CTO",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/jane",
            "lead_source": "apollo_people",
            "lead_confidence": 0.9,
            "email_quality_score": 95,
        }
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["lead_relevance_score"] == 88
    assert ranked[0]["lead_priority_label"] == "high"
    assert ranked[0]["lead_scoring_provider"] == "openai"
    assert ranked[0]["lead_role_type"] == "primary_decision_maker"
    assert ranked[0]["why_selected"] == "Owns technology strategy and delivery."
    assert ranked[0]["outreach_angle"] == "Discuss engineering capacity and delivery acceleration."
    assert ranked[0]["expected_relevance"] == "high"
    assert ranked[0]["risk_or_uncertainty"] == "No explicit budget authority confirmed."
    assert "lead_scoring_context" in captured["payload"]
    assert captured["payload"]["lead_scoring_context"]["commercial_rules"]["decision_maker_seniority_required_for_top_scores"] is True
    assert "banking and financial services" in captured["payload"]["lead_scoring_context"]["priority_industries"]


def test_lead_ranking_service_tracks_llm_vs_rules_metrics():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_lead(self, payload):
                    return {
                        "lead_relevance_score": 80,
                        "lead_priority_label": "high",
                    }
            return DummyOpenAIClient()

    class DummyProviderControlService:
        def __init__(self):
            self.registry = DummyRegistry()

    class DummyProviderExecutionService:
        def execute(self, provider_name, operation_name, func, *args, **kwargs):
            return func(*args)

    ctx = RunContext.create(config={}, flags={})
    control = DummyProviderControlService()
    service = LeadRankingService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    ranked = service.rank_leads(
        [
            {
                "company_key": "cmp_a",
                "contact_name": "A",
                "contact_title": "CTO",
                "email": "a@acme.com",
                "linkedin_url": "",
                "lead_source": "apollo_people",
                "lead_confidence": 0.9,
                "email_quality_score": 90,
            }
        ]
    )

    assert len(ranked) == 1
    assert ctx.metrics["lead_scoring_llm_used"] == 1
    assert ctx.metrics["lead_scoring_rules_used"] == 0

def test_lead_ranking_service_prioritizes_icp_titles_like_cdo_and_it_manager():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "CDO Contact",
            "contact_title": "Chief Digital Officer",
            "email": "cdo@acme.com",
            "linkedin_url": "https://linkedin.com/in/cdo",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.8,
            "email_quality_score": 90,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Generic Director",
            "contact_title": "Director",
            "email": "director@acme.com",
            "linkedin_url": "https://linkedin.com/in/director",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.8,
            "email_quality_score": 90,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "CDO Contact"
    assert ranked[0]["lead_score_title"] > ranked[1]["lead_score_title"]




def test_lead_ranking_service_deprioritizes_product_titles_against_true_buyer_personas():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Product Leader",
            "contact_title": "Head of Product",
            "email": "product@acme.com",
            "linkedin_url": "https://linkedin.com/in/product",
            "lead_source": "apollo_people",
            "lead_confidence": 0.95,
            "email_quality_score": 95,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Engineering Leader",
            "contact_title": "Head of Engineering",
            "email": "eng@acme.com",
            "linkedin_url": "https://linkedin.com/in/eng",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 88,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Engineering Leader"
    assert ranked[0]["lead_score_title"] > ranked[1]["lead_score_title"]


def test_lead_ranking_service_deprioritizes_coo_against_cto():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Operations Exec",
            "contact_title": "COO",
            "email": "coo@acme.com",
            "linkedin_url": "https://linkedin.com/in/coo",
            "lead_source": "apollo_people",
            "lead_confidence": 0.95,
            "email_quality_score": 95,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Technology Exec",
            "contact_title": "CTO",
            "email": "cto@acme.com",
            "linkedin_url": "https://linkedin.com/in/cto",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.80,
            "email_quality_score": 85,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Technology Exec"
    assert ranked[0]["lead_score_title"] > ranked[1]["lead_score_title"]


def test_lead_ranking_service_deprioritizes_competitor_or_staffing_contacts():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_vendor",
            "company_type_ai": "staffing",
            "contact_name": "Vendor CTO",
            "contact_title": "CTO",
            "email": "vendor@staffco.com",
            "linkedin_url": "https://linkedin.com/in/vendor",
            "lead_source": "apollo_people",
            "lead_confidence": 0.95,
            "email_quality_score": 95,
        },
        {
            "company_key": "cmp_client",
            "company_type_ai": "end_client",
            "contact_name": "Client Engineering Manager",
            "contact_title": "Engineering Manager",
            "email": "manager@client.com",
            "linkedin_url": "https://linkedin.com/in/clientmanager",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 90,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Client Engineering Manager"
    assert ranked[1]["contact_name"] == "Vendor CTO"
    assert ranked[1]["lead_score_company_penalty"] < 0


def test_lead_ranking_service_can_keep_top_multiple_leads_per_company():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Top CTO",
            "contact_title": "CTO",
            "email": "cto@acme.com",
            "linkedin_url": "https://linkedin.com/in/cto",
            "lead_source": "apollo_people",
            "lead_confidence": 0.95,
            "email_quality_score": 95,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Strong VP",
            "contact_title": "VP Engineering",
            "email": "vp@acme.com",
            "linkedin_url": "https://linkedin.com/in/vp",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.85,
            "email_quality_score": 90,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Third Director",
            "contact_title": "Director of Engineering",
            "email": "director@acme.com",
            "linkedin_url": "https://linkedin.com/in/director",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.8,
            "email_quality_score": 88,
        },
        {
            "company_key": "cmp_b",
            "contact_name": "Only B",
            "contact_title": "Head of Engineering",
            "email": "head@beta.com",
            "linkedin_url": "https://linkedin.com/in/headbeta",
            "lead_source": "apollo_people",
            "lead_confidence": 0.9,
            "email_quality_score": 92,
        },
    ]

    ranked = service.rank_leads(leads)
    selected = service.select_top_leads_per_company(leads, max_leads_per_company=2)

    assert len(selected) == 3
    assert selected[0]["contact_name"] == "Top CTO"
    assert selected[1]["contact_name"] == "Only B"
    assert [lead["company_key"] for lead in selected] == ["cmp_a", "cmp_b", "cmp_a"]
    assert selected[0]["contact_name"] == ranked[0]["contact_name"]
    assert selected[1]["contact_name"] == "Only B"
    assert selected[2]["contact_name"] in {"Strong VP", "Third Director"}
    assert {lead["contact_name"] for lead in selected} in [
        {"Top CTO", "Only B", "Strong VP"},
        {"Top CTO", "Only B", "Third Director"},
    ]
    assert ctx.metrics["best_leads_selected"] == len(selected)
    assert ctx.metrics["best_leads_selected_companies"] == 2
    assert ctx.metrics["best_leads_selected_max_per_company"] == 2



def test_lead_ranking_service_prefers_apollo_when_same_contact_competes_with_hunter():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Jane Doe",
            "contact_title": "CTO",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.95,
            "email_quality_score": 100,
            "lead_relevance_score": 140,
            "lead_score_title": 100,
            "lead_score_source": 15,
            "lead_score_email": 20,
            "lead_score_linkedin": 10,
            "lead_score_email_quality": 20,
            "lead_score_confidence": 19,
            "lead_score_completeness_penalty": 0,
            "lead_score_company_penalty": 0,
            "lead_priority_label": "high",
            "lead_scoring_provider": "rules",
            "lead_scoring_mode": "fallback_rules",
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Jane Doe",
            "contact_title": "CTO",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "lead_source": "apollo_people",
            "lead_confidence": 0.80,
            "email_quality_score": 90,
            "lead_relevance_score": 140,
            "lead_score_title": 100,
            "lead_score_source": 30,
            "lead_score_email": 20,
            "lead_score_linkedin": 10,
            "lead_score_email_quality": 18,
            "lead_score_confidence": 16,
            "lead_score_completeness_penalty": 0,
            "lead_score_company_penalty": 0,
            "lead_priority_label": "high",
            "lead_scoring_provider": "rules",
            "lead_scoring_mode": "fallback_rules",
        },
    ]

    selected = service.select_top_leads_per_company(leads, max_leads_per_company=1)

    assert len(selected) == 1
    assert selected[0]["lead_source"] == "apollo_people"



def test_lead_ranking_service_normalizes_legacy_outsourcing_alias():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    leads = [
        {
            "company_key": "cmp_vendor",
            "company_type_ai": "outsourcing",
            "contact_name": "Vendor CTO",
            "contact_title": "CTO",
            "email": "vendor@outsourceco.com",
            "linkedin_url": "https://linkedin.com/in/vendor",
            "lead_source": "apollo_people",
            "lead_confidence": 0.95,
            "email_quality_score": 95,
        },
        {
            "company_key": "cmp_client",
            "company_type_ai": "end_client",
            "contact_name": "Client CTO",
            "contact_title": "CTO",
            "email": "client@acme.com",
            "linkedin_url": "https://linkedin.com/in/client",
            "lead_source": "apollo_people",
            "lead_confidence": 0.95,
            "email_quality_score": 95,
        },
    ]

    ranked = service.rank_leads(leads)

    assert ranked[0]["contact_name"] == "Client CTO"
    assert ranked[1]["contact_name"] == "Vendor CTO"
    assert ranked[1]["lead_score_company_penalty"] < 0

def test_lead_ranking_service_does_not_rerank_when_input_already_has_rank_fields():
    ctx = RunContext.create(config={}, flags={})
    service = LeadRankingService(ctx)

    ranked_input = [
        {
            "company_key": "cmp_a",
            "contact_name": "Top CTO",
            "contact_title": "Director",
            "email": "cto@acme.com",
            "linkedin_url": "https://linkedin.com/in/cto",
            "lead_source": "apollo_people",
            "lead_confidence": 0.9,
            "email_quality_score": 95,
            "lead_relevance_score": 97,
            "lead_score_title": 100,
            "lead_score_source": 30,
            "lead_score_email": 20,
            "lead_score_linkedin": 10,
            "lead_score_email_quality": 19,
            "lead_score_confidence": 18,
            "lead_score_completeness_penalty": 0,
            "lead_score_company_penalty": 0,
            "lead_priority_label": "high",
            "lead_scoring_provider": "rules",
            "lead_scoring_mode": "fallback_rules",
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Second VP",
            "contact_title": "CTO",
            "email": "vp@acme.com",
            "linkedin_url": "https://linkedin.com/in/vp",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.8,
            "email_quality_score": 90,
            "lead_relevance_score": 88,
            "lead_score_title": 80,
            "lead_score_source": 15,
            "lead_score_email": 20,
            "lead_score_linkedin": 10,
            "lead_score_email_quality": 18,
            "lead_score_confidence": 16,
            "lead_score_completeness_penalty": 0,
            "lead_score_company_penalty": 0,
            "lead_priority_label": "high",
            "lead_scoring_provider": "rules",
            "lead_scoring_mode": "fallback_rules",
        },
        {
            "company_key": "cmp_b",
            "contact_name": "Only B",
            "contact_title": "Manager",
            "email": "head@beta.com",
            "linkedin_url": "https://linkedin.com/in/headbeta",
            "lead_source": "apollo_people",
            "lead_confidence": 0.85,
            "email_quality_score": 92,
            "lead_relevance_score": 91,
            "lead_score_title": 58,
            "lead_score_source": 30,
            "lead_score_email": 20,
            "lead_score_linkedin": 10,
            "lead_score_email_quality": 18,
            "lead_score_confidence": 17,
            "lead_score_completeness_penalty": 0,
            "lead_score_company_penalty": 0,
            "lead_priority_label": "high",
            "lead_scoring_provider": "rules",
            "lead_scoring_mode": "fallback_rules",
        },
    ]

    def boom(_):
        raise AssertionError("rank_leads no debería ejecutarse cuando la entrada ya viene rankeada")

    service.rank_leads = boom

    selected = service.select_top_leads_per_company(ranked_input, max_leads_per_company=2)
    top_leads = service.build_top_leads(ranked_input, limit=2)

    assert [lead["contact_name"] for lead in selected] in [
        ["Top CTO", "Only B", "Second VP"],
        ["Top CTO", "Only B"],
    ]
    assert [lead["contact_name"] for lead in top_leads] == ["Top CTO", "Second VP"]
    assert ctx.metrics["best_leads_selected"] == len(selected)
    assert ctx.metrics["best_leads_selected_companies"] == 2
    assert ctx.metrics["best_leads_selected_max_per_company"] == 2

