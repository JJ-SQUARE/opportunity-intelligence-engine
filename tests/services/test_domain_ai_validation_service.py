from oie.orchestration.run_context import RunContext
from oie.services.domain_ai_validation_service import DomainAIValidationService
from oie.services.provider_control_service import ProviderControlService


class _FakeOpenAIClient:
    def __init__(self, payload):
        self.payload = payload

    def complete_json(self, prompt):
        return self.payload


class _FakeRegistry:
    def __init__(self, client):
        self._client = client

    def get_client(self, name):
        if name == "openai":
            return self._client
        return None


class _FakePCS(ProviderControlService):
    def __init__(self, ctx, client):
        self.ctx = ctx
        self.registry = _FakeRegistry(client)


def test_validate_accepts_domain_from_ai():
    ctx = RunContext.create(config={"domain_resolution": {"domain_ai_validation_limit": 10}})
    pcs = _FakePCS(
        ctx,
        _FakeOpenAIClient(
            {
                "selected_domain": "sofka.com.co",
                "decision": "accepted",
                "confidence": 0.91,
                "reason": "official brand/domain alignment",
            }
        ),
    )
    svc = DomainAIValidationService(ctx, pcs)

    result = svc.validate(
        "Sofka Technologies",
        [
            {
                "domain": "sofka.com.co",
                "source": "serpapi_fallback",
                "score": 0.45,
                "title": "Sofka official site",
                "snippet": "Technology company",
                "serp_rank": 1,
            }
        ],
    )

    assert result["selected_domain"] == "sofka.com.co"
    assert result["decision"] == "accepted"
    assert result["confidence"] == 0.91


def test_validate_rejects_when_no_candidates():
    ctx = RunContext.create(config={})
    pcs = _FakePCS(ctx, _FakeOpenAIClient({}))
    svc = DomainAIValidationService(ctx, pcs)

    result = svc.validate("Acme", [])

    assert result["decision"] == "rejected"
    assert result["selected_domain"] is None


def test_validate_respects_limit():
    ctx = RunContext.create(config={"domain_resolution": {"domain_ai_validation_limit": 0}})
    pcs = _FakePCS(ctx, _FakeOpenAIClient({}))
    svc = DomainAIValidationService(ctx, pcs)

    result = svc.validate(
        "Acme",
        [{"domain": "acme.com", "source": "serpapi_fallback", "score": 0.50}],
    )

    assert result["decision"] == "review"
    assert result["reason"] == "validation_limit_reached"
