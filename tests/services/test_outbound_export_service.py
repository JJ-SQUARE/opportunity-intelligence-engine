from pathlib import Path

from oie.orchestration.run_context import RunContext
from oie.persistence.sqlite import initialize_database, get_connection
from oie.services.outbound_export_service import OutboundExportService


def test_outbound_export_service_exports_commercial_pipeline_and_apollo_import(tmp_path):
    db_path = tmp_path / "oie.db"
    outputs_path = tmp_path / "outputs"

    ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(outputs_path)},
            "hubspot": {
                "owner_id": "owner_123",
                "target_account": "tekton_enterprise_sales",
                "source_tag": "OIE",
                "max_contacts_per_company": 3,
            },
        },
        flags={},
    )
    ctx.paths["output_dir"] = str(outputs_path / ctx.run_id)

    initialize_database(str(db_path))
    conn = get_connection(str(db_path))
    try:
        conn.execute(
            """
            INSERT INTO companies (
                company_key,
                company_display,
                company_normalized,
                resolved_domain,
                domain_source,
                domain_confidence,
                domain_candidate,
                domain_validation_status,
                domain_review_required,
                domain_ai_decision,
                industry,
                employee_range,
                company_size,
                linkedin_company_url,
                company_description,
                company_type_ai,
                classification_confidence_ai
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cmp_acme",
                "Acme",
                "acme",
                "acme.com",
                "serpapi_fallback",
                0.92,
                "acme.com",
                "accepted",
                0,
                "accepted",
                "Software",
                "51-200",
                "51-200",
                "https://linkedin.com/company/acme",
                "Builds software",
                "end_client",
                0.95,
            ),
        )

        conn.execute(
            """
            INSERT INTO company_scores (
                run_id,
                company_key,
                opportunity_score,
                opportunity_label,
                score_openings,
                score_remote,
                score_contractor,
                score_multi_source,
                score_company_type,
                score_icp_fit,
                score_pain_urgency,
                score_region_fit,
                score_company_scale,
                score_role_seniority_mix,
                score_penalty_competitor,
                score_penalty_negative_signals,
                primary_service_fit,
                buyer_persona_fit,
                opportunity_score_reason,
                scoring_provider,
                scoring_model,
                scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.run_id,
                "cmp_acme",
                32.0,
                "medium",
                10.0,
                8.0,
                4.0,
                5.0,
                5.0,
                18.0,
                8.0,
                3.0,
                2.0,
                1.0,
                -10.0,
                -5.0,
                "talent_as_a_service",
                "medium",
                "Good fit but still medium priority.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.execute(
            """
            INSERT INTO leads (
                lead_key,
                lead_fingerprint,
                run_id,
                run_date,
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url,
                lead_source,
                lead_confidence,
                email_quality_score,
                lead_capture_reason,
                lead_relevance_score,
                lead_priority_label,
                lead_decision_maker_score,
                lead_icp_fit_score,
                lead_contact_completeness_score,
                lead_penalty_negative_title,
                lead_score_reason,
                lead_scoring_provider,
                lead_scoring_model,
                lead_scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "lead_1",
                "leadfp_1",
                ctx.run_id,
                ctx.run_date,
                "cmp_acme",
                "Jane Doe",
                "CTO",
                "jane@acme.com",
                "https://linkedin.com/in/jane",
                "apollo_people",
                0.9,
                95,
                "apollo_match | title:CTO | email_quality:95",
                80,
                "high",
                34,
                28,
                18,
                0,
                "Strong technical decision-maker.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.execute(
            """
            INSERT INTO leads (
                lead_key,
                lead_fingerprint,
                run_id,
                run_date,
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url,
                lead_source,
                lead_confidence,
                email_quality_score,
                lead_capture_reason,
                lead_relevance_score,
                lead_priority_label,
                lead_decision_maker_score,
                lead_icp_fit_score,
                lead_contact_completeness_score,
                lead_penalty_negative_title,
                lead_score_reason,
                lead_scoring_provider,
                lead_scoring_model,
                lead_scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "lead_2",
                "leadfp_2",
                ctx.run_id,
                ctx.run_date,
                "cmp_acme",
                "John Roe",
                "VP Engineering",
                "",
                "https://linkedin.com/in/johnroe",
                "hunter_domain_search",
                0.7,
                70,
                "hunter_match | title:VP Engineering | email_quality:70",
                60,
                "medium",
                24,
                20,
                10,
                0,
                "Relevant but weaker than CTO.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.commit()
    finally:
        conn.close()

    service = OutboundExportService(ctx)
    service.export_all()

    commercial_path = Path(ctx.paths["commercial_pipeline_csv"])
    apollo_path = Path(ctx.paths["apollo_import_csv"])
    hubspot_companies_path = Path(ctx.paths["hubspot_companies_json"])
    hubspot_contacts_path = Path(ctx.paths["hubspot_contacts_json"])
    hubspot_tasks_path = Path(ctx.paths["hubspot_tasks_json"])
    hubspot_notes_path = Path(ctx.paths["hubspot_notes_json"])
    commercial_report_path = Path(ctx.paths["commercial_report_md"])

    assert commercial_path.exists()
    assert apollo_path.exists()
    assert hubspot_companies_path.exists()
    assert hubspot_contacts_path.exists()
    assert hubspot_tasks_path.exists()
    assert hubspot_notes_path.exists()
    assert commercial_report_path.exists()

    commercial_text = commercial_path.read_text(encoding="utf-8")
    apollo_text = apollo_path.read_text(encoding="utf-8")
    hubspot_companies_text = hubspot_companies_path.read_text(encoding="utf-8")
    hubspot_contacts_text = hubspot_contacts_path.read_text(encoding="utf-8")
    hubspot_tasks_text = hubspot_tasks_path.read_text(encoding="utf-8")
    hubspot_notes_text = hubspot_notes_path.read_text(encoding="utf-8")
    commercial_report_text = commercial_report_path.read_text(encoding="utf-8")

    assert "company_display" in commercial_text
    assert "Acme" in commercial_text
    assert "jane@acme.com" in commercial_text
    assert "best_lead_capture_reason" in commercial_text
    assert "opportunity_label" in commercial_text
    assert "score_icp_fit" in commercial_text
    assert "primary_service_fit" in commercial_text
    assert "opportunity_score_reason" in commercial_text
    assert "best_lead_priority_label" in commercial_text
    assert "best_lead_decision_maker_score" in commercial_text
    assert "best_lead_score_reason" in commercial_text
    assert "suggested_outreach_channel" in commercial_text
    assert "outreach_status" in commercial_text
    assert "commercial_priority_score" in commercial_text
    assert "lead_count" in commercial_text
    assert "apollo_leads_count" in commercial_text
    assert "hunter_leads_count" in commercial_text
    assert "contacts_with_email_count" in commercial_text
    assert "contacts_with_linkedin_count" in commercial_text
    assert "ready_email" in commercial_text
    assert "email" in commercial_text
    assert ",2," in commercial_text

    assert "website" in apollo_text
    assert "acme.com" in apollo_text

    assert "Acme" in hubspot_companies_text
    assert '"domain": "acme.com"' in hubspot_companies_text
    assert '"type": "PROSPECT"' in hubspot_companies_text
    assert "Opportunity score: 32.0" in hubspot_companies_text
    assert "Commercial priority score" in hubspot_companies_text
    assert "Run timestamp:" in hubspot_companies_text
    assert "ready_email" in hubspot_companies_text
    assert "OIE" in hubspot_companies_text

    assert "jane@acme.com" in hubspot_contacts_text
    assert "John Roe" in hubspot_tasks_text
    assert "Score: 32.0 | Source: OIE" in hubspot_contacts_text
    assert '"lifecyclestage": "opportunity"' in hubspot_contacts_text

    assert "Revisar reporte: John Roe (Acme)" in hubspot_tasks_text
    assert "Run timestamp:" in hubspot_tasks_text
    assert "### Posiciones" in hubspot_tasks_text
    assert '"hs_task_priority": "HIGH"' in hubspot_tasks_text

    assert "Run timestamp:" in hubspot_notes_text
    assert "Top jobs:" in hubspot_notes_text
    assert "Selected contacts:" in hubspot_notes_text

    assert "# Commercial Report" in commercial_report_text
    assert "## Actionable companies" in commercial_report_text
    assert "### 1. Acme" in commercial_report_text
    assert "- Best contact email: jane@acme.com" in commercial_report_text
    assert "#### Top jobs" in commercial_report_text
    assert "#### Selected contacts" in commercial_report_text
    assert "## Benchmark competitors" in commercial_report_text

    assert ctx.metrics["commercial_pipeline_rows"] == 1
    assert ctx.metrics["apollo_import_rows"] == 1
    assert ctx.metrics["hubspot_companies_rows"] == 1
    assert ctx.metrics["hubspot_contacts_rows"] == 1
    assert ctx.metrics["hubspot_tasks_rows"] == 2
    assert ctx.metrics["hubspot_notes_rows"] == 1

def test_outbound_export_service_filters_rows_to_current_run(tmp_path):
    db_path = tmp_path / "oie.db"
    outputs_path = tmp_path / "outputs"

    ctx = RunContext.create(
        config={
            "database": {"path": str(db_path)},
            "outputs": {"path": str(outputs_path)},
            "hubspot": {
                "owner_id": "owner_123",
                "target_account": "tekton_enterprise_sales",
                "source_tag": "OIE",
                "max_contacts_per_company": 3,
            },
        },
        flags={},
    )
    ctx.paths["output_dir"] = str(outputs_path / ctx.run_id)

    initialize_database(str(db_path))
    conn = get_connection(str(db_path))
    try:
        conn.execute(
            """
            INSERT INTO companies (
                company_key,
                company_display,
                company_normalized,
                resolved_domain,
                domain_source,
                domain_confidence,
                domain_candidate,
                domain_validation_status,
                domain_review_required,
                domain_ai_decision,
                industry,
                employee_range,
                company_size,
                linkedin_company_url,
                company_description,
                company_type_ai,
                classification_confidence_ai
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cmp_current",
                "Current Co",
                "current co",
                "currentco.com",
                "serpapi_fallback",
                0.95,
                "currentco.com",
                "accepted",
                0,
                "accepted",
                "Software",
                "11-50",
                "11-50",
                "https://linkedin.com/company/currentco",
                "Current run company",
                "end_client",
                0.9,
            ),
        )

        conn.execute(
            """
            INSERT INTO companies (
                company_key,
                company_display,
                company_normalized,
                resolved_domain,
                domain_source,
                domain_confidence,
                domain_candidate,
                domain_validation_status,
                domain_review_required,
                domain_ai_decision,
                industry,
                employee_range,
                company_size,
                linkedin_company_url,
                company_description,
                company_type_ai,
                classification_confidence_ai
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "cmp_old",
                "Old Co",
                "old co",
                "oldco.com",
                "serpapi_fallback",
                0.91,
                "oldco.com",
                "accepted",
                0,
                "accepted",
                "Software",
                "51-200",
                "51-200",
                "https://linkedin.com/company/oldco",
                "Previous run company",
                "end_client",
                0.88,
            ),
        )

        conn.execute(
            """
            INSERT INTO company_scores (
                run_id,
                company_key,
                opportunity_score,
                opportunity_label,
                score_openings,
                score_remote,
                score_contractor,
                score_multi_source,
                score_company_type,
                score_icp_fit,
                score_pain_urgency,
                score_region_fit,
                score_company_scale,
                score_role_seniority_mix,
                score_penalty_competitor,
                score_penalty_negative_signals,
                primary_service_fit,
                buyer_persona_fit,
                opportunity_score_reason,
                scoring_provider,
                scoring_model,
                scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ctx.run_id,
                "cmp_current",
                30.0,
                "medium",
                10.0,
                8.0,
                4.0,
                3.0,
                5.0,
                16.0,
                7.0,
                4.0,
                2.0,
                1.0,
                -8.0,
                -4.0,
                "agile_solution_delivery",
                "medium",
                "Current run scored company.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.execute(
            """
            INSERT INTO company_scores (
                run_id,
                company_key,
                opportunity_score,
                opportunity_label,
                score_openings,
                score_remote,
                score_contractor,
                score_multi_source,
                score_company_type,
                score_icp_fit,
                score_pain_urgency,
                score_region_fit,
                score_company_scale,
                score_role_seniority_mix,
                score_penalty_competitor,
                score_penalty_negative_signals,
                primary_service_fit,
                buyer_persona_fit,
                opportunity_score_reason,
                scoring_provider,
                scoring_model,
                scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "older_run",
                "cmp_old",
                99.0,
                "high",
                40.0,
                20.0,
                20.0,
                10.0,
                9.0,
                28.0,
                20.0,
                9.0,
                8.0,
                7.0,
                0.0,
                0.0,
                "managed_it_services",
                "high",
                "Old run scored company.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.execute(
            """
            INSERT INTO leads (
                lead_key,
                lead_fingerprint,
                run_id,
                run_date,
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url,
                lead_source,
                lead_confidence,
                email_quality_score,
                lead_capture_reason,
                lead_relevance_score,
                lead_priority_label,
                lead_decision_maker_score,
                lead_icp_fit_score,
                lead_contact_completeness_score,
                lead_penalty_negative_title,
                lead_score_reason,
                lead_scoring_provider,
                lead_scoring_model,
                lead_scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "lead_current",
                "leadfp_current",
                ctx.run_id,
                ctx.run_date,
                "cmp_current",
                "Jane Current",
                "CTO",
                "jane@currentco.com",
                "https://linkedin.com/in/janecurrent",
                "apollo_people",
                0.9,
                95,
                "apollo_match | title:CTO | email_quality:95",
                80,
                "high",
                34,
                28,
                18,
                0,
                "Current run strong lead.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.execute(
            """
            INSERT INTO leads (
                lead_key,
                lead_fingerprint,
                run_id,
                run_date,
                company_key,
                contact_name,
                contact_title,
                email,
                linkedin_url,
                lead_source,
                lead_confidence,
                email_quality_score,
                lead_capture_reason,
                lead_relevance_score,
                lead_priority_label,
                lead_decision_maker_score,
                lead_icp_fit_score,
                lead_contact_completeness_score,
                lead_penalty_negative_title,
                lead_score_reason,
                lead_scoring_provider,
                lead_scoring_model,
                lead_scoring_mode
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "lead_old",
                "leadfp_old",
                "older_run",
                ctx.run_date,
                "cmp_old",
                "John Old",
                "VP Engineering",
                "john@oldco.com",
                "https://linkedin.com/in/johnold",
                "hunter_domain_search",
                0.7,
                70,
                "hunter_match | title:VP Engineering | email_quality:70",
                60,
                "medium",
                24,
                20,
                10,
                0,
                "Old run relevant lead.",
                "openai",
                "gpt-4.1-mini",
                "live_api",
            ),
        )

        conn.commit()
    finally:
        conn.close()

    service = OutboundExportService(ctx)
    service.export_all()

    commercial_text = Path(ctx.paths["commercial_pipeline_csv"]).read_text(encoding="utf-8")
    apollo_text = Path(ctx.paths["apollo_import_csv"]).read_text(encoding="utf-8")
    hubspot_companies_text = Path(ctx.paths["hubspot_companies_json"]).read_text(encoding="utf-8")
    hubspot_contacts_text = Path(ctx.paths["hubspot_contacts_json"]).read_text(encoding="utf-8")
    hubspot_tasks_text = Path(ctx.paths["hubspot_tasks_json"]).read_text(encoding="utf-8")
    hubspot_notes_text = Path(ctx.paths["hubspot_notes_json"]).read_text(encoding="utf-8")
    commercial_report_text = Path(ctx.paths["commercial_report_md"]).read_text(encoding="utf-8")

    assert "Current Co" in commercial_text
    assert "currentco.com" in commercial_text
    assert "jane@currentco.com" in commercial_text

    assert "Old Co" not in commercial_text
    assert "oldco.com" not in commercial_text
    assert "john@oldco.com" not in commercial_text

    assert "currentco.com" in apollo_text
    assert "oldco.com" not in apollo_text

    assert "Current Co" in hubspot_companies_text
    assert '"domain": "currentco.com"' in hubspot_companies_text
    assert "Opportunity score: 30.0" in hubspot_companies_text
    assert "ready_email" in hubspot_companies_text
    assert "OIE" in hubspot_companies_text

    assert "jane@currentco.com" in hubspot_contacts_text
    assert "Score: 30.0 | Source: OIE" in hubspot_contacts_text
    assert '"lifecyclestage": "opportunity"' in hubspot_contacts_text

    assert "Current Co" in hubspot_tasks_text
    assert "Revisar reporte: Jane Current (Current Co)" in hubspot_tasks_text
    assert "### Posiciones" in hubspot_tasks_text

    assert "Current Co" in hubspot_notes_text
    assert "Current Co" in commercial_report_text

    assert "Old Co" not in hubspot_companies_text
    assert "oldco.com" not in hubspot_companies_text
    assert "john@oldco.com" not in hubspot_contacts_text

