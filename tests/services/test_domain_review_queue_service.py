from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.domain_review_queue_service import DomainReviewQueueService


def test_domain_review_queue_service_exports_review_rows(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path)}},
        flags={},
    )
    ctx.paths["output_dir"] = str(tmp_path / "run_output")

    service = DomainReviewQueueService(ctx)

    companies = [
        {
            "company_key": "cmp_1",
            "company_display": "Quid Solutions",
            "company_normalized": "quid solutions",
            "domain_candidate": "jobgether.com",
            "resolved_domain": None,
            "domain_source": "apply_url",
            "domain_confidence": 0.55,
            "domain_validation_status": "review",
            "domain_review_required": 1,
            "domain_ai_validated": 1,
            "domain_ai_decision": "review",
            "domain_ai_confidence": 0.55,
            "domain_ai_reason": "aggregator_domain",
            "apply_url": "https://jobgether.com/offer/123",
            "url": None,
            "title": "Software Architect at Quid Solutions",
            "snippet": "Remote role",
        },
        {
            "company_key": "cmp_2",
            "company_display": "Tenaris",
            "company_normalized": "tenaris",
            "domain_candidate": "tenaris.com",
            "resolved_domain": "tenaris.com",
            "domain_source": "serpapi_fallback",
            "domain_confidence": 1.0,
            "domain_validation_status": "accepted",
        },
    ]

    out_path = service.export_csv(companies)

    assert Path(out_path).exists()
    content = Path(out_path).read_text(encoding="utf-8")
    assert "Quid Solutions" in content
    assert "Tenaris" not in content
    assert ctx.metrics["domain_review_queue_count"] == 1
    assert ctx.metrics["domain_review_queue_written"] == 1
