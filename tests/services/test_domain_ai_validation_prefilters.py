from oie.orchestration.run_context import RunContext
from oie.services.domain_ai_validation_service import DomainAIValidationService


class _DummyRegistry:
    def __init__(self, client):
        self._client = client

    def get_client(self, name):
        return self._client


class _DummyProviderControlService:
    def __init__(self, client):
        self.registry = _DummyRegistry(client)


class _DummyProviderExecutionService:
    def execute(self, provider_name, operation_name, func, *args, **kwargs):
        return func(*args)


class _ClientReturningExternalDomain:
    def validate_domain_candidates(self, payload):
        return {
            "selected_domain": "outside-example.com",
            "decision": "accepted",
            "confidence": 0.95,
            "reason": "hallucinated_domain",
        }


class _ClientReturningAcceptedCandidate:
    def __init__(self):
        self.calls = 0

    def validate_domain_candidates(self, payload):
        self.calls += 1
        return {
            "selected_domain": payload["candidates"][0]["domain"],
            "decision": "accepted",
            "confidence": 0.91,
            "reason": "accepted_by_test_client",
        }


def test_domain_ai_validation_skips_prefilter_for_job_board_candidate():
    client = _ClientReturningAcceptedCandidate()
    ctx = RunContext.create(config={}, flags={})
    service = DomainAIValidationService(ctx, _DummyProviderControlService(client))
    service.provider_execution_service = _DummyProviderExecutionService()

    result = service.validate(
        "Tenaris",
        [
            {
                "domain": "jobgether.com",
                "source": "apply_url",
                "title": "",
                "snippet": "",
                "confidence_reasons": [],
            }
        ],
    )

    assert result["decision"] == "review"
    assert result["reason"] == "prefilter_rejected_candidates"
    assert ctx.metrics["domain_ai_validation_skipped_prefilter"] == 1
    assert client.calls == 0


def test_domain_ai_validation_rejects_selected_domain_outside_candidate_whitelist():
    ctx = RunContext.create(config={}, flags={})
    service = DomainAIValidationService(ctx, _DummyProviderControlService(_ClientReturningExternalDomain()))
    service.provider_execution_service = _DummyProviderExecutionService()

    result = service.validate(
        "Tenaris",
        [
            {
                "domain": "tenaris.com",
                "source": "serpapi_fallback",
                "title": "Tenaris Official Website",
                "snippet": "Official site",
                "confidence_reasons": ["text_core_hits_1"],
            }
        ],
    )

    assert result["decision"] == "rejected"
    assert result["reason"] == "selected_domain_not_in_candidates"
    assert result["selected_domain"] is None


def test_domain_ai_validation_calls_openai_for_eligible_candidate():
    client = _ClientReturningAcceptedCandidate()
    ctx = RunContext.create(config={}, flags={})
    service = DomainAIValidationService(ctx, _DummyProviderControlService(client))
    service.provider_execution_service = _DummyProviderExecutionService()

    result = service.validate(
        "Tenaris",
        [
            {
                "domain": "tenaris.com",
                "source": "serpapi_fallback",
                "title": "Tenaris Official Website",
                "snippet": "Official site",
                "confidence_reasons": ["text_core_hits_1"],
            }
        ],
    )

    assert result["decision"] == "accepted"
    assert result["selected_domain"] == "tenaris.com"
    assert client.calls == 1
    assert ctx.metrics["domain_ai_validation_attempted"] == 1

def test_domain_ai_validation_limit_takes_precedence_over_prefilter():
    client = _ClientReturningAcceptedCandidate()
    ctx = RunContext.create(
        config={"domain_resolution": {"domain_ai_validation_limit": 0}},
        flags={},
    )
    service = DomainAIValidationService(ctx, _DummyProviderControlService(client))
    service.provider_execution_service = _DummyProviderExecutionService()

    result = service.validate(
        "Acme",
        [
            {
                "domain": "acme.com",
                "source": "serpapi_fallback",
                "score": 0.50,
            }
        ],
    )

    assert result["decision"] == "review"
    assert result["reason"] == "validation_limit_reached"
    assert client.calls == 0

