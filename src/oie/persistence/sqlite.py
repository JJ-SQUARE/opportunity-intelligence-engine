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
                message TEXT,
                metadata_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id)
            );

            CREATE TABLE IF NOT EXISTS companies (
                company_key TEXT PRIMARY KEY,
                company_display TEXT NOT NULL,
                company_normalized TEXT NOT NULL,
                resolved_domain TEXT,
                domain_source TEXT,
                domain_confidence REAL,
                industry TEXT,
                employee_range TEXT,
                linkedin_company_url TEXT,
                company_description TEXT,
                company_size TEXT,
                enriched_at TEXT,
                enrichment_source TEXT,
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
                run_id TEXT NOT NULL,
                run_date TEXT NOT NULL,
                company_key TEXT,
                contact_name TEXT,
                contact_title TEXT,
                email TEXT,
                linkedin_url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES runs (run_id),
                FOREIGN KEY (company_key) REFERENCES companies (company_key)
            );

            CREATE TABLE IF NOT EXISTS company_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL,
                company_key TEXT NOT NULL,
                opportunity_score REAL,
                score_openings REAL,
                score_remote REAL,
                score_contractor REAL,
                score_multi_source REAL,
                score_company_type REAL,
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

            CREATE INDEX IF NOT EXISTS idx_company_scores_run_id
            ON company_scores (run_id);

            CREATE INDEX IF NOT EXISTS idx_company_scores_company_key
            ON company_scores (company_key);
            """
        )

        # Migraciones simples para bases ya existentes
        existing_columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(companies)").fetchall()
        }
        required_columns = {
            "industry": "TEXT",
            "employee_range": "TEXT",
            "linkedin_company_url": "TEXT",
            "company_description": "TEXT",
            "company_size": "TEXT",
            "enriched_at": "TEXT",
            "enrichment_source": "TEXT",
        }

        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE companies ADD COLUMN {column_name} {column_type}"
                )

        conn.commit()
    finally:
        conn.close()
