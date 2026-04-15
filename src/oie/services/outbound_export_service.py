from __future__ import annotations

import csv
import re
import sqlite3
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
    "score_openings",
    "score_remote",
    "score_contractor",
    "score_multi_source",
    "score_company_type",
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
                lead_capture_reason AS best_lead_capture_reason
            FROM ranked_leads
            WHERE rn = 1
        ),
        run_scores AS (
            SELECT
                cs.company_key,
                cs.opportunity_score,
                cs.score_openings,
                cs.score_remote,
                cs.score_contractor,
                cs.score_multi_source,
                cs.score_company_type
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
            COALESCE(s.score_openings, 0) AS score_openings,
            COALESCE(s.score_remote, 0) AS score_remote,
            COALESCE(s.score_contractor, 0) AS score_contractor,
            COALESCE(s.score_multi_source, 0) AS score_multi_source,
            COALESCE(s.score_company_type, 0) AS score_company_type,
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
        rows = self._build_commercial_pipeline_rows()
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

    def export_commercial_report_markdown(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        lines: List[str] = []
        lines.append(f"# Commercial report - run {self.ctx.run_id}")
        lines.append("")

        for row in rows:
            company_key = row.get("company_key", "")
            company_name = row.get("company_display") or "Unknown"
            website = row.get("resolved_domain") or ""
            company_linkedin = row.get("linkedin_company_url") or ""
            industry = row.get("industry") or "N/D"
            size = row.get("company_size") or row.get("employee_range") or "N/D"
            outreach_status = row.get("outreach_status") or "N/D"
            priority = row.get("commercial_priority_score") or 0

            jobs = self._build_company_jobs(company_key)
            contacts = self._build_company_contacts(company_key)

            lines.append(f"## {company_name}")
            lines.append(f"- Website: {'https://' + website if website else 'N/D'}")
            lines.append(f"- LinkedIn company: {company_linkedin or 'N/D'}")
            lines.append(f"- Industry: {industry}")
            lines.append(f"- Size: {size}")
            lines.append(f"- Opportunity score: {row.get('opportunity_score', 0)}")
            lines.append(f"- Commercial priority score: {priority}")
            lines.append(f"- Outreach status: {outreach_status}")
            lines.append("")

            lines.append("### Posiciones")
            if jobs:
                for idx, job in enumerate(jobs, start=1):
                    lines.append(f"{idx}. {self._job_summary(job)}")
                    if job.get("job_url"):
                        lines.append(f"   - Job URL: {job.get('job_url')}")
                    if job.get("apply_url"):
                        lines.append(f"   - Apply URL: {job.get('apply_url')}")
            else:
                lines.append("Sin posiciones registradas en este run.")
            lines.append("")

            lines.append("### Contactos")
            if contacts:
                for idx, contact in enumerate(contacts, start=1):
                    lines.append(
                        f"{idx}. Nombre: {contact.get('contact_name') or 'N/D'} | "
                        f"Puesto: {contact.get('contact_title') or 'N/D'} | "
                        f"Email: {contact.get('email') or 'N/D'} | "
                        f"LinkedIn: {contact.get('linkedin_url') or 'N/D'} | "
                        f"Source: {contact.get('lead_source') or 'N/D'} | "
                        f"Confidence: {contact.get('lead_confidence') or 0} | "
                        f"Email quality: {contact.get('email_quality_score') or 0}"
                    )
            else:
                lines.append("Sin contactos relevantes todavía.")
            lines.append("")
            lines.append("---")
            lines.append("")

        path = self._output_dir() / "commercial_report.md"
        output = self._write_text(path, "\n".join(lines).rstrip() + "\n")
        self.ctx.paths["commercial_report_md"] = output
        self.ctx.metrics["commercial_report_rows"] = len(rows)
        return output

    def export_all(self) -> None:
        self.export_commercial_pipeline()
        self.export_apollo_import()
        self.export_commercial_report_markdown()
