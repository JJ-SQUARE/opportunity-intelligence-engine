import json
from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.orchestration.pipeline_orchestrator import PipelineOrchestrator


def test_orchestrator_has_initial_stages():
    ctx = RunContext.create(config={})
    orchestrator = PipelineOrchestrator(ctx)

    assert orchestrator.collection_service is not None
    assert orchestrator.normalization_service is not None
    assert orchestrator.job_dedup_service is not None
    assert orchestrator.hiring_signals_service is not None
    assert orchestrator.company_identity_service is not None
    assert orchestrator.company_identity_ai_service is not None
    assert orchestrator.domain_resolution_service is not None
    assert orchestrator.company_classification_service is not None
    assert orchestrator.opportunity_scoring_service is not None
    assert orchestrator.persistence_service is not None
    assert orchestrator.provider_control_service is not None


def test_orchestrator_splits_benchmark_competitors_from_config():
    ctx = RunContext.create(
        config={
            "benchmark": {
                "competitors": [
                    "bairesdev",
                    "globant.com",
                ]
            }
        }
    )
    orchestrator = PipelineOrchestrator(ctx)

    companies = [
        {
            "company_key": "cmp_bairesdev",
            "company_display": "BairesDev",
            "company_normalized": "bairesdev",
            "resolved_domain": "bairesdev.com",
            "linkedin_company_url": "https://linkedin.com/company/bairesdev",
        },
        {
            "company_key": "cmp_acme",
            "company_display": "Acme Bank",
            "company_normalized": "acme bank",
            "resolved_domain": "acmebank.com",
            "linkedin_company_url": "https://linkedin.com/company/acmebank",
        },
    ]

    actionable, benchmark = orchestrator._split_benchmark_competitors(companies)

    assert len(actionable) == 1
    assert len(benchmark) == 1
    assert actionable[0]["company_key"] == "cmp_acme"
    assert benchmark[0]["company_key"] == "cmp_bairesdev"
    assert benchmark[0]["benchmark_only"] is True
    assert benchmark[0]["company_type_ai"] == "competitor"
    assert benchmark[0]["classification_confidence_ai"] == 1.0
    assert benchmark[0]["classification_source"] == "config_benchmark_competitor"
    assert ctx.metrics["benchmark_competitors_detected"] == 1


def test_orchestrator_skips_benchmark_competitors_for_lead_generation():
    ctx = RunContext.create(config={})
    orchestrator = PipelineOrchestrator(ctx)

    companies = [
        {
            "company_key": "cmp_comp",
            "company_display": "Competitor Co",
            "company_type_ai": "competitor",
            "benchmark_only": True,
        },
        {
            "company_key": "cmp_client",
            "company_display": "Client Co",
            "company_type_ai": "end_client",
        },
    ]

    filtered = orchestrator._companies_for_lead_generation(companies)

    assert len(filtered) == 1
    assert filtered[0]["company_key"] == "cmp_client"
    assert ctx.metrics["benchmark_competitors_skipped_for_leads"] == 1

