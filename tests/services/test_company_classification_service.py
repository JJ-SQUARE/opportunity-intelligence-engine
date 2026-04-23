from oie.orchestration.run_context import RunContext
from oie.services.company_classification_service import CompanyClassificationService
from oie.services.provider_control_service import ProviderControlService


def test_company_classification_service_uses_openai_heuristic_classification():
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
            "company_description": "Builds software products for banks and insurers.",
            "industry": "Computer Software",
            "resolved_domain": "acme.com",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "end_client"
    assert result[0]["classification_provider"] == "openai"
    assert result[0]["classification_confidence_ai"] > 0
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


def test_company_classification_service_rules_detect_outsourcing_vendor():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Nearshore Vendor Co",
            "company_display": "Nearshore Vendor Co",
            "company_description": "Nearshore software outsourcing and staff augmentation services for global clients.",
            "industry": "Information Technology and Services",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] in {"consulting", "staffing"}
    assert result[0]["classification_provider"] == "rules"

def test_company_classification_service_detects_staffing_vendor_with_strong_result():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Talent Vendor Co",
            "company_display": "Talent Vendor Co",
            "company_description": "Global staffing and recruiting partner for technology teams.",
            "industry": "Staffing and Recruiting",
            "resolved_domain": "talentvendor.com",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "staffing"
    assert result[0]["classification_provider"] in {"rules", "openai"}
    assert result[0]["classification_confidence_ai"] >= 0.8


def test_company_classification_service_rules_detect_job_board_from_domain():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Jobgether",
            "company_display": "Jobgether",
            "company_description": "",
            "industry": "",
            "resolved_domain": "jobgether.com",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "job_board"
    assert result[0]["classification_provider"] == "rules"

def test_company_classification_service_normalizes_outsourcing_to_consulting():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Nearshore Vendor Co",
            "company_display": "Nearshore Vendor Co",
            "company_description": "Nearshore software outsourcing and staff augmentation services for global clients.",
            "industry": "Information Technology and Services",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "consulting"
    assert result[0]["classification_provider"] == "rules"

def test_company_classification_service_detects_competitor_from_brand_hint_without_llm():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Globant",
            "company_display": "Globant",
            "company_description": "Digital transformation services company.",
            "industry": "Computer Software",
            "resolved_domain": "globant.com",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "competitor"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] >= 0.9


def test_company_classification_service_detects_job_board_from_blocked_wrapper_domain():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Google Wrapper",
            "company_display": "Google Wrapper",
            "company_description": "",
            "industry": "",
            "resolved_domain": "google.com",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "job_board"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] >= 0.9


def test_company_classification_service_uses_rule_override_for_competitor_even_with_llm_available():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def classify_company(self, company_payload):
                    raise AssertionError("OpenAI no debería ejecutarse para competitor con regla fuerte")
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
            "company": "Globant",
            "company_display": "Globant",
            "company_description": "Digital transformation services company.",
            "industry": "Computer Software",
            "resolved_domain": "globant.com",
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "competitor"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] >= 0.9

def test_company_classification_service_uses_jobs_text_for_rules_without_llm():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Acme",
            "company_display": "Acme",
            "company_description": "",
            "industry": "",
            "jobs": [
                {
                    "title": "Senior Engineer",
                    "description": "Nearshore software outsourcing and staff augmentation services for global clients.",
                    "location": "Mexico",
                }
            ],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "consulting"
    assert result[0]["classification_provider"] == "rules"

def test_company_classification_service_keeps_unknown_for_placeholder_with_weak_evidence_without_llm():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Empresa Confidencial",
            "company_display": "Empresa Confidencial",
            "company_description": "",
            "industry": "",
            "resolved_domain": "",
            "linkedin_company_url": "",
            "jobs": [],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "unknown"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] == 0.0

