from oie.orchestration.run_context import RunContext
from oie.services.job_intelligence_service import JobIntelligenceService


class DummyRegistry:
    def get_client(self, name):
        class DummyOpenAIClient:
            def analyze_job_intelligence(self, job):
                return {
                    "is_real_job": True,
                    "is_contaminated": False,
                    "real_company_name": "Acme Inc.",
                    "confidence": 0.92,
                    "usable_for_scoring": True,
                    "role": "Backend Engineer",
                    "seniority": "senior",
                    "tech_stack": ["Python", "AWS"],
                    "budget": "USD 5000",
                    "workplace_type": "remote",
                    "commercial_signals": ["cloud modernization"],
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


def test_job_intelligence_service_analyzes_serp_jobs_with_ai():
    ctx = RunContext.create(config={}, flags={})
    service = JobIntelligenceService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    jobs = [
        {
            "title": "Senior Backend Engineer",
            "company": "Acme",
            "source": "linkedin_serpapi",
            "description": "Python and AWS role.",
        }
    ]

    result = service.enrich_jobs(jobs)

    assert len(result) == 1
    assert result[0]["job_intelligence"]["real_company_name"] == "Acme Inc."
    assert result[0]["job_intelligence"]["confidence"] == 0.92
    assert result[0]["job_intelligence"]["usable_for_scoring"] is True
    assert result[0]["job_intelligence"]["tech_stack"] == ["Python", "AWS"]
    assert service.provider_execution_service.calls == [
        ("openai", "analyze_job_intelligence")
    ]
    assert ctx.metrics["job_intelligence_analyzed"] == 1
    assert ctx.metrics["job_intelligence_completed"] is True


def test_job_intelligence_service_does_not_call_ai_for_trusted_source():
    ctx = RunContext.create(config={}, flags={})
    service = JobIntelligenceService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    jobs = [
        {
            "title": "Backend Engineer",
            "company": "Beta",
            "source": "greenhouse",
            "description": "Trusted ATS job.",
        }
    ]

    result = service.enrich_jobs(jobs)

    assert result[0]["job_intelligence"]["real_company_name"] == "Beta"
    assert result[0]["job_intelligence"]["job_intelligence_provider"] == "fallback"
    assert result[0]["job_intelligence"]["job_intelligence_mode"] == "trusted_source_not_analyzed"
    assert service.provider_execution_service.calls == []


def test_job_intelligence_service_overrides_company_when_ai_is_confident():
    ctx = RunContext.create(config={}, flags={})
    service = JobIntelligenceService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    result = service.enrich_jobs([
        {
            "title": "Senior Backend Engineer",
            "company": "Wrong Snippet Company",
            "source": "linkedin_serpapi",
            "description": "Backend role at Acme Inc.",
        }
    ])

    assert result[0]["company"] == "Acme Inc."
    assert result[0]["original_company"] == "Wrong Snippet Company"
    assert result[0]["company_ai_overridden"] is True
    assert result[0]["job_ai_usable_for_scoring"] is True
    assert result[0]["job_ai_is_contaminated"] is False
    assert result[0]["job_ai_confidence"] == 0.92


def test_job_intelligence_service_tracks_company_override_metric():
    ctx = RunContext.create(config={}, flags={})
    service = JobIntelligenceService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    service.enrich_jobs([
        {
            "title": "Senior Backend Engineer",
            "company": "Wrong Snippet Company",
            "source": "linkedin_serpapi",
            "description": "Backend role at Acme Inc.",
        }
    ])

    assert ctx.metrics["job_intelligence_company_overrides"] == 1


def test_job_intelligence_service_respects_max_jobs_to_analyze_cap():
    ctx = RunContext.create(
        config={"job_intelligence": {"max_jobs_to_analyze": 1}},
        flags={},
    )
    service = JobIntelligenceService(ctx, DummyProviderControlService())
    service.provider_execution_service = DummyProviderExecutionService()

    result = service.enrich_jobs([
        {
            "title": "Senior Backend Engineer",
            "company": "Acme",
            "source": "linkedin_serpapi",
            "description": "Python and AWS role.",
        },
        {
            "title": "Senior Backend Engineer",
            "company": "Beta",
            "source": "linkedin_serpapi",
            "description": "Java and AWS role.",
        },
    ])

    assert len(service.provider_execution_service.calls) == 1
    assert ctx.metrics["job_intelligence_analyzed"] == 1
    assert ctx.metrics["jobs_analyzed_by_ai"] == 1
    assert ctx.metrics["job_intelligence_max_jobs_to_analyze"] == 1
    assert ctx.metrics["job_intelligence_cap_reached"] is True
    assert result[1]["job_intelligence"]["job_intelligence_mode"] == "job_intelligence_cap_reached"
