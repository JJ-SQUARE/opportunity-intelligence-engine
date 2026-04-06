from pathlib import Path

from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator
from oie.orchestration.run_context import RunContext


def test_pipeline_orchestrator_e2e_controlled_run(tmp_path):
    outputs_path = tmp_path / "outputs"
    db_path = tmp_path / "oie_test.db"
    masters_path = tmp_path / "masters"
    cache_path = tmp_path / "http_cache"

    ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(outputs_path)},
            "masters": {"path": str(masters_path)},
            "cache": {"base_dir": str(cache_path)},
            "sources": {
                "google_jobs": {"enabled": True},
            },
            "providers": {
                "limits": {
                    "serpapi": 5,
                    "apollo": 5,
                    "hunter": 5,
                    "openai": 5,
                },
                "clients": {
                    "apollo": {"api_key": "fake-apollo"},
                    "hunter": {"api_key": "fake-hunter"},
                    "openai": {"api_key": "fake-openai"},
                    "serpapi": {"api_key": "fake-serpapi"},
                },
            },
        },
        flags={},
    )

    orchestrator = PipelineOrchestrator(ctx)

    orchestrator.collection_service.collect = lambda: [
        {
            "title": "Backend Engineer",
            "company": "Acme Inc.",
            "location": "Remote",
            "job_url": "https://acme.com/jobs/1",
            "apply_url": "https://acme.com/apply/1",
            "description": "Python backend role",
            "source": "google_jobs",
            "detected_at": "2026-03-10",
        },
        {
            "title": "Data Engineer",
            "company": "Beta Inc.",
            "location": "Remote",
            "job_url": "https://beta.com/jobs/2",
            "apply_url": "https://beta.com/apply/2",
            "description": "Data platform role",
            "source": "linkedin_serpapi",
            "detected_at": "2026-03-10",
        },
    ]

    orchestrator.domain_resolution_service.resolve_domains = lambda companies: [
        {
            **company,
            "resolved_domain": (
                "acme.com" if "Acme" in company.get("company", "") else "beta.com"
            ),
        }
        for company in companies
    ]

    orchestrator.company_enrichment_service.enrich_companies = lambda companies: [
        {
            **company,
            "industry": "Software",
            "company_size": "51-200",
            "linkedin_url": f"https://linkedin.com/company/{company.get('company_normalized', 'company')}",
            "company_description": "Test company",
        }
        for company in companies
    ]

    orchestrator.company_classification_service.classify_companies = lambda companies: [
        {
            **company,
            "company_type_ai": "end_client",
            "classification_confidence_ai": 0.9,
            "classification_provider": "openai",
        }
        for company in companies
    ]

    orchestrator.lead_generation_service.generate_leads = lambda companies: [
        {
            "company_key": company["company_key"],
            "contact_name": f"{company['company_display']} Contact",
            "contact_title": "CTO",
            "email": f"cto@{company['resolved_domain']}",
            "linkedin_url": "https://linkedin.com/in/test",
            "lead_source": "apollo_people",
        }
        for company in companies
    ]

    result = orchestrator.run()

    assert result["status"] == "company_pipeline_completed"
    assert result["jobs_count"] == 2
    assert result["companies_count"] == 2
    assert result["leads_count"] == 2

    assert result["db_path"] is not None
    assert result["suspected_duplicates_report"] is not None
    assert result["domain_review_queue_csv"] is not None
    assert result["companies_export"] is not None
    assert result["jobs_export"] is not None
    assert result["leads_export"] is not None
    assert result["executive_summary_json"] is not None
    assert result["run_readiness_report_json"] is not None
    assert result["run_metrics_summary_json"] is not None
    assert result["run_metrics_summary"] is not None
    assert result["run_analytics_json"] is not None
    assert result["run_analytics"] is not None
    assert result["collector_metrics_json"] is not None
    assert result["collector_contribution_metrics_json"] is not None
    assert result["collector_roi_metrics_json"] is not None

    assert result["run_metrics_summary"]["jobs_after_dedupe"] == 2
    assert result["run_metrics_summary"]["companies_detected"] == 2

    assert result["run_analytics"]["top_leads"][0]["contact_title"] == "CTO"
    assert result["run_analytics"]["top_leads"][0]["lead_source"] == "apollo_people"
    assert result["executive_summary"]["top_leads"][0]["contact_title"] == "CTO"

    assert result["historical_company_hiring_csv"] is not None
    assert result["historical_growth_summary_csv"] is not None
    assert result["historical_summary_json"] is not None
    assert result["market_trends_by_source_csv"] is not None
    assert result["market_trends_by_location_csv"] is not None
    assert result["market_new_companies_by_source_csv"] is not None
    assert result["market_trends_summary_json"] is not None
    assert result["market_segmented_companies_csv"] is not None
    assert result["market_segment_summary_csv"] is not None
    assert result["market_segment_summary_json"] is not None
    assert result["provider_operation_metrics_csv"] is not None
    assert result["provider_operation_metrics_json"] is not None

    assert Path(result["db_path"]).exists()
    assert Path(result["suspected_duplicates_report"]).exists()
    assert Path(result["domain_review_queue_csv"]).exists()
    assert Path(result["companies_export"]).exists()
    assert Path(result["jobs_export"]).exists()
    assert Path(result["leads_export"]).exists()
    assert Path(result["executive_summary_json"]).exists()
    assert Path(result["run_readiness_report_json"]).exists()
    assert Path(result["run_metrics_summary_json"]).exists()
    assert Path(result["run_analytics_json"]).exists()
    assert Path(result["collector_metrics_json"]).exists()
    assert Path(result["collector_contribution_metrics_json"]).exists()
    assert Path(result["collector_roi_metrics_json"]).exists()
    assert Path(result["historical_company_hiring_csv"]).exists()
    assert Path(result["historical_growth_summary_csv"]).exists()
    assert Path(result["historical_summary_json"]).exists()
    assert Path(result["market_trends_by_source_csv"]).exists()
    assert Path(result["market_trends_by_location_csv"]).exists()
    assert Path(result["market_new_companies_by_source_csv"]).exists()
    assert Path(result["market_trends_summary_json"]).exists()
    assert Path(result["market_segmented_companies_csv"]).exists()
    assert Path(result["market_segment_summary_csv"]).exists()
    assert Path(result["market_segment_summary_json"]).exists()
    assert Path(result["provider_operation_metrics_csv"]).exists()
    assert Path(result["provider_operation_metrics_json"]).exists()

    assert "output_dir" in ctx.paths
    assert Path(result["suspected_duplicates_report"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["domain_review_queue_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["companies_export"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["jobs_export"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["leads_export"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["executive_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["run_readiness_report_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["run_metrics_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["run_analytics_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["collector_metrics_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["collector_contribution_metrics_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["collector_roi_metrics_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["historical_company_hiring_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["historical_growth_summary_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["historical_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_trends_by_source_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_trends_by_location_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_new_companies_by_source_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_trends_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_segmented_companies_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_segment_summary_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["market_segment_summary_json"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["provider_operation_metrics_csv"]).parent == Path(ctx.paths["output_dir"])
    assert Path(result["provider_operation_metrics_json"]).parent == Path(ctx.paths["output_dir"])
