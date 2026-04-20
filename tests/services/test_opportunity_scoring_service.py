from oie.orchestration.run_context import RunContext
from oie.services.opportunity_scoring_service import OpportunityScoringService


def test_opportunity_scoring_service_scores_and_sorts_companies():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme",
            "total_openings": 3,
            "remote_jobs": 2,
            "contractor_jobs": 1,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
        },
        {
            "company_key": "cmp_b",
            "company_display": "Beta",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "job_board",
        },
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 2

    assert scored[0]["company_key"] == "cmp_a"
    assert scored[0]["score_openings"] == 24
    assert scored[0]["score_remote"] == 8
    assert scored[0]["score_contractor"] == 6
    assert scored[0]["score_multi_source"] == 10
    assert scored[0]["score_company_type"] == 20
    assert scored[0]["opportunity_score"] == 68

    assert scored[1]["company_key"] == "cmp_b"
    assert scored[1]["score_openings"] == 8
    assert scored[1]["score_remote"] == 0
    assert scored[1]["score_contractor"] == 0
    assert scored[1]["score_multi_source"] == 0
    assert scored[1]["score_company_type"] == -10
    assert scored[1]["opportunity_score"] == -2

    assert ctx.metrics["companies_scored"] == 2
    assert ctx.metrics["scoring_completed"] is True


def test_opportunity_scoring_service_caps_components():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_cap",
            "company_display": "Cap Co",
            "total_openings": 20,
            "remote_jobs": 10,
            "contractor_jobs": 10,
            "multi_source_signal": True,
            "company_type_ai": "consulting",
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["score_openings"] == 40
    assert scored[0]["score_remote"] == 20
    assert scored[0]["score_contractor"] == 20
    assert scored[0]["score_multi_source"] == 10
    assert scored[0]["score_company_type"] == 10
    assert scored[0]["opportunity_score"] == 100


def test_opportunity_scoring_service_supports_legacy_company_type_aliases():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_product",
            "company_display": "Product Co",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "product_company",
        },
        {
            "company_key": "cmp_staffing",
            "company_display": "Staffing Co",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "staffing_agency",
        },
    ]

    scored = {row["company_key"]: row for row in service.score_companies(companies)}

    assert scored["cmp_product"]["score_company_type"] == 20
    assert scored["cmp_staffing"]["score_company_type"] == 5


def test_opportunity_scoring_service_uses_llm_shape_when_available():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    return {
                        "opportunity_score": 83,
                        "opportunity_label": "high",
                        "score_icp_fit": 28,
                        "score_pain_urgency": 20,
                        "score_region_fit": 8,
                        "score_company_scale": 9,
                        "score_role_seniority_mix": 7,
                        "score_penalty_competitor": -5,
                        "score_penalty_negative_signals": -2,
                        "primary_service_fit": "talent_as_a_service",
                        "buyer_persona_fit": "high",
                        "opportunity_score_reason": "Buen fit ICP y señales claras de dolor.",
                        "scoring_provider": "openai",
                        "scoring_model": "gpt-4.1-mini",
                        "scoring_mode": "live_api",
                    }
            return DummyOpenAIClient()

    class DummyProviderControlService:
        def __init__(self):
            self.registry = DummyRegistry()

    class DummyProviderExecutionService:
        def __init__(self):
            self.calls = []

        def execute(self, provider_name, operation_name, func, *args, **kwargs):
            self.calls.append((provider_name, operation_name))
            return func(*args)

    ctx = RunContext.create(config={}, flags={})
    control = DummyProviderControlService()
    service = OpportunityScoringService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    companies = [
        {
            "company_key": "cmp_llm",
            "company_display": "Enterprise BFSI Co",
            "total_openings": 2,
            "remote_jobs": 1,
            "contractor_jobs": 0,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["company_key"] == "cmp_llm"
    assert scored[0]["opportunity_score"] == 83
    assert scored[0]["opportunity_label"] == "high"
    assert scored[0]["score_icp_fit"] == 28
    assert scored[0]["primary_service_fit"] == "talent_as_a_service"
    assert scored[0]["buyer_persona_fit"] == "high"
    assert scored[0]["opportunity_score_reason"] == "Buen fit ICP y señales claras de dolor."
    assert scored[0]["scoring_provider"] == "openai"
    assert scored[0]["scoring_model"] == "gpt-4.1-mini"
    assert scored[0]["scoring_mode"] == "live_api"


def test_opportunity_scoring_service_passes_scoring_context_to_llm():
    captured = {}

    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    captured["payload"] = company_payload
                    return {
                        "opportunity_score": 71,
                        "opportunity_label": "medium",
                        "score_icp_fit": 25,
                        "score_pain_urgency": 18,
                        "score_region_fit": 8,
                        "score_company_scale": 8,
                        "score_role_seniority_mix": 6,
                        "score_penalty_competitor": 0,
                        "score_penalty_negative_signals": -4,
                        "primary_service_fit": "agile_solution_delivery",
                        "buyer_persona_fit": "medium",
                        "opportunity_score_reason": "Buen fit, aunque con señales mixtas.",
                        "scoring_provider": "openai",
                        "scoring_model": "gpt-4.1-mini",
                        "scoring_mode": "live_api",
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
    service = OpportunityScoringService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    companies = [
        {
            "company_key": "cmp_ctx",
            "company_display": "BFSI Enterprise",
            "total_openings": 4,
            "remote_jobs": 2,
            "contractor_jobs": 0,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert "payload" in captured
    assert "scoring_context" in captured["payload"]
    assert captured["payload"]["scoring_context"]["commercial_rules"]["company_fit_more_important_than_vacancy_volume"] is True
    assert "banking and financial services" in captured["payload"]["scoring_context"]["priority_industries"]


def test_opportunity_scoring_service_tracks_llm_vs_rules_metrics():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    return {
                        "opportunity_score": 80,
                        "opportunity_label": "high",
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
    service = OpportunityScoringService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    companies = [
        {"company_key": "a", "company_display": "A"},
        {"company_key": "b", "company_display": "B"},
    ]

    scored = service.score_companies(companies)

    assert ctx.metrics["scoring_llm_used"] == 2
    assert ctx.metrics["scoring_rules_used"] == 0


def test_opportunity_scoring_service_skips_llm_for_benchmark_competitor():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    raise AssertionError("LLM no debería ejecutarse para benchmark competitor")
            return DummyOpenAIClient()

    class DummyProviderControlService:
        def __init__(self):
            self.registry = DummyRegistry()

    class DummyProviderExecutionService:
        def __init__(self):
            self.calls = []

        def execute(self, provider_name, operation_name, func, *args, **kwargs):
            self.calls.append((provider_name, operation_name))
            return func(*args)

    ctx = RunContext.create(config={}, flags={})
    control = DummyProviderControlService()
    service = OpportunityScoringService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    companies = [
        {
            "company_key": "cmp_comp",
            "company_display": "Competitor Co",
            "total_openings": 3,
            "remote_jobs": 1,
            "contractor_jobs": 0,
            "multi_source_signal": True,
            "company_type_ai": "competitor",
            "benchmark_only": True,
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["company_key"] == "cmp_comp"
    assert scored[0]["scoring_provider"] == "rules"
    assert scored[0]["scoring_mode"] == "fallback_rules"
    assert service.provider_execution_service.calls == []
