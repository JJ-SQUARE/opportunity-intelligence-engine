from __future__ import annotations

import csv
import json
import re
import sqlite3
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


COMMERCIAL_PIPELINE_FIELDS = [
    "company_key",
    "company_display",
    "company_normalized",
    "resolved_domain",
    "domain_source",
    "domain_confidence",
    "domain_candidate",
    "domain_validation_status",
    "domain_review_required",
    "domain_ai_decision",
    "company_type_ai",
    "classification_confidence_ai",
    "industry",
    "employee_range",
    "company_size",
    "linkedin_company_url",
    "company_description",
    "opportunity_score",
    "opportunity_label",
    "score_openings",
    "score_remote",
    "score_contractor",
    "score_multi_source",
    "score_company_type",
    "score_icp_fit",
    "score_pain_urgency",
    "score_region_fit",
    "score_company_scale",
    "score_role_seniority_mix",
    "score_penalty_competitor",
    "score_penalty_negative_signals",
    "primary_service_fit",
    "buyer_persona_fit",
    "opportunity_score_reason",
    "scoring_provider",
    "scoring_model",
    "scoring_mode",
    "lead_count",
    "apollo_leads_count",
    "hunter_leads_count",
    "contacts_with_email_count",
    "contacts_with_linkedin_count",
    "best_contact_name",
    "best_contact_title",
    "best_contact_email",
    "best_contact_linkedin_url",
    "best_lead_source",
    "best_lead_confidence",
    "best_lead_relevance_score",
    "best_email_quality_score",
    "best_lead_capture_reason",
    "best_lead_priority_label",
    "best_lead_decision_maker_score",
    "best_lead_icp_fit_score",
    "best_lead_contact_completeness_score",
    "best_lead_penalty_negative_title",
    "best_lead_score_reason",
    "best_lead_scoring_provider",
    "best_lead_scoring_model",
    "best_lead_scoring_mode",
    "suggested_outreach_channel",
    "outreach_status",
    "commercial_priority_score",
]


APOLLO_IMPORT_FIELDS = [
    "name",
    "website",
    "linkedin_url",
]

TECH_HINTS = [
    ".net", "react", "angular", "vue", "node", "node.js", "python", "fastapi",
    "java", "spring", "aws", "azure", "gcp", "sql", "mysql", "postgres",
    "graphql", "rest", "microservices", "docker", "kubernetes", "aem",
    "javascript", "typescript", "php", "c#", "ai", "gemini", "codex"
]


class OutboundExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.db_path = self.ctx.paths.get("db_path") or self.ctx.config.get("database", {}).get("path", "data/oie.db")

    def _output_dir(self) -> Path:
        output_dir = Path(
            self.ctx.paths.get("output_dir")
            or Path(self.ctx.config.get("outputs", {}).get("path", "data/outputs")) / self.ctx.run_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.paths["output_dir"] = str(output_dir)
        return output_dir

    def _query_rows(self, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(query, params).fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def _write_csv(self, path: Path, fieldnames: List[str], rows: List[Dict[str, Any]]) -> str:
        with path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({field: row.get(field, "") for field in fieldnames})
        return str(path)

    def _write_text(self, path: Path, content: str) -> str:
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _build_commercial_pipeline_rows(self) -> List[Dict[str, Any]]:
        query = """
        WITH ranked_leads AS (
            SELECT
                l.company_key,
                l.contact_name,
                l.contact_title,
                l.email,
                l.linkedin_url,
                l.lead_source,
                l.lead_confidence,
                COALESCE(l.email_quality_score, 0) AS email_quality_score,
                COALESCE(l.lead_capture_reason, '') AS lead_capture_reason,
                COALESCE(l.lead_relevance_score, 0) AS lead_relevance_score,
                COALESCE(l.lead_priority_label, '') AS lead_priority_label,
                COALESCE(l.lead_decision_maker_score, 0) AS lead_decision_maker_score,
                COALESCE(l.lead_icp_fit_score, 0) AS lead_icp_fit_score,
                COALESCE(l.lead_contact_completeness_score, 0) AS lead_contact_completeness_score,
                COALESCE(l.lead_penalty_negative_title, 0) AS lead_penalty_negative_title,
                COALESCE(l.lead_score_reason, '') AS lead_score_reason,
                COALESCE(l.lead_scoring_provider, '') AS lead_scoring_provider,
                COALESCE(l.lead_scoring_model, '') AS lead_scoring_model,
                COALESCE(l.lead_scoring_mode, '') AS lead_scoring_mode,
                ROW_NUMBER() OVER (
                    PARTITION BY l.company_key
                    ORDER BY
                        COALESCE(l.lead_relevance_score, 0) DESC,
                        COALESCE(l.email_quality_score, 0) DESC,
                        COALESCE(l.lead_confidence, 0) DESC,
                        CASE LOWER(COALESCE(l.lead_source, ''))
                            WHEN 'apollo_people' THEN 3
                            WHEN 'hunter_domain_search' THEN 2
                            WHEN 'stub_generation' THEN 1
                            ELSE 0
                        END DESC,
                        CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
                        COALESCE(l.contact_name, '') ASC
                ) AS rn
            FROM leads l
            WHERE l.run_id = ?
        ),
        lead_stats AS (
            SELECT
                l.company_key,
                COUNT(*) AS lead_count,
                SUM(CASE WHEN LOWER(COALESCE(l.lead_source, '')) = 'apollo_people' THEN 1 ELSE 0 END) AS apollo_leads_count,
                SUM(CASE WHEN LOWER(COALESCE(l.lead_source, '')) = 'hunter_domain_search' THEN 1 ELSE 0 END) AS hunter_leads_count,
                SUM(CASE WHEN COALESCE(l.email, '') <> '' THEN 1 ELSE 0 END) AS contacts_with_email_count,
                SUM(CASE WHEN COALESCE(l.linkedin_url, '') <> '' THEN 1 ELSE 0 END) AS contacts_with_linkedin_count
            FROM leads l
            WHERE l.run_id = ?
            GROUP BY l.company_key
        ),
        best_leads AS (
            SELECT
                company_key,
                contact_name AS best_contact_name,
                contact_title AS best_contact_title,
                email AS best_contact_email,
                linkedin_url AS best_contact_linkedin_url,
                lead_source AS best_lead_source,
                lead_confidence AS best_lead_confidence,
                lead_relevance_score AS best_lead_relevance_score,
                email_quality_score AS best_email_quality_score,
                lead_capture_reason AS best_lead_capture_reason,
                COALESCE(lead_priority_label, '') AS best_lead_priority_label,
                COALESCE(lead_decision_maker_score, 0) AS best_lead_decision_maker_score,
                COALESCE(lead_icp_fit_score, 0) AS best_lead_icp_fit_score,
                COALESCE(lead_contact_completeness_score, 0) AS best_lead_contact_completeness_score,
                COALESCE(lead_penalty_negative_title, 0) AS best_lead_penalty_negative_title,
                COALESCE(lead_score_reason, '') AS best_lead_score_reason,
                COALESCE(lead_scoring_provider, '') AS best_lead_scoring_provider,
                COALESCE(lead_scoring_model, '') AS best_lead_scoring_model,
                COALESCE(lead_scoring_mode, '') AS best_lead_scoring_mode
            FROM ranked_leads
            WHERE rn = 1
        ),
        run_scores AS (
            SELECT
                cs.company_key,
                cs.opportunity_score,
                cs.opportunity_label,
                cs.score_openings,
                cs.score_remote,
                cs.score_contractor,
                cs.score_multi_source,
                cs.score_company_type,
                cs.score_icp_fit,
                cs.score_pain_urgency,
                cs.score_region_fit,
                cs.score_company_scale,
                cs.score_role_seniority_mix,
                cs.score_penalty_competitor,
                cs.score_penalty_negative_signals,
                cs.primary_service_fit,
                cs.buyer_persona_fit,
                cs.opportunity_score_reason,
                cs.scoring_provider,
                cs.scoring_model,
                cs.scoring_mode
            FROM company_scores cs
            WHERE cs.run_id = ?
        )
        SELECT
            s.company_key,
            COALESCE(c.company_display, '') AS company_display,
            COALESCE(c.company_normalized, '') AS company_normalized,
            COALESCE(c.resolved_domain, '') AS resolved_domain,
            COALESCE(c.domain_source, '') AS domain_source,
            COALESCE(c.domain_confidence, 0) AS domain_confidence,
            COALESCE(c.domain_candidate, '') AS domain_candidate,
            COALESCE(c.domain_validation_status, '') AS domain_validation_status,
            COALESCE(c.domain_review_required, 0) AS domain_review_required,
            COALESCE(c.domain_ai_decision, '') AS domain_ai_decision,
            COALESCE(c.company_type_ai, '') AS company_type_ai,
            COALESCE(c.classification_confidence_ai, 0) AS classification_confidence_ai,
            COALESCE(c.industry, '') AS industry,
            COALESCE(c.employee_range, '') AS employee_range,
            COALESCE(c.company_size, '') AS company_size,
            COALESCE(c.linkedin_company_url, '') AS linkedin_company_url,
            COALESCE(c.company_description, '') AS company_description,
            COALESCE(s.opportunity_score, 0) AS opportunity_score,
            COALESCE(s.opportunity_label, '') AS opportunity_label,
            COALESCE(s.score_openings, 0) AS score_openings,
            COALESCE(s.score_remote, 0) AS score_remote,
            COALESCE(s.score_contractor, 0) AS score_contractor,
            COALESCE(s.score_multi_source, 0) AS score_multi_source,
            COALESCE(s.score_company_type, 0) AS score_company_type,
            COALESCE(s.score_icp_fit, 0) AS score_icp_fit,
            COALESCE(s.score_pain_urgency, 0) AS score_pain_urgency,
            COALESCE(s.score_region_fit, 0) AS score_region_fit,
            COALESCE(s.score_company_scale, 0) AS score_company_scale,
            COALESCE(s.score_role_seniority_mix, 0) AS score_role_seniority_mix,
            COALESCE(s.score_penalty_competitor, 0) AS score_penalty_competitor,
            COALESCE(s.score_penalty_negative_signals, 0) AS score_penalty_negative_signals,
            COALESCE(s.primary_service_fit, '') AS primary_service_fit,
            COALESCE(s.buyer_persona_fit, '') AS buyer_persona_fit,
            COALESCE(s.opportunity_score_reason, '') AS opportunity_score_reason,
            COALESCE(s.scoring_provider, '') AS scoring_provider,
            COALESCE(s.scoring_model, '') AS scoring_model,
            COALESCE(s.scoring_mode, '') AS scoring_mode,
            COALESCE(ls.lead_count, 0) AS lead_count,
            COALESCE(ls.apollo_leads_count, 0) AS apollo_leads_count,
            COALESCE(ls.hunter_leads_count, 0) AS hunter_leads_count,
            COALESCE(ls.contacts_with_email_count, 0) AS contacts_with_email_count,
            COALESCE(ls.contacts_with_linkedin_count, 0) AS contacts_with_linkedin_count,
            COALESCE(bl.best_contact_name, '') AS best_contact_name,
            COALESCE(bl.best_contact_title, '') AS best_contact_title,
            COALESCE(bl.best_contact_email, '') AS best_contact_email,
            COALESCE(bl.best_contact_linkedin_url, '') AS best_contact_linkedin_url,
            COALESCE(bl.best_lead_source, '') AS best_lead_source,
            COALESCE(bl.best_lead_confidence, 0) AS best_lead_confidence,
            COALESCE(bl.best_lead_relevance_score, 0) AS best_lead_relevance_score,
            COALESCE(bl.best_email_quality_score, 0) AS best_email_quality_score,
            COALESCE(bl.best_lead_capture_reason, '') AS best_lead_capture_reason,
            COALESCE(bl.best_lead_priority_label, '') AS best_lead_priority_label,
            COALESCE(bl.best_lead_decision_maker_score, 0) AS best_lead_decision_maker_score,
            COALESCE(bl.best_lead_icp_fit_score, 0) AS best_lead_icp_fit_score,
            COALESCE(bl.best_lead_contact_completeness_score, 0) AS best_lead_contact_completeness_score,
            COALESCE(bl.best_lead_penalty_negative_title, 0) AS best_lead_penalty_negative_title,
            COALESCE(bl.best_lead_score_reason, '') AS best_lead_score_reason,
            COALESCE(bl.best_lead_scoring_provider, '') AS best_lead_scoring_provider,
            COALESCE(bl.best_lead_scoring_model, '') AS best_lead_scoring_model,
            COALESCE(bl.best_lead_scoring_mode, '') AS best_lead_scoring_mode,
            CASE
                WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 'email'
                WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 'linkedin'
                WHEN COALESCE(c.linkedin_company_url, '') <> '' THEN 'company_linkedin'
                WHEN COALESCE(c.resolved_domain, '') <> '' THEN 'website_only'
                ELSE 'no_channel'
            END AS suggested_outreach_channel,
            CASE
                WHEN COALESCE(c.domain_validation_status, '') = 'review' THEN 'review_domain'
                WHEN COALESCE(c.domain_validation_status, '') <> 'accepted' THEN 'pending_domain'
                WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 'ready_email'
                WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 'ready_linkedin'
                WHEN COALESCE(c.linkedin_company_url, '') <> '' OR COALESCE(c.resolved_domain, '') <> '' THEN 'research_needed'
                ELSE 'insufficient_data'
            END AS outreach_status,
            (
                COALESCE(s.opportunity_score, 0)
                + CASE WHEN COALESCE(c.domain_validation_status, '') = 'accepted' THEN 20 ELSE 0 END
                + CASE WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 25 ELSE 0 END
                + CASE WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 10 ELSE 0 END
                + CASE WHEN COALESCE(bl.best_email_quality_score, 0) >= 80 THEN 10
                       WHEN COALESCE(bl.best_email_quality_score, 0) >= 50 THEN 5
                       ELSE 0 END
                + CASE WHEN COALESCE(bl.best_lead_source, '') = 'apollo_people' THEN 10
                       WHEN COALESCE(bl.best_lead_source, '') = 'hunter_domain_search' THEN 5
                       ELSE 0 END
                + CASE WHEN COALESCE(c.company_type_ai, '') = 'end_client' THEN 10 ELSE 0 END
                + CASE WHEN COALESCE(c.linkedin_company_url, '') <> '' THEN 5 ELSE 0 END
                - CASE WHEN COALESCE(c.domain_validation_status, '') = 'review' THEN 40 ELSE 0 END
                - CASE WHEN COALESCE(c.domain_validation_status, '') NOT IN ('', 'accepted', 'review') THEN 20 ELSE 0 END
            ) AS commercial_priority_score
        FROM run_scores s
        LEFT JOIN companies c
            ON c.company_key = s.company_key
        LEFT JOIN lead_stats ls
            ON ls.company_key = s.company_key
        LEFT JOIN best_leads bl
            ON bl.company_key = s.company_key
        ORDER BY
            commercial_priority_score DESC,
            COALESCE(s.opportunity_score, 0) DESC,
            CASE WHEN COALESCE(c.domain_validation_status, '') = 'accepted' THEN 1 ELSE 0 END DESC,
            CASE WHEN COALESCE(bl.best_contact_email, '') <> '' THEN 1 ELSE 0 END DESC,
            CASE WHEN COALESCE(bl.best_contact_linkedin_url, '') <> '' THEN 1 ELSE 0 END DESC,
            c.company_display ASC
        """
        return self._query_rows(query, (self.ctx.run_id, self.ctx.run_id, self.ctx.run_id))

    def _build_company_jobs(self, company_key: str) -> List[Dict[str, Any]]:
        queries = [
            """
            SELECT
                title,
                location,
                COALESCE(job_url, '') AS job_url,
                COALESCE(apply_url, '') AS apply_url,
                COALESCE(description, '') AS description,
                COALESCE(source, '') AS source,
                COALESCE(is_remote, 0) AS is_remote,
                COALESCE(is_full_time, 0) AS is_full_time,
                COALESCE(is_contractor, 0) AS is_contractor
            FROM jobs
            WHERE run_id = ? AND company_key = ?
            ORDER BY title ASC
            """,
            """
            SELECT
                title,
                location,
                COALESCE(job_url, '') AS job_url,
                COALESCE(apply_url, '') AS apply_url,
                COALESCE(description, '') AS description,
                COALESCE(source, '') AS source,
                COALESCE(remote_flag, 0) AS is_remote,
                COALESCE(is_full_time, 0) AS is_full_time,
                COALESCE(contractor_flag, 0) AS is_contractor
            FROM jobs
            WHERE run_id = ? AND company_key = ?
            ORDER BY title ASC
            """,
            """
            SELECT
                title,
                location,
                COALESCE(job_url, '') AS job_url,
                COALESCE(apply_url, '') AS apply_url,
                COALESCE(description, '') AS description,
                COALESCE(source, '') AS source,
                0 AS is_remote,
                0 AS is_full_time,
                0 AS is_contractor
            FROM jobs
            WHERE run_id = ? AND company_key = ?
            ORDER BY title ASC
            """,
        ]

        last_error = None
        for query in queries:
            try:
                return self._query_rows(query, (self.ctx.run_id, company_key))
            except sqlite3.OperationalError as exc:
                last_error = exc

        if last_error is not None:
            raise last_error
        return []

    def _build_company_contacts(self, company_key: str) -> List[Dict[str, Any]]:
        query = """
        SELECT
            COALESCE(contact_name, '') AS contact_name,
            COALESCE(contact_title, '') AS contact_title,
            COALESCE(email, '') AS email,
            COALESCE(linkedin_url, '') AS linkedin_url,
            COALESCE(lead_source, '') AS lead_source,
            COALESCE(lead_confidence, 0) AS lead_confidence,
            COALESCE(email_quality_score, 0) AS email_quality_score,
            COALESCE(lead_relevance_score, 0) AS lead_relevance_score
        FROM leads
        WHERE run_id = ? AND company_key = ?
        ORDER BY
            COALESCE(lead_relevance_score, 0) DESC,
            COALESCE(email_quality_score, 0) DESC,
            COALESCE(lead_confidence, 0) DESC,
            contact_name ASC
        """
        return self._query_rows(query, (self.ctx.run_id, company_key))

    def _extract_budget(self, text: str) -> str:
        value = (text or "").replace("\n", " ")
        patterns = [
            r"(USD\s?\$?\s?[\d,]+(?:\s?-\s?USD\s?\$?\s?[\d,]+)?)",
            r"(\$\s?[\d,]+(?:\s?-\s?\$\s?[\d,]+)?)",
            r"(MXN\s?\$?\s?[\d,]+(?:\s?-\s?MXN\s?\$?\s?[\d,]+)?)",
            r"(S/\.\s?[\d,]+(?:\s?-\s?S/\.\s?[\d,]+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, value, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return ""

    def _extract_techs(self, text: str, limit: int = 6) -> str:
        lowered = (text or "").lower()
        found = []
        for hint in TECH_HINTS:
            if hint.lower() in lowered:
                found.append(hint)
        deduped = []
        seen = set()
        for item in found:
            key = item.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(item)
        return ", ".join(deduped[:limit])

    def _truncate(self, text: str, limit: int = 260) -> str:
        value = " ".join((text or "").split())
        if len(value) <= limit:
            return value
        return value[: limit - 3].rstrip() + "..."

    def _job_summary(self, job: Dict[str, Any]) -> str:
        workplace = []
        if job.get("is_remote"):
            workplace.append("remote")
        if job.get("is_full_time"):
            workplace.append("full-time")
        if job.get("is_contractor"):
            workplace.append("contractor")
        workplace_text = ", ".join(workplace) if workplace else "N/D"

        description = job.get("description", "")
        budget = self._extract_budget(description) or "No detectado"
        techs = self._extract_techs(" ".join([job.get("title", ""), description])) or "No detectadas"

        summary = (
            f"{job.get('title', 'Sin título')}. "
            f"Ubicación: {job.get('location') or 'N/D'}. "
            f"Modalidad: {workplace_text}. "
            f"Budget: {budget}. "
            f"Skills/stack detectados: {techs}. "
            f"Resumen: {self._truncate(description)}"
        )
        return summary

    def export_commercial_pipeline(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        path = self._output_dir() / "commercial_pipeline.csv"
        output = self._write_csv(path, COMMERCIAL_PIPELINE_FIELDS, rows)
        self.ctx.paths["commercial_pipeline_csv"] = output
        self.ctx.metrics["commercial_pipeline_rows"] = len(rows)
        return output

    def export_apollo_import(self) -> str:
        rows = [row for row in self._build_commercial_pipeline_rows() if not self._is_benchmark_row(row)]
        apollo_rows = []

        seen = set()
        for row in rows:
            website = (row.get("resolved_domain") or "").strip()
            if not website:
                continue

            key = website.lower()
            if key in seen:
                continue
            seen.add(key)

            apollo_rows.append(
                {
                    "name": row.get("company_display", ""),
                    "website": website,
                    "linkedin_url": row.get("linkedin_company_url", ""),
                }
            )

        path = self._output_dir() / "apollo_import.csv"
        output = self._write_csv(path, APOLLO_IMPORT_FIELDS, apollo_rows)
        self.ctx.paths["apollo_import_csv"] = output
        self.ctx.metrics["apollo_import_rows"] = len(apollo_rows)
        return output

    def _hubspot_safe_text(self, value: Any, limit: int | None = None) -> str:
        text = " ".join(str(value or "").split()).strip()
        if limit is not None and len(text) > limit:
            return text[: limit - 3].rstrip() + "..."
        return text

    def _split_contact_name(self, full_name: str) -> tuple[str, str]:
        name = self._hubspot_safe_text(full_name)
        if not name:
            return "", ""
        parts = name.split()
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], " ".join(parts[1:])

    def _hubspot_config(self) -> Dict[str, Any]:
        return self.ctx.config.get("hubspot", {}) or {}

    def _normalize_hubspot_owner(self) -> str:
        return str(self._hubspot_config().get("owner_id") or "").strip()

    def _normalize_hubspot_target_account(self) -> str:
        return str(self._hubspot_config().get("target_account") or "").strip()

    def _normalize_hubspot_source_tag(self) -> str:
        return str(self._hubspot_config().get("source_tag") or "OIE").strip() or "OIE"

    def _run_timestamp_label(self) -> str:
        raw = str(self.ctx.run_date or "").strip()
        if not raw:
            return "N/D"
        try:
            value = datetime.fromisoformat(raw)
            value = value.astimezone(UTC)
            return value.strftime("%Y-%m-%d %H:%M UTC")
        except ValueError:
            return raw

    def _is_benchmark_row(self, row: Dict[str, Any]) -> bool:
        company_type = self._hubspot_safe_text(row.get("company_type_ai")).lower()
        return company_type == "competitor"

    def _hubspot_task_subject(self, company_name: str, contact_name: str) -> str:
        clean_contact = self._hubspot_safe_text(contact_name) or "Unknown contact"
        clean_company = self._hubspot_safe_text(company_name) or "Unknown company"
        return f"Revisar reporte: {clean_contact} ({clean_company})"

    def _map_hubspot_industry(self, value: Any) -> str:
        raw = self._hubspot_safe_text(value)
        if not raw:
            return ""

        normalized = (
            raw.upper()
            .replace("&", "AND")
            .replace("/", "_")
            .replace("-", "_")
            .replace(",", "")
            .replace(".", "")
        )
        normalized = re.sub(r"\s+", "_", normalized)
        normalized = re.sub(r"_+", "_", normalized).strip("_")

        aliases = {
            "IT_SERVICES": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "INFORMATION_TECHNOLOGY": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "SOFTWARE": "COMPUTER_SOFTWARE",
            "STAFFING": "STAFFING_AND_RECRUITING",
            "STAFFING_RECRUITING": "STAFFING_AND_RECRUITING",
        }
        return aliases.get(normalized, normalized)

    def _hubspot_company_description(self, row: Dict[str, Any]) -> str:
        lines = [
            f"- Run ID: {self._hubspot_safe_text(self.ctx.run_id) or 'N/D'}",
            f"- Run timestamp: {self._run_timestamp_label()}",
            f"- Website: {'https://' + self._hubspot_safe_text(row.get('resolved_domain')) if self._hubspot_safe_text(row.get('resolved_domain')) else 'N/D'}",
            f"- LinkedIn company: {self._hubspot_safe_text(row.get('linkedin_company_url')) or 'N/D'}",
            f"- Industry: {self._hubspot_safe_text(row.get('industry')) or 'N/D'}",
            f"- Size: {self._hubspot_safe_text(row.get('company_size') or row.get('employee_range')) or 'N/D'}",
            f"- Company type: {self._hubspot_safe_text(row.get('company_type_ai')) or 'N/D'}",
            f"- Opportunity score: {row.get('opportunity_score') or 0}",
            f"- Commercial priority score: {row.get('commercial_priority_score') or 0}",
            f"- Outreach status: {self._hubspot_safe_text(row.get('outreach_status')) or 'N/D'}",
            f"- Source: {self._normalize_hubspot_source_tag()}",
        ]
        return "\n\n".join(lines)

    def _hubspot_positions_body(self, jobs: List[Dict[str, Any]]) -> str:
        lines: List[str] = [
            f"Run ID: {self._hubspot_safe_text(self.ctx.run_id) or 'N/D'}",
            f"Run timestamp: {self._run_timestamp_label()}",
            "",
            "### Posiciones",
            "",
        ]
        if not jobs:
            lines.append("Sin posiciones registradas en este run.")
            return "\n".join(lines)

        for idx, job in enumerate(jobs[:3], start=1):
            lines.append(f"{idx}. {self._job_summary(job)}")
            if job.get("job_url"):
                lines.append(f"   - Job URL: {job.get('job_url')}")
            if job.get("apply_url"):
                lines.append(f"   - Apply URL: {job.get('apply_url')}")
            lines.append("")

        return "\n".join(lines).rstrip()

    def _next_business_day_task_timestamp(self) -> str:
        base = datetime.fromisoformat(self.ctx.run_date)
        due = base.astimezone(UTC).replace(hour=9, minute=0, second=0, microsecond=0)

        while True:
            due = due + timedelta(days=1)
            if due.weekday() < 5:
                break

        return due.isoformat().replace("+00:00", "Z")

    def _select_hubspot_contacts(self, company_key: str, limit: int | None = None) -> List[Dict[str, Any]]:
        contacts = self._build_company_contacts(company_key)
        max_contacts = limit
        if max_contacts is None:
            max_contacts = int(
                ((self.ctx.config.get("hubspot", {}) or {}).get("max_contacts_per_company", 3) or 3)
            )

        selected: List[Dict[str, Any]] = []
        seen = set()

        for contact in contacts:
            email = (contact.get("email") or "").strip().lower()
            linkedin_url = (contact.get("linkedin_url") or "").strip().lower()
            relevance = float(contact.get("lead_relevance_score") or 0)

            if not email and not linkedin_url:
                continue
            if relevance < 45:
                continue

            dedupe_key = email or linkedin_url or (
                f"{company_key}|{(contact.get('contact_name') or '').strip().lower()}|"
                f"{(contact.get('contact_title') or '').strip().lower()}"
            )
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            selected.append(contact)

            if len(selected) >= max_contacts:
                break

        return selected

    def _rows_with_selected_contacts(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []

        for row in rows:
            if self._is_benchmark_row(row):
                continue

            company_key = self._hubspot_safe_text(row.get("company_key"))
            if not company_key:
                continue

            selected_contacts = self._select_hubspot_contacts(company_key)
            if not selected_contacts:
                continue

            filtered.append(row)

        return filtered

    def _build_hubspot_note_body(
        self,
        row: Dict[str, Any],
        jobs: List[Dict[str, Any]],
        contacts: List[Dict[str, Any]],
    ) -> str:
        lines: List[str] = []
        lines.append(f"Run ID: {self._hubspot_safe_text(self.ctx.run_id) or 'N/D'}")
        lines.append(f"Run timestamp: {self._run_timestamp_label()}")
        lines.append(f"Company: {row.get('company_display') or 'Unknown'}")
        lines.append(f"Domain: {row.get('resolved_domain') or 'N/D'}")
        lines.append(f"Industry: {row.get('industry') or 'N/D'}")
        lines.append(f"Size: {row.get('company_size') or row.get('employee_range') or 'N/D'}")
        lines.append(f"Company type: {row.get('company_type_ai') or 'N/D'}")
        lines.append(f"Opportunity score: {row.get('opportunity_score') or 0}")
        lines.append(f"Opportunity label: {row.get('opportunity_label') or 'N/D'}")
        lines.append(f"Commercial priority score: {row.get('commercial_priority_score') or 0}")
        lines.append(f"Primary service fit: {row.get('primary_service_fit') or 'N/D'}")
        lines.append(f"Buyer persona fit: {row.get('buyer_persona_fit') or 'N/D'}")
        lines.append(f"Outreach status: {row.get('outreach_status') or 'N/D'}")
        lines.append(
            f"Reason: {self._hubspot_safe_text(row.get('opportunity_score_reason') or 'N/D', 500)}"
        )
        lines.append("")
        lines.append("Top jobs:")
        if jobs:
            for idx, job in enumerate(jobs[:3], start=1):
                lines.append(f"{idx}. {self._job_summary(job)}")
        else:
            lines.append("No jobs registered in this run.")
        lines.append("")
        lines.append("Selected contacts:")
        if contacts:
            for idx, contact in enumerate(contacts, start=1):
                lines.append(
                    f"{idx}. {contact.get('contact_name') or 'N/D'} | "
                    f"{contact.get('contact_title') or 'N/D'} | "
                    f"{contact.get('email') or 'N/D'} | "
                    f"{contact.get('linkedin_url') or 'N/D'} | "
                    f"source={contact.get('lead_source') or 'N/D'} | "
                    f"relevance={contact.get('lead_relevance_score') or 0}"
                )
        else:
            lines.append("No selected contacts.")
        return "\n".join(lines)

    def _build_hubspot_company_payloads(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        owner_id = self._normalize_hubspot_owner()
        payloads: List[Dict[str, Any]] = []

        for row in rows:
            if self._is_benchmark_row(row):
                continue

            domain = self._hubspot_safe_text(row.get("resolved_domain"))
            properties = {
                "name": self._hubspot_safe_text(row.get("company_display")),
                "domain": domain,
                "website": f"https://{domain}" if domain else "",
                "industry": self._map_hubspot_industry(row.get("industry")),
                "numberofemployees": self._hubspot_safe_text(row.get("company_size") or row.get("employee_range")),
                "type": "PROSPECT",
                "description": self._hubspot_safe_text(self._hubspot_company_description(row), 5000),
            }
            if owner_id:
                properties["hubspot_owner_id"] = owner_id

            payloads.append(
                {
                    "company_key": self._hubspot_safe_text(row.get("company_key")),
                    "company_name": self._hubspot_safe_text(row.get("company_display")),
                    "properties": properties,
                }
            )

        return payloads

    def _build_hubspot_contact_payloads(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        owner_id = self._normalize_hubspot_owner()
        source_tag = self._normalize_hubspot_source_tag()
        payloads: List[Dict[str, Any]] = []
        seen = set()

        for row in rows:
            if self._is_benchmark_row(row):
                continue

            company_key = self._hubspot_safe_text(row.get("company_key"))
            company_name = self._hubspot_safe_text(row.get("company_display"))
            opportunity_score = row.get("opportunity_score", 0)

            contacts = self._select_hubspot_contacts(company_key)
            for contact in contacts:
                contact_name = self._hubspot_safe_text(contact.get("contact_name"))
                email = self._hubspot_safe_text(contact.get("email")).lower()
                linkedin_url = self._hubspot_safe_text(contact.get("linkedin_url"))
                firstname, lastname = self._split_contact_name(contact_name)

                if not email:
                    continue

                dedupe_key = email or linkedin_url or f"{company_key}|{contact_name}"
                if dedupe_key in seen:
                    continue
                seen.add(dedupe_key)

                properties = {
                    "email": email,
                    "firstname": firstname,
                    "lastname": lastname,
                    "jobtitle": (
                        f"{self._hubspot_safe_text(contact.get('contact_title'))} | "
                        f"Score: {opportunity_score} | Source: {source_tag}"
                    ).strip(),
                    "company": company_name,
                    "lifecyclestage": "opportunity",
                }
                if owner_id:
                    properties["hubspot_owner_id"] = owner_id

                payloads.append(
                    {
                        "company_key": company_key,
                        "company_name": company_name,
                        "contact_name": contact_name,
                        "properties": properties,
                    }
                )

        return payloads

    def _build_hubspot_task_payloads(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        owner_id = self._normalize_hubspot_owner()
        payloads: List[Dict[str, Any]] = []

        for row in rows:
            if self._is_benchmark_row(row):
                continue

            company_key = self._hubspot_safe_text(row.get("company_key"))
            company_name = self._hubspot_safe_text(row.get("company_display"))
            jobs = self._build_company_jobs(company_key)
            contacts = self._select_hubspot_contacts(company_key)

            for contact in contacts:
                contact_name = self._hubspot_safe_text(contact.get("contact_name")) or "Unknown contact"

                properties = {
                    "hs_task_subject": self._hubspot_task_subject(company_name, contact_name),
                    "hs_task_body": self._hubspot_positions_body(jobs),
                    "hs_task_status": "NOT_STARTED",
                    "hs_task_priority": "HIGH",
                    "hs_timestamp": self._next_business_day_task_timestamp(),
                }
                if owner_id:
                    properties["hubspot_owner_id"] = owner_id

                payloads.append(
                    {
                        "company_key": company_key,
                        "company_name": company_name,
                        "contact_name": contact_name,
                        "task_subject": properties["hs_task_subject"],
                        "properties": properties,
                    }
                )

        return payloads

    def _build_hubspot_note_payloads(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        target_account = self._normalize_hubspot_target_account()
        source_tag = self._normalize_hubspot_source_tag()

        payloads: List[Dict[str, Any]] = []

        for row in rows:
            if self._is_benchmark_row(row):
                continue

            company_key = self._hubspot_safe_text(row.get("company_key"))
            jobs = self._build_company_jobs(company_key)
            contacts = self._select_hubspot_contacts(company_key)
            note_body = self._build_hubspot_note_body(row, jobs, contacts)

            payloads.append(
                {
                    "company_key": company_key,
                    "company_name": self._hubspot_safe_text(row.get("company_display")),
                    "properties": {
                        "hs_timestamp": self.ctx.run_date,
                        "hs_note_body": (
                            note_body
                            + f"\n\nTarget account: {target_account or 'N/D'}"
                            + f"\nSource tag: {source_tag}"
                        ),
                    },
                }
            )

        return payloads

    def export_hubspot_payloads(self) -> None:
        rows = self._rows_with_selected_contacts(self._build_commercial_pipeline_rows())

        companies_payload = self._build_hubspot_company_payloads(rows)
        contacts_payload = self._build_hubspot_contact_payloads(rows)
        tasks_payload = self._build_hubspot_task_payloads(rows)
        notes_payload = self._build_hubspot_note_payloads(rows)

        output_dir = self._output_dir()

        companies_path = output_dir / "hubspot_companies.json"
        contacts_path = output_dir / "hubspot_contacts.json"
        tasks_path = output_dir / "hubspot_tasks.json"
        notes_path = output_dir / "hubspot_notes.json"

        self._write_text(companies_path, json.dumps(companies_payload, ensure_ascii=False, indent=2))
        self._write_text(contacts_path, json.dumps(contacts_payload, ensure_ascii=False, indent=2))
        self._write_text(tasks_path, json.dumps(tasks_payload, ensure_ascii=False, indent=2))
        self._write_text(notes_path, json.dumps(notes_payload, ensure_ascii=False, indent=2))

        self.ctx.paths["hubspot_companies_json"] = str(companies_path)
        self.ctx.paths["hubspot_contacts_json"] = str(contacts_path)
        self.ctx.paths["hubspot_tasks_json"] = str(tasks_path)
        self.ctx.paths["hubspot_notes_json"] = str(notes_path)

        self.ctx.metrics["hubspot_companies_rows"] = len(companies_payload)
        self.ctx.metrics["hubspot_contacts_rows"] = len(contacts_payload)
        self.ctx.metrics["hubspot_tasks_rows"] = len(tasks_payload)
        self.ctx.metrics["hubspot_notes_rows"] = len(notes_payload)


    def _hubspot_sync_enabled(self) -> bool:
        cfg = self._hubspot_config()

        # Nuevo: override por flag de ejecución
        force_push = str(self.ctx.flags.get("push_hubspot", "")).lower() in {"1", "true", "yes"}

        if force_push:
            return True

        return (
            bool(cfg.get("enabled"))
            and bool(cfg.get("push_enabled"))
            and not bool(cfg.get("pause_before_push"))
        )

    def push_hubspot_payloads(self, provider_execution_service: Any) -> Dict[str, Any]:
        self.export_hubspot_payloads()

        if not self._hubspot_sync_enabled():
            self.ctx.metrics["hubspot_push_skipped"] = True
            return {
                "enabled": False,
                "pushed": False,
                "reason": "hubspot_push_disabled",
            }

        client = provider_execution_service.provider_control_service.registry.get_client("hubspot")
        if client is None:
            raise RuntimeError("HubSpot client no está registrado")

        rows = self._rows_with_selected_contacts(self._build_commercial_pipeline_rows())
        companies_payload = self._build_hubspot_company_payloads(rows)
        contacts_payload = self._build_hubspot_contact_payloads(rows)
        tasks_payload = self._build_hubspot_task_payloads(rows)
        notes_payload = self._build_hubspot_note_payloads(rows)

        results = {
            "companies": [],
            "contacts": [],
            "tasks": [],
            "notes": [],
            "associations": [],
        }

        company_id_map: Dict[str, str] = {}
        contact_ids_by_company: Dict[str, List[str]] = {}

        for payload in companies_payload:
            properties = payload.get("properties", {}) or {}
            domain = str(properties.get("domain") or "").strip().lower()

            existing = None
            if domain and hasattr(client, "search_company_by_domain"):
                existing = provider_execution_service.execute(
                    "hubspot",
                    "search_company_by_domain",
                    client.search_company_by_domain,
                    domain,
                )

            response = existing
            status = "existing"
            if not response:
                response = provider_execution_service.execute(
                    "hubspot",
                    "create_company",
                    client.create_company,
                    {"properties": properties},
                )
                status = "created"

            company_key = payload.get("company_key", "")
            company_id = str((response or {}).get("id") or "")
            if company_key and company_id:
                company_id_map[company_key] = company_id

            results["companies"].append(
                {
                    "status": status,
                    "company_key": company_key,
                    "company_name": payload.get("company_name", ""),
                    "response": response,
                }
            )

        for payload in contacts_payload:
            properties = payload.get("properties", {}) or {}
            email = str(properties.get("email") or "").strip().lower()
            if not email:
                results["contacts"].append(
                    {
                        "status": "skipped",
                        "reason": "missing_email",
                        "company_key": payload.get("company_key", ""),
                        "contact_name": payload.get("contact_name", ""),
                    }
                )
                continue

            existing = None
            if hasattr(client, "search_contact_by_email"):
                existing = provider_execution_service.execute(
                    "hubspot",
                    "search_contact_by_email",
                    client.search_contact_by_email,
                    email,
                )

            response = existing
            status = "existing"
            if not response:
                response = provider_execution_service.execute(
                    "hubspot",
                    "create_contact",
                    client.create_contact,
                    {"properties": properties},
                )
                status = "created"

            company_key = payload.get("company_key", "")
            contact_id = str((response or {}).get("id") or "")
            company_id = company_id_map.get(company_key)

            if company_key and contact_id:
                ids = contact_ids_by_company.setdefault(company_key, [])
                if contact_id not in ids:
                    ids.append(contact_id)

            if company_id and contact_id:
                association_response = provider_execution_service.execute(
                    "hubspot",
                    "associate_contact_company",
                    client.create_association,
                    "contacts",
                    contact_id,
                    "companies",
                    company_id,
                )
                results["associations"].append(
                    {
                        "type": "contact_company",
                        "company_key": company_key,
                        "contact_name": payload.get("contact_name", ""),
                        "from_object_type": "contacts",
                        "from_object_id": contact_id,
                        "to_object_type": "companies",
                        "to_object_id": company_id,
                        "response": association_response,
                    }
                )

            results["contacts"].append(
                {
                    "status": status,
                    "company_key": company_key,
                    "company_name": payload.get("company_name", ""),
                    "contact_name": payload.get("contact_name", ""),
                    "response": response,
                }
            )

        for payload in tasks_payload:
            properties = payload.get("properties", {}) or {}
            subject = str(payload.get("task_subject") or properties.get("hs_task_subject") or "").strip()

            existing = None
            if subject and hasattr(client, "search_task_by_subject"):
                existing = provider_execution_service.execute(
                    "hubspot",
                    "search_task_by_subject",
                    client.search_task_by_subject,
                    subject,
                )

            response = existing
            status = "existing"
            if not response:
                response = provider_execution_service.execute(
                    "hubspot",
                    "create_task",
                    client.create_task,
                    {"properties": properties},
                )
                status = "created"

            company_key = payload.get("company_key", "")
            company_id = company_id_map.get(company_key)
            task_id = str((response or {}).get("id") or "")

            if company_id and task_id:
                association_response = provider_execution_service.execute(
                    "hubspot",
                    "associate_task_company",
                    client.create_association,
                    "tasks",
                    task_id,
                    "companies",
                    company_id,
                )
                results["associations"].append(
                    {
                        "type": "task_company",
                        "company_key": company_key,
                        "from_object_type": "tasks",
                        "from_object_id": task_id,
                        "to_object_type": "companies",
                        "to_object_id": company_id,
                        "response": association_response,
                    }
                )

            results["tasks"].append(
                {
                    "status": status,
                    "company_key": company_key,
                    "company_name": payload.get("company_name", ""),
                    "contact_name": payload.get("contact_name", ""),
                    "response": response,
                }
            )

        for payload in notes_payload:
            properties = payload.get("properties", {}) or {}
            response = provider_execution_service.execute(
                "hubspot",
                "create_note",
                client.create_note,
                {"properties": properties},
            )

            company_key = payload.get("company_key", "")
            company_id = company_id_map.get(company_key)
            note_id = str((response or {}).get("id") or "")

            if company_id and note_id:
                association_response = provider_execution_service.execute(
                    "hubspot",
                    "associate_note_company",
                    client.create_association,
                    "notes",
                    note_id,
                    "companies",
                    company_id,
                )
                results["associations"].append(
                    {
                        "type": "note_company",
                        "company_key": company_key,
                        "from_object_type": "notes",
                        "from_object_id": note_id,
                        "to_object_type": "companies",
                        "to_object_id": company_id,
                        "response": association_response,
                    }
                )

            results["notes"].append(
                {
                    "status": "created",
                    "company_key": company_key,
                    "company_name": payload.get("company_name", ""),
                    "response": response,
                }
            )

        self.ctx.metrics["hubspot_push_companies"] = len(results["companies"])
        self.ctx.metrics["hubspot_push_contacts"] = len(results["contacts"])
        self.ctx.metrics["hubspot_push_tasks"] = len(results["tasks"])
        self.ctx.metrics["hubspot_push_notes"] = len(results["notes"])

        return results


    def export_commercial_report_markdown(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        actionable_rows = [row for row in rows if not self._is_benchmark_row(row)]
        benchmark_rows = [row for row in rows if self._is_benchmark_row(row)]

        lines: List[str] = []
        lines.append("# Commercial Report")
        lines.append("")
        lines.append(f"- Run ID: {self._hubspot_safe_text(self.ctx.run_id) or 'N/D'}")
        lines.append(f"- Run timestamp: {self._run_timestamp_label()}")
        lines.append(f"- Actionable companies: {len(actionable_rows)}")
        lines.append(f"- Benchmark competitors: {len(benchmark_rows)}")
        lines.append("")

        if actionable_rows:
            lines.append("## Actionable companies")
            lines.append("")
            for idx, row in enumerate(actionable_rows, start=1):
                company_key = self._hubspot_safe_text(row.get("company_key"))
                lines.append(f"### {idx}. {row.get('company_display') or 'Unknown'}")
                lines.append(f"- Domain: {row.get('resolved_domain') or 'N/D'}")
                lines.append(f"- LinkedIn: {row.get('linkedin_company_url') or 'N/D'}")
                lines.append(f"- Industry: {row.get('industry') or 'N/D'}")
                lines.append(f"- Size: {row.get('company_size') or row.get('employee_range') or 'N/D'}")
                lines.append(f"- Company type: {row.get('company_type_ai') or 'N/D'}")
                lines.append(f"- Opportunity score: {row.get('opportunity_score') or 0}")
                lines.append(f"- Opportunity label: {row.get('opportunity_label') or 'N/D'}")
                lines.append(f"- Commercial priority score: {row.get('commercial_priority_score') or 0}")
                lines.append(f"- Outreach status: {row.get('outreach_status') or 'N/D'}")
                lines.append(f"- Primary service fit: {row.get('primary_service_fit') or 'N/D'}")
                lines.append(f"- Buyer persona fit: {row.get('buyer_persona_fit') or 'N/D'}")
                lines.append(f"- Best contact: {row.get('best_contact_name') or 'N/D'} | {row.get('best_contact_title') or 'N/D'}")
                lines.append(f"- Best contact email: {row.get('best_contact_email') or 'N/D'}")
                lines.append(f"- Best contact LinkedIn: {row.get('best_contact_linkedin_url') or 'N/D'}")
                lines.append(f"- Reason: {self._hubspot_safe_text(row.get('opportunity_score_reason') or 'N/D', 500)}")
                lines.append("")

                jobs = self._build_company_jobs(company_key) if company_key else []
                lines.append("#### Top jobs")
                if jobs:
                    for job_idx, job in enumerate(jobs[:3], start=1):
                        lines.append(f"{job_idx}. {self._job_summary(job)}")
                else:
                    lines.append("No jobs registered in this run.")
                lines.append("")

                contacts = self._select_hubspot_contacts(company_key) if company_key else []
                lines.append("#### Selected contacts")
                if contacts:
                    for contact_idx, contact in enumerate(contacts, start=1):
                        lines.append(
                            f"{contact_idx}. "
                            f"{contact.get('contact_name') or 'N/D'} | "
                            f"{contact.get('contact_title') or 'N/D'} | "
                            f"{contact.get('email') or 'N/D'} | "
                            f"{contact.get('linkedin_url') or 'N/D'} | "
                            f"source={contact.get('lead_source') or 'N/D'} | "
                            f"relevance={contact.get('lead_relevance_score') or 0}"
                        )
                else:
                    lines.append("No selected contacts.")
                lines.append("")
        else:
            lines.append("## Actionable companies")
            lines.append("")
            lines.append("No actionable companies in this run.")
            lines.append("")

        lines.append("## Benchmark competitors")
        lines.append("")
        if benchmark_rows:
            for idx, row in enumerate(benchmark_rows, start=1):
                company_key = self._hubspot_safe_text(row.get("company_key"))
                lines.append(f"### {idx}. {row.get('company_display') or 'Unknown'}")
                lines.append(f"- Company type: {row.get('company_type_ai') or 'competitor'}")
                lines.append(f"- Industry: {row.get('industry') or 'N/D'}")
                lines.append(f"- LinkedIn: {row.get('linkedin_company_url') or 'N/D'}")
                lines.append(f"- What they are hiring for: {self._hubspot_safe_text(row.get('opportunity_score_reason') or row.get('company_description') or 'N/D', 500)}")
                jobs = self._build_company_jobs(company_key) if company_key else []
                if jobs:
                    lines.append("- Sample roles:")
                    for job in jobs[:3]:
                        lines.append(f"  - {job.get('title') or 'Sin título'} | {job.get('location') or 'N/D'}")
                else:
                    lines.append("- Sample roles: N/D")
                lines.append("")
        else:
            lines.append("No benchmark competitors in this run.")
            lines.append("")

        path = self._output_dir() / "commercial_report.md"
        output = self._write_text(path, "\n".join(lines).rstrip() + "\n")
        self.ctx.paths["commercial_report_md"] = output
        self.ctx.metrics["commercial_report_companies"] = len(actionable_rows)
        self.ctx.metrics["commercial_report_benchmark_companies"] = len(benchmark_rows)
        return output


    def export_all(self) -> None:
        self.export_commercial_pipeline()
        self.export_apollo_import()
        self.export_hubspot_payloads()
        self.export_commercial_report_markdown()
