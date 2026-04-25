from oie.orchestration.run_context import RunContext
from oie.services.opportunity_scoring_service import OpportunityScoringService


def test_opportunity_scoring_service_scores_and_sorts_companies():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme Bank",
            "industry": "Banking and Financial Services",
            "company_size": "1001-5000",
            "total_openings": 3,
            "remote_jobs": 2,
            "contractor_jobs": 1,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
            "jobs": [
                {
                    "title": "Senior Backend Engineer",
                    "description": "Java microservices on AWS for legacy migration",
                    "location": "Mexico",
                }
            ],
        },
        {
            "company_key": "cmp_b",
            "company_display": "Beta Jobs",
            "industry": "Internet",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "job_board",
            "jobs": [
                {
                    "title": "Junior Developer",
                    "description": "Entry level role",
                    "location": "Spain",
                }
            ],
        },
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 2

    assert scored[0]["company_key"] == "cmp_a"
    assert scored[0]["score_openings"] == 12
    assert scored[0]["score_remote"] == 4
    assert scored[0]["score_contractor"] == 2
    assert scored[0]["score_multi_source"] == 4
    assert scored[0]["score_company_type"] == 20
    assert scored[0]["score_icp_fit"] == 30
    assert scored[0]["score_region_fit"] == 10
    assert scored[0]["score_company_scale"] == 10
    assert scored[0]["score_role_seniority_mix"] >= 7
    assert scored[0]["score_pain_urgency"] >= 10
    assert scored[0]["opportunity_score"] > scored[1]["opportunity_score"]

    assert scored[1]["company_key"] == "cmp_b"
    assert scored[1]["score_openings"] == 4
    assert scored[1]["score_remote"] == 0
    assert scored[1]["score_contractor"] == 0
    assert scored[1]["score_multi_source"] == 0
    assert scored[1]["score_company_type"] == -20
    assert scored[1]["score_penalty_negative_signals"] <= -5
    assert scored[1]["opportunity_score"] == 0

    assert ctx.metrics["companies_scored"] == 2
    assert ctx.metrics["scoring_completed"] is True


def test_opportunity_scoring_service_caps_components():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_cap",
            "company_display": "Cap Co",
            "industry": "Banking and Financial Services",
            "company_size": "5001-10000",
            "total_openings": 20,
            "remote_jobs": 10,
            "contractor_jobs": 10,
            "multi_source_signal": True,
            "company_type_ai": "end_client",
            "jobs": [
                {
                    "title": "Principal Architect",
                    "description": "Critical role for legacy migration, microservices, cloud, AI",
                    "location": "Mexico",
                }
            ],
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["score_openings"] == 12
    assert scored[0]["score_remote"] == 6
    assert scored[0]["score_contractor"] == 6
    assert scored[0]["score_multi_source"] == 4
    assert scored[0]["score_company_type"] == 20
    assert scored[0]["score_icp_fit"] == 30
    assert scored[0]["score_pain_urgency"] == 25
    assert scored[0]["score_region_fit"] == 10
    assert scored[0]["score_company_scale"] == 10
    assert scored[0]["score_role_seniority_mix"] == 10
    assert scored[0]["opportunity_score"] <= 100


def test_opportunity_scoring_service_supports_legacy_company_type_aliases():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_product",
            "company_display": "Product Co",
            "industry": "Software",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "product_company",
        },
        {
            "company_key": "cmp_staffing",
            "company_display": "Staffing Co",
            "industry": "Staffing and Recruiting",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "company_type_ai": "staffing_agency",
        },
    ]

    scored = {row["company_key"]: row for row in service.score_companies(companies)}

    assert scored["cmp_product"]["score_company_type"] == 20
    assert scored["cmp_staffing"]["score_company_type"] == -25
    assert scored["cmp_staffing"]["score_penalty_competitor"] == -30
    assert scored["cmp_staffing"]["opportunity_label"] == "low"
    assert scored["cmp_staffing"]["opportunity_score"] <= 25


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



