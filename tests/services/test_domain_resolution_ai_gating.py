from oie.orchestration.run_context import RunContext
from oie.services.domain_resolution_service import DomainResolutionService


class _FakeAIService:
    def __init__(self):
        self.calls = []

    def validate(self, company_name, candidates):
        self.calls.append((company_name, candidates))
        return {
            "selected_domain": candidates[0].get("domain"),
            "decision": "accepted",
            "confidence": 0.91,
            "reason": "accepted_by_test_ai",
        }


def test_ai_not_called_for_direct_aggregator_candidate():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    result = service._evaluate_best_candidate(
        company_name="Tenaris",
        candidates=[
            {
                "domain": "jobgether.com",
                "source": "apply_url",
                "serp_rank": None,
                "title": "",
                "snippet": "",
                "score": 0.55,
                "validation_status": "review",
            }
        ],
    )

    assert result["validation_status"] == "review"
    assert result["ai_validated"] == 0
    assert len(fake_ai.calls) == 0


def test_ai_called_for_review_candidate_from_serpapi_in_gray_zone():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    result = service._evaluate_best_candidate(
        company_name="Sofka Technologies",
        candidates=[
            {
                "domain": "sofka.com.co",
                "source": "serpapi_fallback",
                "serp_rank": 1,
                "title": "Sofka official site",
                "snippet": "Technology company",
                "score": 0.55,
                "validation_status": "review",
            }
        ],
    )

    assert result["ai_validated"] == 1
    assert result["validation_status"] == "accepted"
    assert result["domain"] == "sofka.com.co"
    assert len(fake_ai.calls) == 1


def test_ai_not_called_for_low_score_candidate():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    should_send = service._should_send_candidate_to_ai(
        "Weak Company",
        {
            "domain": "weak-example.com",
            "source": "serpapi_fallback",
        },
        "review",
        0.30,
    )

    assert should_send is False
    assert len(fake_ai.calls) == 0


def test_ai_called_for_rejected_serpapi_candidate_with_soft_brand_signal():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    should_send = service._should_send_candidate_to_ai(
        "Inmediatum Technology Services",
        {
            "domain": "inetum.com",
            "source": "serpapi_fallback",
            "serp_rank": 1,
            "title": "Inetum - digital services",
            "snippet": "Official technology services company site",
            "confidence_brand_match": False,
            "confidence_reasons": ["text_core_hits_1", "serp_rank_1", "source_serpapi_fallback"],
        },
        "rejected",
        0.34,
    )

    assert should_send is True


def test_ai_not_called_for_rejected_serpapi_candidate_without_soft_signal():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    should_send = service._should_send_candidate_to_ai(
        "Generic Company",
        {
            "domain": "random-example.com",
            "source": "serpapi_fallback",
            "serp_rank": 1,
            "title": "Welcome",
            "snippet": "Official website",
            "confidence_brand_match": False,
            "confidence_reasons": ["source_serpapi_fallback", "serp_rank_1"],
        },
        "rejected",
        0.34,
    )

    assert should_send is False


def test_ai_not_called_for_high_score_candidate():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    should_send = service._should_send_candidate_to_ai(
        "Strong Company",
        {
            "domain": "strong-example.com",
            "source": "serpapi_fallback",
        },
        "review",
        0.90,
    )

    assert should_send is False
    assert len(fake_ai.calls) == 0

def test_ai_called_for_suspicious_high_score_subdomain_review():
    ctx = RunContext.create(
        config={
            "domain_resolution": {
                "review_threshold": 0.45,
                "auto_accept_threshold": 0.80,
            }
        }
    )
    service = DomainResolutionService(ctx, provider_control_service=None)
    fake_ai = _FakeAIService()
    service.domain_ai_validation_service = fake_ai

    should_send = service._should_send_candidate_to_ai(
        "Rimutee",
        {
            "domain": "beta.rimutee.com",
            "source": "serpapi_fallback",
        },
        "review",
        0.83,
    )

    assert should_send is True

