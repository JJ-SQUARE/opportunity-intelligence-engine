from __future__ import annotations

import sqlite3
from pathlib import Path


DEFAULT_DB_PATH = "data/oie.db"


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database(db_path: str = DEFAULT_DB_PATH) -> None:
    conn = get_connection(db_path)
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS runs (
                run_id TEXT PRIMARY KEY,
                run_date TEXT NOT NULL,
                status TEXT,
                mode TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS run_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                metric_key TEXT NOT NULL,
                metric_value TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            );

            CREATE TABLE IF NOT EXISTS provider_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                event_type TEXT NOT NULL,
                status_code INTEGER,
                message TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            );

            CREATE TABLE IF NOT EXISTS companies (
                company_key TEXT PRIMARY KEY,
                company_display TEXT NOT NULL,
                company_normalized TEXT NOT NULL,
                company_root TEXT,
                resolved_domain TEXT,
                domain_source TEXT,
                domain_confidence REAL,
                domain_candidate TEXT,
                domain_validation_status TEXT,
                domain_review_required INTEGER DEFAULT 0,
                domain_ai_validated INTEGER DEFAULT 0,
                domain_ai_decision TEXT,
                domain_ai_confidence REAL,
                domain_ai_reason TEXT,
                ai_company_identity_confidence REAL,
                ai_company_identity_source TEXT,
                ai_company_identity_reason TEXT,
                company_identity_ai_valid INTEGER DEFAULT 1,
                company_identity_ai_contaminated INTEGER DEFAULT 0,
                company_identity_ai_ambiguous INTEGER DEFAULT 0,
                industry TEXT,
                employee_range TEXT,
                linkedin_company_url TEXT,
                company_description TEXT,
                company_size TEXT,
                enriched_at TEXT,
                enrichment_source TEXT,
                enrichment_ai_match INTEGER DEFAULT 0,
                enrichment_ai_confidence REAL,
                enrichment_ai_decision TEXT,
                enrichment_ai_reason TEXT,
                enrichment_ai_provider TEXT,
                enrichment_ai_model TEXT,
                enrichment_ai_mode TEXT,
                company_type_ai TEXT,
                classification_confidence_ai REAL,
                classification_provider TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS company_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_key TEXT NOT NULL,
                alias_value TEXT NOT NULL,
                alias_normalized TEXT NOT NULL,
                alias_type TEXT DEFAULT 'observed_name',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_key) REFERENCES companies (company_key)
            );

            CREATE TABLE IF NOT EXISTS domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_key TEXT NOT NULL,
                domain TEXT NOT NULL,
                source TEXT,
                confidence REAL,
                is_primary INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (company_key) REFERENCES companies (company_key)
            );

            CREATE TABLE IF NOT EXISTS company_merge_candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                company_key_left TEXT NOT NULL,
                company_key_right TEXT NOT NULL,
                reason TEXT NOT NULL,
                confidence REAL DEFAULT 0.0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            );

            CREATE TABLE IF NOT EXISTS jobs (
                job_key TEXT PRIMARY KEY,
                job_fingerprint TEXT,
                run_id TEXT NOT NULL,
                run_date TEXT NOT NULL,
                title TEXT,
                company TEXT,
                company_key TEXT,
                location TEXT,
                job_url TEXT,
                apply_url TEXT,
                description TEXT,
                source TEXT,
                detected_at TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (company_key) REFERENCES companies (company_key)
            );

            CREATE TABLE IF NOT EXISTS leads (
                lead_key TEXT PRIMARY KEY,
                lead_fingerprint TEXT,
                run_id TEXT NOT NULL,
                run_date TEXT NOT NULL,
                company_key TEXT,
                contact_name TEXT,
                contact_title TEXT,
                email TEXT,
                linkedin_url TEXT,
                lead_source TEXT,
                lead_confidence REAL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (company_key) REFERENCES companies (company_key)
            );

            CREATE TABLE IF NOT EXISTS provider_operation_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                provider TEXT NOT NULL,
                operation TEXT NOT NULL,
                max_calls INTEGER,
                used_calls INTEGER DEFAULT 0,
                remaining_calls INTEGER,
                started INTEGER DEFAULT 0,
                success INTEGER DEFAULT 0,
                retry_count INTEGER DEFAULT 0,
                blocked_budget INTEGER DEFAULT 0,
                blocked_provider INTEGER DEFAULT 0,
                errors_timeout INTEGER DEFAULT 0,
                errors_rate_limit INTEGER DEFAULT 0,
                errors_http_5xx INTEGER DEFAULT 0,
                errors_execution_error INTEGER DEFAULT 0,
                errors_auth INTEGER DEFAULT 0,
                errors_permission INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            );


            CREATE TABLE IF NOT EXISTS company_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                company_key TEXT NOT NULL,
                opportunity_score REAL,
                opportunity_label TEXT,
                icp_bucket TEXT,
                commercial_bucket TEXT,
                pain_urgency TEXT,
                recommended_service TEXT,
                reason TEXT,
                score_openings REAL,
                score_remote REAL,
                score_contractor REAL,
                score_multi_source REAL,
                score_company_type REAL,
                score_icp_fit REAL,
                score_pain_urgency REAL,
                score_region_fit REAL,
                score_company_scale REAL,
                score_role_seniority_mix REAL,
                score_penalty_competitor REAL,
                score_penalty_negative_signals REAL,
                primary_service_fit TEXT,
                buyer_persona_fit TEXT,
                opportunity_score_reason TEXT,
                scoring_provider TEXT,
                scoring_model TEXT,
                scoring_mode TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (company_key) REFERENCES companies (company_key)
            );

            CREATE INDEX IF NOT EXISTS idx_run_metrics_run_id
            ON run_metrics (run_id);

            CREATE INDEX IF NOT EXISTS idx_provider_events_run_id
            ON provider_events (run_id);

            CREATE INDEX IF NOT EXISTS idx_companies_normalized
            ON companies (company_normalized);

            CREATE INDEX IF NOT EXISTS idx_company_aliases_company_key
            ON company_aliases (company_key);

            CREATE INDEX IF NOT EXISTS idx_company_aliases_alias_normalized
            ON company_aliases (alias_normalized);

            CREATE INDEX IF NOT EXISTS idx_domains_company_key
            ON domains (company_key);

            CREATE INDEX IF NOT EXISTS idx_domains_domain
            ON domains (domain);

            CREATE INDEX IF NOT EXISTS idx_merge_candidates_run_id
            ON company_merge_candidates (run_id);

            CREATE INDEX IF NOT EXISTS idx_jobs_run_id
            ON jobs (run_id);

            CREATE INDEX IF NOT EXISTS idx_jobs_job_url
            ON jobs (job_url);

            CREATE INDEX IF NOT EXISTS idx_jobs_apply_url
            ON jobs (apply_url);

            CREATE INDEX IF NOT EXISTS idx_leads_run_id
            ON leads (run_id);

            CREATE INDEX IF NOT EXISTS idx_leads_email
            ON leads (email);

            CREATE INDEX IF NOT EXISTS idx_provider_operation_metrics_run_id
            ON provider_operation_metrics (run_id);

            CREATE INDEX IF NOT EXISTS idx_provider_operation_metrics_provider_operation
            ON provider_operation_metrics (provider, operation);


            CREATE INDEX IF NOT EXISTS idx_company_scores_run_id
            ON company_scores (run_id);

            CREATE INDEX IF NOT EXISTS idx_company_scores_company_key
            ON company_scores (company_key);
            """
        )

        company_columns = {row["name"] for row in conn.execute("PRAGMA table_info(companies)").fetchall()}
        required_company_columns = {
            "company_root": "TEXT",
            "domain_candidate": "TEXT",
            "domain_validation_status": "TEXT",
            "domain_review_required": "INTEGER DEFAULT 0",
            "domain_ai_validated": "INTEGER DEFAULT 0",
            "domain_ai_decision": "TEXT",
            "domain_ai_confidence": "REAL",
            "domain_ai_reason": "TEXT",
            "ai_company_identity_confidence": "REAL",
            "ai_company_identity_source": "TEXT",
            "ai_company_identity_reason": "TEXT",
            "company_identity_ai_valid": "INTEGER DEFAULT 1",
            "company_identity_ai_contaminated": "INTEGER DEFAULT 0",
            "company_identity_ai_ambiguous": "INTEGER DEFAULT 0",
            "industry": "TEXT",
            "employee_range": "TEXT",
            "linkedin_company_url": "TEXT",
            "company_description": "TEXT",
            "company_size": "TEXT",
            "enriched_at": "TEXT",
            "enrichment_source": "TEXT",
            "enrichment_ai_match": "INTEGER DEFAULT 0",
            "enrichment_ai_confidence": "REAL",
            "enrichment_ai_decision": "TEXT",
            "enrichment_ai_reason": "TEXT",
            "enrichment_ai_provider": "TEXT",
            "enrichment_ai_model": "TEXT",
            "enrichment_ai_mode": "TEXT",
            "company_type_ai": "TEXT",
            "classification_confidence_ai": "REAL",
            "classification_provider": "TEXT",
        }
        for column_name, column_type in required_company_columns.items():
            if column_name not in company_columns:
                conn.execute(f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}")

        provider_event_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(provider_events)").fetchall()
        }
        required_provider_event_columns = {
            "status_code": "INTEGER",
        }
        for column_name, column_type in required_provider_event_columns.items():
            if column_name not in provider_event_columns:
                conn.execute(f"ALTER TABLE provider_events ADD COLUMN {column_name} {column_type}")

        provider_operation_metrics_columns = {
            row["name"] for row in conn.execute("PRAGMA table_info(provider_operation_metrics)").fetchall()
        }
        required_provider_operation_metrics_columns = {
            "blocked_provider": "INTEGER DEFAULT 0",
            "errors_rate_limit": "INTEGER DEFAULT 0",
            "errors_http_5xx": "INTEGER DEFAULT 0",
            "errors_auth": "INTEGER DEFAULT 0",
            "errors_permission": "INTEGER DEFAULT 0",
        }
        for column_name, column_type in required_provider_operation_metrics_columns.items():
            if column_name not in provider_operation_metrics_columns:
                conn.execute(
                    f"ALTER TABLE provider_operation_metrics ADD COLUMN {column_name} {column_type}"
                )

        job_columns = {row["name"] for row in conn.execute("PRAGMA table_info(jobs)").fetchall()}
        required_job_columns = {
            "job_fingerprint": "TEXT",
            "is_remote": "INTEGER DEFAULT 0",
            "is_contractor": "INTEGER DEFAULT 0",
            "is_full_time": "INTEGER DEFAULT 0",
            "nearshore_friendly": "INTEGER DEFAULT 0",
            "us_only": "INTEGER DEFAULT 0",
            "remote_flag": "INTEGER DEFAULT 0",
            "contractor_flag": "INTEGER DEFAULT 0",
            "many_openings_signal": "INTEGER DEFAULT 0",
            "offshore_mentioned": "INTEGER DEFAULT 0",
            "urgency_hits": "INTEGER DEFAULT 0",
        }
        for column_name, column_type in required_job_columns.items():
            if column_name not in job_columns:
                conn.execute(f"ALTER TABLE jobs ADD COLUMN {column_name} {column_type}")

        lead_columns = {row["name"] for row in conn.execute("PRAGMA table_info(leads)").fetchall()}
        required_lead_columns = {
            "lead_source": "TEXT",
            "lead_confidence": "REAL",
            "lead_fingerprint": "TEXT",
            "email_quality_score": "INTEGER DEFAULT 0",
            "lead_capture_reason": "TEXT",
            "lead_relevance_score": "REAL DEFAULT 0",
            "lead_priority_label": "TEXT",
            "lead_decision_maker_score": "REAL DEFAULT 0",
            "lead_icp_fit_score": "REAL DEFAULT 0",
            "lead_contact_completeness_score": "REAL DEFAULT 0",
            "lead_penalty_negative_title": "REAL DEFAULT 0",
            "lead_score_reason": "TEXT",
            "lead_scoring_provider": "TEXT",
            "lead_scoring_model": "TEXT",
            "lead_scoring_mode": "TEXT",
            "lead_score_title": "REAL DEFAULT 0",
            "lead_score_source": "REAL DEFAULT 0",
            "lead_score_email": "REAL DEFAULT 0",
            "lead_score_linkedin": "REAL DEFAULT 0",
            "lead_score_email_quality": "REAL DEFAULT 0",
            "lead_score_confidence": "REAL DEFAULT 0",
            "lead_score_completeness_penalty": "REAL DEFAULT 0",
            "lead_score_company_penalty": "REAL DEFAULT 0",
            "target_persona": "TEXT",
            "suggested_titles": "TEXT",
            "search_reason": "TEXT",
            "pain_alignment": "TEXT",
            "priority": "TEXT",
            "recommended_channel": "TEXT",
            "lead_role_type": "TEXT",
            "why_selected": "TEXT",
            "outreach_angle": "TEXT",
            "expected_relevance": "TEXT",
            "risk_or_uncertainty": "TEXT",
        }
        for column_name, column_type in required_lead_columns.items():
            if column_name not in lead_columns:
                conn.execute(f"ALTER TABLE leads ADD COLUMN {column_name} {column_type}")

        company_score_columns = {row["name"] for row in conn.execute("PRAGMA table_info(company_scores)").fetchall()}
        required_company_score_columns = {
            "opportunity_label": "TEXT",
            "icp_bucket": "TEXT",
            "commercial_bucket": "TEXT",
            "pain_urgency": "TEXT",
            "recommended_service": "TEXT",
            "reason": "TEXT",
            "score_icp_fit": "REAL",
            "score_pain_urgency": "REAL",
            "score_region_fit": "REAL",
            "score_company_scale": "REAL",
            "score_role_seniority_mix": "REAL",
            "score_penalty_competitor": "REAL",
            "score_penalty_negative_signals": "REAL",
            "primary_service_fit": "TEXT",
            "buyer_persona_fit": "TEXT",
            "opportunity_score_reason": "TEXT",
            "scoring_provider": "TEXT",
            "scoring_model": "TEXT",
            "scoring_mode": "TEXT",
        }
        for column_name, column_type in required_company_score_columns.items():
            if column_name not in company_score_columns:
                conn.execute(f"ALTER TABLE company_scores ADD COLUMN {column_name} {column_type}")

        conn.execute("CREATE INDEX IF NOT EXISTS idx_jobs_job_fingerprint ON jobs (job_fingerprint)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_leads_lead_fingerprint ON leads (lead_fingerprint)")

        conn.commit()
    finally:
        conn.close()
