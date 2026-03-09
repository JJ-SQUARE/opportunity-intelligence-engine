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
    assert ctx.budgets["openai"]["used_calls"] == 1


def test_company_classification_service_respects_no_llm_flag():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [{"company": "Acme"}]
    result = service.classify_companies(companies)

    assert result == companies
    assert ctx.metrics["company_classification_skipped_no_llm"] is True