def test_orchestrator_uses_top_multiple_leads_per_company_config():
    ctx = RunContext.create(
        config={
            "lead_generation": {
                "max_selected_leads_per_company": 2,
            }
        }
    )
    orchestrator = PipelineOrchestrator(ctx)

    calls = {}

    orchestrator.provider_control_service.initialize = lambda: None
    orchestrator.provider_control_service.sync_budget_metrics = lambda: None
    orchestrator.run_company_pipeline = lambda: ([], [{"company_key": "cmp_a"}], [])
    orchestrator._companies_for_lead_generation = lambda companies: companies
    orchestrator.lead_generation_service.generate_leads = lambda companies: [
        {"company_key": "cmp_a", "contact_name": "Lead 1", "lead_relevance_score": 95},
        {"company_key": "cmp_a", "contact_name": "Lead 2", "lead_relevance_score": 85},
        {"company_key": "cmp_a", "contact_name": "Lead 3", "lead_relevance_score": 75},
    ]
    orchestrator.lead_ranking_service.rank_leads = lambda leads: leads

    def fake_select_top_leads_per_company(leads, max_leads_per_company=3):
        calls["max_leads_per_company"] = max_leads_per_company
        return leads[:max_leads_per_company]

    orchestrator.lead_ranking_service.select_top_leads_per_company = fake_select_top_leads_per_company
    orchestrator.master_dedup_service.dedupe_leads_against_master = lambda leads: (leads, [])

    orchestrator.persistence_service.persist_run_snapshot = lambda **kwargs: None
    orchestrator.master_data_service.append_jobs = lambda jobs: 0
    orchestrator.master_data_service.append_companies = lambda companies: 0
    orchestrator.master_data_service.append_leads = lambda leads: 0
    orchestrator.master_dedup_service.build_suspected_duplicates_report = lambda **kwargs: []
    orchestrator.duplicate_report_service.write_suspected_duplicates_report = lambda rows: None
    orchestrator.domain_review_queue_service.export_csv = lambda companies: None
    orchestrator.db_export_service.export_all = lambda: None

    orchestrator.opportunity_dataset_service.build_dataset = lambda: []
    orchestrator.opportunity_dataset_service.build_top_opportunities = lambda limit=25: []
    orchestrator.opportunity_dataset_export_service.export_dataset = lambda dataset: None
    orchestrator.opportunity_dataset_export_service.export_top_dataset = lambda dataset: None
    orchestrator.outbound_export_service.export_all = lambda: None
    orchestrator.outbound_export_service.push_hubspot_payloads = lambda provider_execution_service: {"pushed": False}

    orchestrator.executive_summary_service.build_summary = lambda companies, leads: {}
    orchestrator.executive_summary_service.write_summary = lambda summary: None

    orchestrator.historical_intelligence_service.build_company_hiring_history = lambda: []
    orchestrator.historical_intelligence_service.build_company_growth_summary = lambda: []
    orchestrator.historical_export_service.export_company_history = lambda rows: None
    orchestrator.historical_export_service.export_growth_summary = lambda rows: None
    orchestrator.historical_export_service.export_summary_json = lambda rows: None

    orchestrator.market_trends_service.build_source_trends = lambda: []
    orchestrator.market_trends_service.build_country_trends = lambda: []
    orchestrator.market_trends_service.build_new_companies_by_source = lambda: []
    orchestrator.market_trends_service.build_summary = lambda: {}
    orchestrator.market_trends_export_service.export_source_trends = lambda rows: None
    orchestrator.market_trends_export_service.export_country_trends = lambda rows: None
    orchestrator.market_trends_export_service.export_new_companies_by_source = lambda rows: None
    orchestrator.market_trends_export_service.export_summary_json = lambda summary: None

    orchestrator.market_segmentation_service.segment_companies = lambda companies: []
    orchestrator.market_segmentation_service.build_segment_summary = lambda companies: {}
    orchestrator.market_segmentation_export_service.export_segmented_companies = lambda rows: None
    orchestrator.market_segmentation_export_service.export_segment_summary = lambda summary: None
    orchestrator.market_segmentation_export_service.export_segment_summary_json = lambda summary: None

    orchestrator.collector_metrics_service.build_metrics = lambda unique_jobs, companies: {}
    orchestrator.collector_metrics_export_service.export_json = lambda metrics: None

    orchestrator.collector_contribution_service.build_contribution_metrics = lambda unique_jobs, companies, best_leads: []
    orchestrator.collector_contribution_export_service.export_csv = lambda rows: None
    orchestrator.collector_contribution_export_service.export_json = lambda rows: None

    orchestrator.collector_roi_service.build_roi_metrics = lambda **kwargs: []
    orchestrator.collector_roi_export_service.export_csv = lambda rows: None
    orchestrator.collector_roi_export_service.export_json = lambda rows: None

    orchestrator.provider_operation_metrics_service.build_rows = lambda: []
    orchestrator.provider_operation_metrics_export_service.export_csv = lambda rows: None
    orchestrator.provider_operation_metrics_export_service.export_json = lambda rows: None

    orchestrator.run_readiness_service.build_report = lambda **kwargs: {}
    orchestrator.run_readiness_export_service.export_json = lambda report: None

    orchestrator.run_metrics_summary_service.build_summary = lambda: {}
    orchestrator.run_metrics_summary_export_service.export_json = lambda summary: None

    orchestrator.run_analytics_service.build_analytics = lambda **kwargs: {}
    orchestrator.run_analytics_export_service.export_json = lambda analytics: None

    result = orchestrator.run()

    manifest = json.loads(Path(ctx.paths["manifest_path"]).read_text(encoding="utf-8"))

    assert calls["max_leads_per_company"] == 2
    assert ctx.metrics["pipeline_selected_leads_per_company"] == 2
    assert result["leads_count"] == 2
    assert manifest["status"] == "completed"

def test_orchestrator_enriches_before_classification_and_scoring():
    ctx = RunContext.create(config={})
    orchestrator = PipelineOrchestrator(ctx)

    call_order = []

    orchestrator.run_initial_stages = lambda: []
    orchestrator.master_dedup_service.dedupe_jobs_against_master = lambda jobs: (jobs, [])
    orchestrator.hiring_signals_service.aggregate_by_company = lambda jobs: [
        {"company_key": "cmp_a", "company_display": "Go Sinergia"}
    ]
    orchestrator._split_benchmark_competitors = lambda companies: (companies, [])
    orchestrator.company_identity_ai_service.enrich_companies = lambda companies: (
        call_order.append("identity_ai") or companies
    )

    orchestrator.domain_resolution_service.resolve_domains = lambda companies: (
        call_order.append("domain_resolution") or companies
    )
    orchestrator.company_identity_service.enrich_company_identity = lambda companies: (
        call_order.append("identity") or companies
    )
    orchestrator.company_enrichment_service.enrich_companies = lambda companies: (
        call_order.append("enrichment") or companies
    )
    orchestrator.company_classification_service.classify_companies = lambda companies: (
        call_order.append("classification") or companies
    )
    orchestrator.opportunity_scoring_service.score_companies = lambda companies: (
        call_order.append("scoring") or companies
    )
    orchestrator._limit_companies_for_run = lambda companies: (
        call_order.append("limit") or companies
    )
    orchestrator._attach_company_keys_to_jobs = lambda jobs, companies: []

    jobs, companies, duplicate_jobs = orchestrator.run_company_pipeline()

    assert jobs == []
    assert companies == [{"company_key": "cmp_a", "company_display": "Go Sinergia"}]
    assert duplicate_jobs == []
    assert call_order == [
        "identity_ai",
        "domain_resolution",
        "identity",
        "enrichment",
        "classification",
        "scoring",
        "limit",
    ]