def test_company_classification_service_keeps_unknown_for_generic_ambiguous_company_without_llm():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Generic Holdings",
            "company_display": "Generic Holdings",
            "company_description": "General business company.",
            "industry": "",
            "resolved_domain": "generic-holdings.example",
            "linkedin_company_url": "",
            "jobs": [
                {
                    "title": "Developer",
                    "description": "Generalist role",
                    "location": "Remote",
                }
            ],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "unknown"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] <= 0.2


def test_company_classification_service_detects_end_client_when_product_evidence_is_clear_without_llm():
    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={"no_llm": True},
    )
    control = ProviderControlService(ctx)
    control.initialize()

    service = CompanyClassificationService(ctx, control)

    companies = [
        {
            "company": "Acme Product",
            "company_display": "Acme Product",
            "company_description": "Builds software products and SaaS platforms for banks and insurers.",
            "industry": "Computer Software",
            "resolved_domain": "acmeproduct.com",
            "jobs": [
                {
                    "title": "Senior Backend Engineer",
                    "description": "Platform engineering for fintech product.",
                    "location": "Mexico",
                }
            ],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "end_client"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] >= 0.72

def test_company_classification_service_uses_rule_override_for_strong_end_client_even_with_llm_available():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def classify_company(self, company_payload):
                    raise AssertionError("OpenAI no debería ejecutarse para end_client con evidencia fuerte por reglas")
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
            "company": "Acme Product",
            "company_display": "Acme Product",
            "company_description": "Builds software products and SaaS platforms for banks and insurers.",
            "industry": "Computer Software",
            "resolved_domain": "acmeproduct.com",
            "jobs": [
                {
                    "title": "Senior Backend Engineer",
                    "description": "Platform engineering for fintech product.",
                    "location": "Mexico",
                }
            ],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "end_client"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] >= 0.72
    assert ctx.metrics["company_classification_rule_override_end_client"] == 1


def test_company_classification_service_skips_llm_for_low_evidence_unknown_when_rules_are_enough():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def classify_company(self, company_payload):
                    raise AssertionError("OpenAI no debería ejecutarse para unknown de evidencia débil")
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
            "company": "Empresa Confidencial",
            "company_display": "Empresa Confidencial",
            "company_description": "",
            "industry": "",
            "resolved_domain": "",
            "linkedin_company_url": "",
            "jobs": [],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["company_type_ai"] == "unknown"
    assert result[0]["classification_provider"] == "rules"
    assert result[0]["classification_confidence_ai"] == 0.0
    assert ctx.metrics["company_classification_llm_skipped_low_evidence"] == 1

def test_company_classification_service_does_not_force_end_client_override_when_evidence_is_only_partial():
    class DummyRegistry:
        def get_client(self, name):
            class DummyOpenAIClient:
                def classify_company(self, company_payload):
                    return {
                        "classification": "unknown",
                        "confidence": 0.35,
                        "provider": "openai",
                    }
            return DummyOpenAIClient()

    class DummyProviderControlService:
        def __init__(self):
            self.registry = DummyRegistry()

    class DummyProviderExecutionService:
        def execute(self, provider_name, operation_name, func, *args, **kwargs):
            return func(*args)

    ctx = RunContext.create(
        config={"providers": {"limits": {"openai": 5}}},
        flags={},
    )
    control = DummyProviderControlService()
    service = CompanyClassificationService(ctx, control)
    service.provider_execution_service = DummyProviderExecutionService()

    companies = [
        {
            "company": "Acme Maybe",
            "company_display": "Acme Maybe",
            "company_description": "Software company.",
            "industry": "Computer Software",
            "resolved_domain": "",
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "description": "",
                    "location": "Mexico",
                }
            ],
        }
    ]

    result = service.classify_companies(companies)

    assert len(result) == 1
    assert result[0]["classification_provider"] == "openai"
    assert result[0]["company_type_ai"] == "unknown"
    assert ctx.metrics.get("company_classification_rule_override_end_client", 0) == 0

