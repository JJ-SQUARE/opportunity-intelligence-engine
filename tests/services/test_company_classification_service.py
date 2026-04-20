from oie.orchestration.run_context import RunContext
from oie.services.company_classification_service import CompanyClassificationService
from oie.services.provider_control_service import ProviderControlService


def test_company_classification_service_uses_openai_stub():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Acme",
            "company_display": "Acme Inc.",
            "company_normalized": "acme",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "unknown"
    assert result[0]["classification_provider"] == "openai"
    assert ctx.metrics["companies_classified"] == 1


def test_company_classification_service_respects_no_llm_flag_with_rules():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Acme Consulting",
            "company_display": "Acme Consulting",
            "company_description": "Professional services and consulting",
        }
    ]
    result = service.classify_companies(companies)

    assert result[0]["company_type_ai"] == "consulting"
    assert result[0]["classification_provider"] == "rules"
    assert ctx.metrics["company_classification_skipped_no_llm"] is True


def test_company_classification_service_preserves_benchmark_competitor_without_llm_call():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def classify_company(self, company_payload):
                    raise AssertionError("OpenAI no debería ejecutarse para benchmark competitor")
            return DummyOpenAIClient()

    class DummyProviderControlService:
        def __init__(self):
            self.registry = DummyRegistry()

    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={},
    )
    control = DummyProviderControlService()
    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Competitor Co",
            "company_display": "Competitor Co",
            "company_type_ai": "competitor",
            "classification_confidence_ai": 1.0,
            "classification_source": "config_benchmark_competitor",
            "benchmark_only": True,
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "competitor"
    assert result[0]["classification_confidence_ai"] == 1.0
    assert result[0]["classification_provider"] == "config_benchmark_competitor"
