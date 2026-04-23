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
            "domain_validation_status": "accepted",
            "linkedin_company_url": "https://linkedin.com/company/acme",
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
            "email_quality_score": 95,
            "lead_capture_reason": "apollo_match | title:CTO | email_quality:95",
            "lead_relevance_score": 197,
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
    assert summary["top_companies"][0]["reachability_ready"] is True
    assert summary["top_companies"][0]["icp_bucket"] == "possible_icp"
    assert summary["icp_summary"]["reachability_ready_companies"] == 1
    assert summary["icp_summary"]["strong_icp_companies"] == 0
    assert summary["top_leads"][0]["contact_name"] == "Jane Doe"
    assert summary["top_leads"][0]["lead_relevance_score"] == 197
    assert summary["top_leads"][0]["email_quality_score"] == 95
    assert "apollo_match" in summary["top_leads"][0]["lead_capture_reason"]
    assert ctx.paths["executive_summary_json"] == output_path
    assert "output_dir" in ctx.paths
    assert Path(output_path).exists()
    assert Path(output_path).parent == Path(ctx.paths["output_dir"])


def test_executive_summary_service_prefers_higher_quality_lead_on_tie(tmp_path):
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
            "contact_name": "Lower Quality",
            "contact_title": "VP Engineering",
            "email": "low@acme.com",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.5,
            "email_quality_score": 60,
            "lead_capture_reason": "hunter_match | title:VP Engineering | email_quality:60",
            "lead_relevance_score": 139,
            "lead_score_source": 15,
        },
        {
            "company_key": "cmp_a",
            "contact_name": "Higher Quality",
            "contact_title": "VP Engineering",
            "email": "high@acme.com",
            "linkedin_url": "",
            "lead_source": "hunter_domain_search",
            "lead_confidence": 0.5,
            "email_quality_score": 90,
            "lead_capture_reason": "hunter_match | title:VP Engineering | email_quality:90",
            "lead_relevance_score": 139,
            "lead_score_source": 15,
        },
    ]

    summary = service.build_summary(companies, leads)

    assert summary["top_leads"][0]["contact_name"] == "Higher Quality"
    assert summary["top_leads"][0]["email_quality_score"] == 90



def test_executive_summary_service_uses_shared_commercial_signals(tmp_path):
    ctx = RunContext.create(
        config={"outputs": {"path": str(tmp_path / "outputs")}},
        flags={},
    )
    service = ExecutiveSummaryService(ctx)

    companies = [
        {
            "company_key": "cmp_strong",
            "company_display": "Strong Co",
            "opportunity_score": 72,
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.98,
            "resolved_domain": "strongco.com",
            "domain_validation_status": "accepted",
            "linkedin_company_url": "",
            "score_openings": 18,
            "score_remote": 8,
            "score_contractor": 4,
            "score_multi_source": 8,
            "score_company_type": 20,
        }
    ]

    summary = service.build_summary(companies, [])

    assert summary["top_companies"][0]["icp_bucket"] == "strong_icp"
    assert summary["top_companies"][0]["reachability_ready"] is True
    assert summary["icp_summary"]["strong_icp_companies"] == 1
    assert summary["icp_summary"]["strong_icp_with_reachability"] == 1
    assert summary["top_companies"][0]["suggested_outreach_channel"] == "website_only"
    assert summary["top_companies"][0]["outreach_status"] == "research_needed"
    assert summary["top_companies"][0]["commercial_bucket"] == "icp_target"
    assert summary["top_companies"][0]["commercial_priority_score"] >= 72
