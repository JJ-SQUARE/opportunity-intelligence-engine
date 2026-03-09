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
            "resolved_domain": "acme.com",
        }
    ]
    leads = [
        {
            "company_key": "cmp_a",
            "contact_name": "Jane Doe",
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
    assert Path(output_path).exists()