def test_opportunity_scoring_service_preserves_rule_score_breakdown_when_llm_scores():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    return {
                        "opportunity_score": 54,
                        "opportunity_label": "medium",
                        "score_icp_fit": 16,
                        "score_pain_urgency": 12,
                        "score_penalty_competitor": 0,
                        "opportunity_score_reason": "LLM score without base breakdown.",
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
    service = OpportunityScoringService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    scored = service.score_companies([
        {
            "company_key": "cmp_llm_breakdown",
            "company_display": "Hopper",
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.9,
            "resolved_domain": "hopper.com",
            "total_openings": 1,
            "remote_jobs": 1,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "jobs": [{"title": "Senior Backend Developer", "description": "Scala GCP AI remote role."}],
        }
    ])

    assert scored[0]["scoring_provider"] == "openai"
    assert scored[0]["score_openings"] == 4
    assert scored[0]["score_remote"] == 2
    assert scored[0]["score_contractor"] == 0
    assert scored[0]["score_multi_source"] == 0
    assert scored[0]["score_company_type"] == 20


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
        {
            "company_key": "a",
            "company_display": "A Bank",
            "company_type_ai": "end_client",
            "industry": "Banking and Financial Services",
            "jobs": [{"title": "Senior Backend Engineer", "description": "Python on AWS", "location": "Mexico"}],
        },
        {
            "company_key": "b",
            "company_display": "B Insurance",
            "company_type_ai": "end_client",
            "industry": "Insurance",
            "jobs": [{"title": "Engineering Manager", "description": "Cloud modernization", "location": "Colombia"}],
        },
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

def test_opportunity_scoring_service_caps_llm_score_for_vendor_like_company():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    return {
                        "opportunity_score": 86,
                        "opportunity_label": "high",
                        "score_icp_fit": 24,
                        "score_pain_urgency": 18,
                        "score_region_fit": 8,
                        "score_company_scale": 9,
                        "score_role_seniority_mix": 8,
                        "score_penalty_competitor": -5,
                        "score_penalty_negative_signals": 0,
                        "primary_service_fit": "talent_as_a_service",
                        "buyer_persona_fit": "high",
                        "opportunity_score_reason": "Mucha actividad de contratación.",
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
            "company_key": "cmp_vendor_llm",
            "company_display": "Vendor Co",
            "company_type_ai": "consulting",
            "industry": "Information Technology and Services",
            "company_description": "Software consulting and outsourcing services",
            "total_openings": 10,
            "remote_jobs": 8,
            "contractor_jobs": 5,
            "multi_source_signal": True,
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["opportunity_score"] <= 25
    assert scored[0]["opportunity_label"] == "low"
    assert scored[0]["score_penalty_competitor"] <= -30


def test_opportunity_scoring_service_caps_unknown_with_weak_evidence():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    companies = [
        {
            "company_key": "cmp_unknown",
            "company_display": "Stealth World",
            "company_type_ai": "unknown",
            "industry": "",
            "company_description": "",
            "total_openings": 1,
            "remote_jobs": 1,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "jobs": [
                {
                    "title": "Developer",
                    "description": "Generalist role",
                    "location": "Remote",
                }
            ],
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["opportunity_score"] <= 39
    assert scored[0]["opportunity_label"] == "low"

def test_opportunity_scoring_service_skips_llm_for_job_board_and_uses_rules():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    raise AssertionError("LLM no debería ejecutarse para job_board")
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
            "company_key": "cmp_jobs",
            "company_display": "Jobs Board Co",
            "company_type_ai": "job_board",
            "industry": "Internet",
            "total_openings": 20,
            "remote_jobs": 10,
            "contractor_jobs": 10,
            "multi_source_signal": True,
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["company_key"] == "cmp_jobs"
    assert scored[0]["opportunity_label"] == "low"
    assert scored[0]["opportunity_score"] <= 20
    assert service.provider_execution_service.calls == []


def test_opportunity_scoring_service_caps_weak_buyer_persona_even_with_high_score():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_guard",
            "company_display": "Weak Buyer Persona Co",
            "company_type_ai": "end_client",
        },
        {
            "opportunity_score": 82,
            "score_icp_fit": 14,
            "score_pain_urgency": 8,
            "score_region_fit": 0,
            "buyer_persona_fit": "low",
            "opportunity_score_reason": "Raw score alto pero sin evidencia suficiente.",
        },
    )

    assert guarded["opportunity_score"] <= 54
    assert guarded["opportunity_label"] == "medium"

def test_opportunity_scoring_service_caps_high_score_without_reachability_signal():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_reach",
            "company_display": "Strong ICP but unreachable Co",
            "company_type_ai": "end_client",
            "domain_validation_status": "rejected",
            "resolved_domain": "",
            "linkedin_company_url": "",
            "enrichment_source": "",
        },
        {
            "opportunity_score": 84,
            "score_icp_fit": 28,
            "score_pain_urgency": 20,
            "score_region_fit": 8,
            "buyer_persona_fit": "high",
            "opportunity_score_reason": "Buen fit comercial bruto.",
        },
    )

    assert guarded["opportunity_score"] <= 64
    assert guarded["opportunity_label"] == "medium"
    assert "reachability" in guarded["opportunity_score_reason"].lower()

