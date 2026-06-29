from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.commercial_selection_service import CommercialSelectionService
from oie.services.commercial_row_service import CommercialRowService
from oie.services.commercial_signal_service import CommercialSignalService
from oie.services.job_text_service import build_job_summary


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
    "domain_ai_validated",
    "domain_ai_decision",
    "domain_ai_confidence",
    "domain_ai_reason",
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
    "commercial_bucket",
    "commercial_priority_score",
    "icp_bucket",
    "reachability_ready",
    "real_reachability_ready",
    "soft_reachability_ready",
    "commercially_actionable",
    "company_domain_usable",
    "commercial_domain_usable",
    "contact_channel_ready",
    "company_channel_ready",
]


APOLLO_IMPORT_FIELDS = [
    "name",
    "website",
    "linkedin_url",
]

class OutboundExportService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx
        self.commercial_row_service = CommercialRowService(ctx)
        self.commercial_signal_service = self.commercial_row_service.commercial_signal_service
        self.commercial_selection_service = self.commercial_row_service.commercial_selection_service

    def _output_dir(self) -> Path:
        output_dir = Path(
            self.ctx.paths.get("output_dir")
            or Path(self.ctx.config.get("outputs", {}).get("path", "data/outputs")) / self.ctx.run_id
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        self.ctx.paths["output_dir"] = str(output_dir)
        return output_dir

    def _query_rows(self, query: str, params: tuple[Any, ...] = ()) -> List[Dict[str, Any]]:
        return self.commercial_row_service.query_rows(query, params)

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
        return self.commercial_row_service.build_commercial_pipeline_rows()

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
            except Exception as exc:
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

    def _job_summary(self, job: Dict[str, Any]) -> str:
        return build_job_summary(job)

    def _safe_float(self, value: Any, default: float = 0.0) -> float:
        try:
            return float(value if value is not None else default)
        except Exception:
            return default

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value if value is not None else default)
        except Exception:
            return default

    def _derived_suggested_outreach_channel(self, row: Dict[str, Any]) -> str:
        return self.commercial_signal_service.derived_suggested_outreach_channel(row)

    def _derived_outreach_status(self, row: Dict[str, Any]) -> str:
        return self.commercial_signal_service.derived_outreach_status(row)

    def _derived_icp_bucket(self, row: Dict[str, Any]) -> str:
        return self.commercial_signal_service.derived_icp_bucket(row)

    def _derived_reachability_ready(self, row: Dict[str, Any]) -> int:
        return self.commercial_signal_service.derived_reachability_ready(row)

    def _derived_commercial_bucket(self, row: Dict[str, Any]) -> str:
        return self.commercial_signal_service.derived_commercial_bucket(row)

    def _derived_commercial_priority_score(self, row: Dict[str, Any]) -> int:
        return self.commercial_signal_service.derived_commercial_priority_score(row)

    def _finalize_commercial_row(self, row: Dict[str, Any]) -> Dict[str, Any]:
        return self.commercial_row_service.finalize_row(row)

    def _finalize_commercial_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.commercial_row_service.finalize_rows(rows)

    def export_commercial_pipeline(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        path = self._output_dir() / "commercial_pipeline.csv"
        output = self._write_csv(path, COMMERCIAL_PIPELINE_FIELDS, rows)
        self.ctx.paths["commercial_pipeline_csv"] = output
        self.ctx.metrics["commercial_pipeline_rows"] = len(rows)
        return output

    def _commercial_bucket(self, row: Dict[str, Any]) -> str:
        return str(row.get("commercial_bucket") or "").strip().lower()

    def _rows_for_apollo_import(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.commercial_row_service.commercial_selection_service.rows_for_apollo_import(rows)

    def export_apollo_import(self) -> str:
        rows = self._rows_for_apollo_import(self._build_commercial_pipeline_rows())
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

    def _resolve_env_style_value(self, value: Any) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""

        match = re.fullmatch(r"\$\{([A-Z0-9_]+)\}", raw)
        if match:
            return str(os.getenv(match.group(1), "")).strip()

        return raw

    def _normalize_hubspot_owner(self) -> str:
        return self._resolve_env_style_value(self._hubspot_config().get("owner_id"))

    def _normalize_hubspot_target_account(self) -> str:
        return self._resolve_env_style_value(self._hubspot_config().get("target_account"))

    def _normalize_hubspot_source_tag(self) -> str:
        return str(self._hubspot_config().get("source_tag") or "OIE").strip() or "OIE"

    def _hubspot_custom_properties_enabled(self) -> bool:
        return bool(self._hubspot_config().get("custom_properties_enabled", False))

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

    def _normalized_company_type(self, value: Any) -> str:
        return self.commercial_signal_service.normalized_company_type(value)

    def _is_benchmark_row(self, row: Dict[str, Any]) -> bool:
        company_type = self._normalized_company_type(row.get("company_type_ai"))
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
            "DEFENSE_AND_SPACE": "DEFENSE_SPACE",
            "DEFENSE_AEROSPACE": "DEFENSE_SPACE",
            "AEROSPACE_DEFENSE": "DEFENSE_SPACE",
            "AVIATION_AND_AEROSPACE": "AVIATION_AEROSPACE",
            "IT_SERVICES": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "INFORMATION_TECHNOLOGY": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "INFORMATION_TECHNOLOGY_SERVICES": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "TECHNOLOGY": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "TECH": "INFORMATION_TECHNOLOGY_AND_SERVICES",
            "SOFTWARE": "COMPUTER_SOFTWARE",
            "SAAS": "COMPUTER_SOFTWARE",
            "FINTECH": "FINANCIAL_SERVICES",
            "BANKING_AND_FINANCIAL_SERVICES": "FINANCIAL_SERVICES",
            "BFSI": "FINANCIAL_SERVICES",
            "HEALTHCARE": "HOSPITAL_HEALTH_CARE",
            "HEALTH_CARE": "HOSPITAL_HEALTH_CARE",
            "HEALTH_TECH": "HOSPITAL_HEALTH_CARE",
            "HEALTHTECH": "HOSPITAL_HEALTH_CARE",
            "LOGISTICS": "LOGISTICS_AND_SUPPLY_CHAIN",
            "SUPPLY_CHAIN": "LOGISTICS_AND_SUPPLY_CHAIN",
            "LOGISTICS_SUPPLY_CHAIN": "LOGISTICS_AND_SUPPLY_CHAIN",
            "TRANSPORTATION": "LOGISTICS_AND_SUPPLY_CHAIN",
            "E_COMMERCE": "INTERNET",
            "ECOMMERCE": "INTERNET",
            "EDTECH": "E_LEARNING",
            "EDUCATION_TECHNOLOGY": "E_LEARNING",
            "STAFFING": "HUMAN_RESOURCES",
            "STAFFING_RECRUITING": "HUMAN_RESOURCES",
            "STAFFING_AND_RECRUITING": "HUMAN_RESOURCES",
            "RECRUITING": "HUMAN_RESOURCES",
            "HUMAN_RESOURCES_SERVICES": "HUMAN_RESOURCES",
            "COMPUTER_AND_NETWORK_SECURITY": "COMPUTER_NETWORK_SECURITY",
        }

        allowed = {
            "ACCOUNTING", "AIRLINES_AVIATION", "ALTERNATIVE_DISPUTE_RESOLUTION",
            "ALTERNATIVE_MEDICINE", "ANIMATION", "APPAREL_FASHION",
            "ARCHITECTURE_PLANNING", "ARTS_AND_CRAFTS", "AUTOMOTIVE",
            "AVIATION_AEROSPACE", "BANKING", "BIOTECHNOLOGY",
            "BROADCAST_MEDIA", "BUILDING_MATERIALS",
            "BUSINESS_SUPPLIES_AND_EQUIPMENT", "CAPITAL_MARKETS", "CHEMICALS",
            "CIVIC_SOCIAL_ORGANIZATION", "CIVIL_ENGINEERING",
            "COMMERCIAL_REAL_ESTATE", "COMPUTER_NETWORK_SECURITY",
            "COMPUTER_GAMES", "COMPUTER_HARDWARE", "COMPUTER_NETWORKING",
            "COMPUTER_SOFTWARE", "INTERNET", "CONSTRUCTION",
            "CONSUMER_ELECTRONICS", "CONSUMER_GOODS", "CONSUMER_SERVICES",
            "COSMETICS", "DAIRY", "DEFENSE_SPACE", "DESIGN",
            "EDUCATION_MANAGEMENT", "E_LEARNING",
            "ELECTRICAL_ELECTRONIC_MANUFACTURING", "ENTERTAINMENT",
            "ENVIRONMENTAL_SERVICES", "EVENTS_SERVICES", "EXECUTIVE_OFFICE",
            "FACILITIES_SERVICES", "FARMING", "FINANCIAL_SERVICES",
            "FINE_ART", "FISHERY", "FOOD_BEVERAGES", "FOOD_PRODUCTION",
            "FUND_RAISING", "FURNITURE", "GAMBLING_CASINOS",
            "GLASS_CERAMICS_CONCRETE", "GOVERNMENT_ADMINISTRATION",
            "GOVERNMENT_RELATIONS", "GRAPHIC_DESIGN",
            "HEALTH_WELLNESS_AND_FITNESS", "HIGHER_EDUCATION",
            "HOSPITAL_HEALTH_CARE", "HOSPITALITY", "HUMAN_RESOURCES",
            "IMPORT_AND_EXPORT", "INDIVIDUAL_FAMILY_SERVICES",
            "INDUSTRIAL_AUTOMATION", "INFORMATION_SERVICES",
            "INFORMATION_TECHNOLOGY_AND_SERVICES", "INSURANCE",
            "INTERNATIONAL_AFFAIRS", "INTERNATIONAL_TRADE_AND_DEVELOPMENT",
            "INVESTMENT_BANKING", "INVESTMENT_MANAGEMENT", "JUDICIARY",
            "LAW_ENFORCEMENT", "LAW_PRACTICE", "LEGAL_SERVICES",
            "LEGISLATIVE_OFFICE", "LEISURE_TRAVEL_TOURISM", "LIBRARIES",
            "LOGISTICS_AND_SUPPLY_CHAIN", "LUXURY_GOODS_JEWELRY",
            "MACHINERY", "MANAGEMENT_CONSULTING", "MARITIME",
            "MARKET_RESEARCH", "MARKETING_AND_ADVERTISING",
            "MECHANICAL_OR_INDUSTRIAL_ENGINEERING", "MEDIA_PRODUCTION",
            "MEDICAL_DEVICES", "MEDICAL_PRACTICE", "MENTAL_HEALTH_CARE",
            "MILITARY", "MINING_METALS", "MOTION_PICTURES_AND_FILM",
            "MUSEUMS_AND_INSTITUTIONS", "MUSIC", "NANOTECHNOLOGY",
            "NEWSPAPERS", "NON_PROFIT_ORGANIZATION_MANAGEMENT",
            "OIL_ENERGY",
        }

        mapped = aliases.get(normalized, normalized)
        return mapped if mapped in allowed else ""

    def _hubspot_company_description(self, row: Dict[str, Any]) -> str:
        lines = [
            f"- Run ID: {self._hubspot_safe_text(self.ctx.run_id) or 'N/D'}",
            f"- Run timestamp: {self._run_timestamp_label()}",
            f"- Website: {'https://' + self._hubspot_safe_text(row.get('resolved_domain')) if self._hubspot_safe_text(row.get('resolved_domain')) else 'N/D'}",
            f"- LinkedIn company: {self._hubspot_safe_text(row.get('linkedin_company_url')) or 'N/D'}",
            f"- Industry: {self._hubspot_safe_text(row.get('industry')) or 'N/D'}",
            f"- Size: {self._hubspot_safe_text(row.get('company_size') or row.get('employee_range')) or 'N/D'}",
            f"- Company type: {self._hubspot_safe_text(row.get('company_type_ai')) or 'N/D'}",
            f"- Commercial bucket: {self._hubspot_safe_text(row.get('commercial_bucket')) or 'N/D'}",
            f"- Opportunity score: {row.get('opportunity_score') or 0}",
            f"- Commercial priority score: {row.get('commercial_priority_score') or 0}",
            f"- Outreach status: {self._hubspot_safe_text(row.get('outreach_status')) or 'N/D'}",
            f"- Source: {self._normalize_hubspot_source_tag()}",
        ]
        return "\n\n".join(lines)

    def _hubspot_number_of_employees(self, row: Dict[str, Any]) -> str:
        raw = self._hubspot_safe_text(row.get("company_size") or row.get("employee_range"))
        if not raw:
            return ""

        digits = re.findall(r"\d+", raw.replace(",", ""))
        if not digits:
            return ""

        if len(digits) >= 2:
            return digits[-1]

        return digits[0]

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
        max_contacts = limit
        if max_contacts is None:
            max_contacts = int(
                ((self.ctx.config.get("hubspot", {}) or {}).get("max_contacts_per_company", 3) or 3)
            )

        return self.commercial_row_service.select_contacts(
            company_key,
            max_contacts=max_contacts,
            min_relevance_score=45,
        )

    def _is_deprioritized_for_outreach(self, row: Dict[str, Any]) -> bool:
        return self.commercial_selection_service.is_deprioritized_for_outreach(row)

    def _rows_with_selected_contacts(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        max_contacts = int(
            ((self.ctx.config.get("hubspot", {}) or {}).get("max_contacts_per_company", 3) or 3)
        )
        return self.commercial_row_service.rows_with_selected_contacts(
            rows,
            max_contacts=max_contacts,
            min_relevance_score=45,
        )

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
                "type": "PROSPECT",
                "description": self._hubspot_safe_text(self._hubspot_company_description(row), 5000),
            }
            if self._hubspot_custom_properties_enabled():
                properties.update(
                    {
                        "company_type_ai": self._hubspot_safe_text(row.get("company_type_ai")),
                        "commercial_relevance": self._hubspot_safe_text(row.get("commercial_bucket")),
                        "ai_confidence": self._hubspot_safe_text(row.get("classification_confidence_ai")),
                        "reachability_status": self._hubspot_safe_text(row.get("outreach_status")),
                        "pain_signals": self._hubspot_safe_text(row.get("opportunity_score_reason"), 1000),
                    }
                )

            industry = self._map_hubspot_industry(row.get("industry"))
            if industry:
                properties["industry"] = industry

            numberofemployees = self._hubspot_number_of_employees(row)
            if numberofemployees:
                properties["numberofemployees"] = numberofemployees

            if owner_id and owner_id.isdigit():
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
                if self._hubspot_custom_properties_enabled():
                    properties.update(
                        {
                            "buyer_persona_type": self._hubspot_safe_text(contact.get("target_persona") or contact.get("lead_role_type")),
                            "lead_quality_score": self._hubspot_safe_text(contact.get("lead_relevance_score")),
                            "reachability_status": "ready_email",
                        }
                    )
                if owner_id and owner_id.isdigit():
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
                if owner_id and owner_id.isdigit():
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
            result = {
                "enabled": False,
                "pushed": False,
                "reason": "hubspot_push_disabled",
            }
            self.ctx.metrics["hubspot_push_skipped"] = True
            sync_path = self._output_dir() / "hubspot_sync_results.json"
            self._write_text(sync_path, json.dumps(result, ensure_ascii=False, indent=2))
            self.ctx.paths["hubspot_sync_results_json"] = str(sync_path)
            return result

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

        sync_path = self._output_dir() / "hubspot_sync_results.json"
        self._write_text(sync_path, json.dumps(results, ensure_ascii=False, indent=2))
        self.ctx.paths["hubspot_sync_results_json"] = str(sync_path)

        return results


    def export_commercial_report_markdown(self) -> str:
        rows = self._build_commercial_pipeline_rows()
        benchmark_rows = [row for row in rows if self._commercial_bucket(row) == "competitor_watchlist"]
        icp_rows = [row for row in rows if self._commercial_bucket(row) == "icp_target"]
        partner_rows = [row for row in rows if self._commercial_bucket(row) == "partner_candidate"]
        low_fit_rows = [row for row in rows if self._commercial_bucket(row) == "low_fit_noise"]

        lines: List[str] = []
        lines.append("# Commercial Report")
        lines.append("")
        lines.append(f"- Run ID: {self._hubspot_safe_text(self.ctx.run_id) or 'N/D'}")
        lines.append(f"- Run timestamp: {self._run_timestamp_label()}")
        lines.append(f"- ICP targets: {len(icp_rows)}")
        lines.append(f"- Partner candidates: {len(partner_rows)}")
        lines.append(f"- Low-fit noise: {len(low_fit_rows)}")
        lines.append(f"- Benchmark competitors: {len(benchmark_rows)}")
        lines.append("")

        def add_company_section(title: str, section_rows: List[Dict[str, Any]]) -> None:
            lines.append(f"## {title}")
            lines.append("")
            if not section_rows:
                lines.append(f"No {title.lower()} in this run.")
                lines.append("")
                return

            for idx, row in enumerate(section_rows, start=1):
                company_key = self._hubspot_safe_text(row.get("company_key"))
                lines.append(f"### {idx}. {row.get('company_display') or 'Unknown'}")
                lines.append(f"- Domain: {row.get('resolved_domain') or 'N/D'}")
                lines.append(f"- LinkedIn: {row.get('linkedin_company_url') or 'N/D'}")
                lines.append(f"- Industry: {row.get('industry') or 'N/D'}")
                lines.append(f"- Size: {row.get('company_size') or row.get('employee_range') or 'N/D'}")
                lines.append(f"- Company type: {row.get('company_type_ai') or 'N/D'}")
                lines.append(f"- Commercial bucket: {row.get('commercial_bucket') or 'N/D'}")
                lines.append(f"- Opportunity score: {row.get('opportunity_score') or 0}")
                lines.append("- Score breakdown:")
                lines.append(f"  - Openings: {row.get('score_openings', 0)}")
                lines.append(f"  - Remote: {row.get('score_remote', 0)}")
                lines.append(f"  - Contractor: {row.get('score_contractor', 0)}")
                lines.append(f"  - Multi-source: {row.get('score_multi_source', 0)}")
                lines.append(f"  - Company type: {row.get('score_company_type', 0)}")
                lines.append(f"  - ICP fit: {row.get('score_icp_fit', 0)}")
                lines.append(f"  - Pain urgency: {row.get('score_pain_urgency', 0)}")
                lines.append(f"  - Region fit: {row.get('score_region_fit', 0)}")
                lines.append(f"  - Company scale: {row.get('score_company_scale', 0)}")
                lines.append(f"  - Seniority mix: {row.get('score_role_seniority_mix', 0)}")
                lines.append(f"  - Penalty competitor: {row.get('score_penalty_competitor', 0)}")
                lines.append(f"  - Negative signals: {row.get('score_penalty_negative_signals', 0)}")
                lines.append(f"- Opportunity label: {row.get('opportunity_label') or 'N/D'}")
                lines.append(f"- Commercial priority score: {row.get('commercial_priority_score') or 0}")
                lines.append(f"- Outreach status: {row.get('outreach_status') or 'N/D'}")
                lines.append(f"- Primary service fit: {row.get('primary_service_fit') or 'N/D'}")
                lines.append(f"- Buyer persona fit: {row.get('buyer_persona_fit') or 'N/D'}")
                lines.append(f"- Best contact: {row.get('best_contact_name') or 'N/D'} | {row.get('best_contact_title') or 'N/D'}")
                lines.append(f"- Best contact email: {row.get('best_contact_email') or 'N/D'}")
                lines.append(f"- Best contact LinkedIn: {row.get('best_contact_linkedin_url') or 'N/D'}")
                lines.append(f"- Why opportunity: {self._hubspot_safe_text(row.get('opportunity_score_reason') or 'N/D', 500)}")
                lines.append(f"- AI signals: provider={row.get('scoring_provider') or 'N/D'} | model={row.get('scoring_model') or 'N/D'} | mode={row.get('scoring_mode') or 'N/D'}")
                lines.append(f"- Recommended outreach angle: {self._hubspot_safe_text(row.get('best_lead_score_reason') or row.get('opportunity_score_reason') or 'N/D', 500)}")
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

        add_company_section("ICP targets", icp_rows)
        add_company_section("Partner candidates", partner_rows)
        add_company_section("Low-fit noise", low_fit_rows)

        lines.append("## Benchmark competitors")
        lines.append("")
        if benchmark_rows:
            for idx, row in enumerate(benchmark_rows, start=1):
                company_key = self._hubspot_safe_text(row.get("company_key"))
                lines.append(f"### {idx}. {row.get('company_display') or 'Unknown'}")
                lines.append(f"- Company type: {row.get('company_type_ai') or 'competitor'}")
                lines.append(f"- Commercial bucket: {row.get('commercial_bucket') or 'competitor_watchlist'}")
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
        self.ctx.metrics["commercial_report_companies"] = len(icp_rows) + len(partner_rows) + len(low_fit_rows)
        self.ctx.metrics["commercial_report_benchmark_companies"] = len(benchmark_rows)
        return output


    def export_all(self) -> None:
        self.export_commercial_pipeline()
        self.export_apollo_import()
        self.export_hubspot_payloads()
        self.export_commercial_report_markdown()
