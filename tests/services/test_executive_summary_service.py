from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.services.executive_summary_service import ExecutiveSummaryService


def test_executive_summary_service_builds_and_writes_summary(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )
    service = ExecutiveSummaryService(ctx)

    companies = [
        {
            "company_key": "cmp_a",
            "company_display": "Acme Inc.",
            "opportunity_score": 42,
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.9,
            "resolved_domain": "acme.com",
            "score_openings": 16,
            "score_remote": 8,
            "score_contractor": 6,
            "score_multi_source": 10,
            "score_company_type": 2,
        }
    ]
    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Jane Doe",
            "contact_title": "CTO",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/jane",
            "lead_source": "apollo_people",
            "lead_confidence": 0.9,
            "lead_relevance_score": 160,
        }
    ]
    ctx.metrics["jobs_after_dedupe"] = 5
    ctx.metrics["companies_enriched"] = 1
    ctx.metrics["suspected_duplicates_report_count"] = 2

    summary = service.build_summary(companies, leads)
    output_path = service.write_summary(summary)

    assert summary["companies_count"] == 1
    assert summary["leads_count"] == 1
    assert summary["top_companies"][0]["company_display"] == "Acme Inc."
    assert summary["top_companies"][0]["classification_confidence_ai"] == 0.9
    assert summary["top_companies"][0]["score_breakdown"]["score_openings"] == 16
    assert summary["top_leads"][0]["contact_name"] == "Jane Doe"
    assert summary["top_leads"][0]["lead_relevance_score"] == 160
    assert ctx.paths["executive_summary_json"] == output_path
    assert "output_dir" in ctx.paths
    assert Path(output_path).exists()
    assert Path(output_path).parent == Path(ctx.paths["output_dir"])