def test_opportunity_scoring_service_skips_llm_for_unknown_with_weak_evidence():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    raise AssertionError("LLM no debería ejecutarse para unknown con evidencia débil")
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
            "company_key": "cmp_weak_unknown",
            "company_display": "Stealth World",
            "company_type_ai": "unknown",
            "industry": "",
            "company_description": "",
            "total_openings": 1,
            "remote_jobs": 1,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "jobs": [
                {
                    "title": "Developer",
                    "description": "Generalist role",
                    "location": "Remote",
                }
            ],
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["company_key"] == "cmp_weak_unknown"
    assert scored[0]["scoring_provider"] == "rules"
    assert scored[0]["scoring_mode"] == "fallback_rules"
    assert service.provider_execution_service.calls == [("openai", "score_company")]
    assert ctx.metrics["scoring_llm_used"] == 0
    assert ctx.metrics["scoring_rules_used"] == 1


def test_opportunity_scoring_service_caps_reachability_without_real_icp_evidence():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_reach_only",
            "company_display": "Reachability Only Co",
            "company_type_ai": "unknown",
            "domain_validation_status": "accepted",
            "resolved_domain": "reachability-only.com",
            "linkedin_company_url": "https://linkedin.com/company/reachability-only",
            "enrichment_source": "",
            "industry": "",
            "company_description": "",
            "jobs": [],
            "total_openings": 1,
        },
        {
            "opportunity_score": 78,
            "score_icp_fit": 12,
            "score_pain_urgency": 8,
            "score_region_fit": 0,
            "buyer_persona_fit": "medium",
            "opportunity_score_reason": "Tiene señales operativas y reachability.",
        },
    )

    assert guarded["opportunity_score"] <= 49
    assert guarded["opportunity_label"] == "low"
    assert "ICP" in guarded["opportunity_score_reason"]


def test_opportunity_scoring_service_hard_caps_when_no_reachability_and_no_real_icp():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_weak_all",
            "company_display": "Weak All Co",
            "company_type_ai": "unknown",
            "domain_validation_status": "rejected",
            "resolved_domain": "",
            "linkedin_company_url": "",
            "enrichment_source": "",
            "industry": "",
            "company_description": "",
            "jobs": [],
            "total_openings": 1,
        },
        {
            "opportunity_score": 61,
            "score_icp_fit": 11,
            "score_pain_urgency": 8,
            "score_region_fit": 0,
            "buyer_persona_fit": "medium",
            "opportunity_score_reason": "Raw score intermedio.",
        },
    )

    assert guarded["opportunity_score"] <= 39
    assert guarded["opportunity_label"] == "low"
    assert "reachability" in guarded["opportunity_score_reason"].lower()


def test_opportunity_scoring_service_skips_llm_for_low_icp_evidence_even_if_structured_data_exists():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def score_company(self, company_payload):
                    raise AssertionError("LLM no debería ejecutarse cuando no hay evidencia ICP real")
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
            "company_key": "cmp_structured_but_weak",
            "company_display": "Generic Holdings",
            "company_type_ai": "unknown",
            "industry": "",
            "company_description": "General business company.",
            "resolved_domain": "generic-holdings.example",
            "linkedin_company_url": "",
            "total_openings": 1,
            "remote_jobs": 0,
            "contractor_jobs": 0,
            "multi_source_signal": False,
            "jobs": [
                {
                    "title": "Developer",
                    "description": "Generalist role",
                    "location": "Remote",
                }
            ],
        }
    ]

    scored = service.score_companies(companies)

    assert len(scored) == 1
    assert scored[0]["scoring_provider"] == "rules"
    assert scored[0]["scoring_mode"] == "fallback_rules"
    assert service.provider_execution_service.calls == [("openai", "score_company")]
    assert ctx.metrics["scoring_llm_used"] == 0
    assert ctx.metrics["scoring_rules_used"] == 1


def test_opportunity_scoring_service_detects_real_icp_evidence_for_confident_end_client_with_supporting_signals():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    assert service._has_real_icp_evidence(
        {
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.9,
            "company_display": "Acme Bank",
            "industry": "Banking and Financial Services",
            "jobs": [
                {
                    "title": "Engineering Manager",
                    "description": "Java modernization on AWS",
                    "location": "Mexico",
                }
            ],
            "total_openings": 2,
        }
    ) is True


