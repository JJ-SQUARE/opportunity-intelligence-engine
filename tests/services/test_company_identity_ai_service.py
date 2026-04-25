from oie.orchestration.run_context import RunContext
from oie.services.company_identity_ai_service import CompanyIdentityAIService


class DummyRegistry:
    def get_client(self, name):
        class DummyOpenAIClient:
            def resolve_company_identity(self, company):
                return {
                    "is_valid_company": True,
                    "is_contaminated": False,
                    "is_ambiguous": False,
                    "company_name": "Acme Inc.",
                    "identity_source": "job_intelligence",
                    "confidence": 0.91,
                    "reason": "AI found a consistent hiring company in the job intelligence payload.",
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


def test_company_identity_ai_service_enriches_company_identity():
    ctx = RunContext.create(config={}, flags={})
    service = CompanyIdentityAIService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    result = service.enrich_companies([
        {
            "company": "Acme",
            "company_display": "Acme",
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "job_intelligence": {
                        "real_company_name": "Acme Inc.",
                        "confidence": 0.91,
                    },
                }
            ],
        }
    ])

    assert len(result) == 1
    assert result[0]["ai_company_identity"]["company_name"] == "Acme Inc."
    assert result[0]["ai_company_identity_confidence"] == 0.91
    assert result[0]["company_identity_ai_valid"] is True
    assert result[0]["company_identity_ai_contaminated"] is False
    assert service.provider_execution_service.calls == [
        ("openai", "resolve_company_identity")
    ]
    assert ctx.metrics["company_identity_ai_analyzed"] == 1
    assert ctx.metrics["company_identity_ai_completed"] is True


def test_company_identity_ai_service_respects_no_llm_flag():
    ctx = RunContext.create(config={}, flags={"no_llm": True})
    service = CompanyIdentityAIService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    companies = [{"company": "Acme"}]
    result = service.enrich_companies(companies)

    assert result == companies
    assert service.provider_execution_service.calls == []
    assert ctx.metrics["company_identity_ai_skipped_disabled"] is True


def test_company_identity_ai_service_discards_contaminated_companies():
    class ContaminatedRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def resolve_company_identity(self, company):
                    return {
                        "is_valid_company": True,
                        "is_contaminated": True,
                        "is_ambiguous": False,
                        "company_name": "Job Board Noise",
                        "identity_source": "snippet",
                        "confidence": 0.88,
                        "reason": "Snippet points to a job board wrapper, not a hiring company.",
                    }

            return DummyOpenAIClient()

    class ContaminatedProviderControlService:
        def __init__(self):
            self.registry = ContaminatedRegistry()

    ctx = RunContext.create(config={}, flags={})
    service = CompanyIdentityAIService(ctx, ContaminatedProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    result = service.enrich_companies([
        {
            "company": "Job Board Noise",
            "company_display": "Job Board Noise",
            "description": "Aggregator snippet with no real hiring company.",
        }
    ])

    assert result == []
    assert service.provider_execution_service.calls == [
        ("openai", "resolve_company_identity")
    ]
    assert ctx.metrics["company_identity_ai_analyzed"] == 1
    assert ctx.metrics["company_identity_ai_discarded"] == 1
    assert ctx.metrics["company_identity_ai_completed"] is True