def test_opportunity_scoring_service_does_not_treat_end_client_label_alone_as_real_icp_evidence():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    assert service._has_real_icp_evidence(
        {
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.55,
            "company_display": "Weak End Client",
            "industry": "",
            "company_description": "",
            "jobs": [],
            "total_openings": 1,
        }
    ) is False


def test_opportunity_scoring_service_does_not_treat_reachability_as_real_icp_evidence():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    assert service._has_real_icp_evidence(
        {
            "company_type_ai": "unknown",
            "company_display": "Generic Holdings",
            "resolved_domain": "generic.example",
            "linkedin_company_url": "https://linkedin.com/company/generic",
            "company_description": "General business company.",
            "jobs": [],
            "total_openings": 1,
        }
    ) is False

def test_opportunity_scoring_service_does_not_treat_secondary_industry_plus_reachability_as_real_icp():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    assert service._has_real_icp_evidence(
        {
            "company_type_ai": "unknown",
            "company_display": "Retail Reach Co",
            "industry": "Retail",
            "resolved_domain": "retailreach.com",
            "linkedin_company_url": "https://linkedin.com/company/retailreach",
            "company_description": "Retail company with generic operations.",
            "jobs": [
                {
                    "title": "Developer",
                    "description": "Generalist role",
                    "location": "Remote",
                }
            ],
            "total_openings": 1,
        }
    ) is False


def test_opportunity_scoring_service_caps_reachable_end_client_with_high_score_when_classification_is_weak():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_endclient_classification_weak",
            "company_display": "Weakly Classified End Client",
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.4,
            "domain_validation_status": "accepted",
            "resolved_domain": "weakclassified.com",
            "linkedin_company_url": "https://linkedin.com/company/weakclassified",
            "enrichment_source": "",
            "industry": "",
            "company_description": "",
            "jobs": [],
            "total_openings": 1,
        },
        {
            "opportunity_score": 81,
            "score_icp_fit": 22,
            "score_pain_urgency": 14,
            "score_region_fit": 0,
            "buyer_persona_fit": "medium",
            "opportunity_score_reason": "Score bruto alto por reachability y señales parciales.",
        },
    )

    assert guarded["opportunity_score"] <= 54
    assert guarded["opportunity_label"] == "medium"
    assert "reachable end_client" in guarded["opportunity_score_reason"].lower()


def test_opportunity_scoring_service_caps_reachable_end_client_without_real_icp_evidence():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_endclient_weak_icp",
            "company_display": "Reachable Weak ICP Co",
            "company_type_ai": "end_client",
            "domain_validation_status": "accepted",
            "resolved_domain": "weakicp.com",
            "linkedin_company_url": "https://linkedin.com/company/weakicp",
            "enrichment_source": "",
            "industry": "",
            "company_description": "",
            "jobs": [],
            "total_openings": 1,
        },
        {
            "opportunity_score": 74,
            "score_icp_fit": 14,
            "score_pain_urgency": 8,
            "score_region_fit": 0,
            "buyer_persona_fit": "medium",
            "opportunity_score_reason": "Tiene dominio válido y señales básicas.",
        },
    )

    assert guarded["opportunity_score"] <= 54
    assert guarded["opportunity_label"] == "medium"
    assert "evidencia icp" in guarded["opportunity_score_reason"].lower()


def test_opportunity_scoring_service_applies_floor_for_reachable_end_client_with_good_icp_and_pain():
    ctx = RunContext.create(config={}, flags={})
    service = OpportunityScoringService(ctx)

    guarded = service._apply_scoring_guardrails(
        {
            "company_key": "cmp_endclient_floor",
            "company_display": "Strong Reachable End Client",
            "company_type_ai": "end_client",
            "domain_validation_status": "accepted",
            "resolved_domain": "strongclient.com",
            "linkedin_company_url": "",
            "enrichment_source": "",
            "industry": "Banking and Financial Services",
            "company_description": "Enterprise bank modernizing core platforms.",
            "jobs": [
                {
                    "title": "Engineering Manager",
                    "description": "Critical modernization role using Java microservices on AWS.",
                    "location": "Mexico",
                }
            ],
            "total_openings": 3,
        },
        {
            "opportunity_score": 38,
            "score_icp_fit": 26,
            "score_pain_urgency": 18,
            "score_region_fit": 8,
            "buyer_persona_fit": "high",
            "opportunity_score_reason": "Score bruto demasiado conservador.",
        },
    )

    assert guarded["opportunity_score"] >= 45
    assert guarded["opportunity_label"] in {"medium", "high"}
    assert "piso aplicado" in guarded["opportunity_score_reason"].lower()

