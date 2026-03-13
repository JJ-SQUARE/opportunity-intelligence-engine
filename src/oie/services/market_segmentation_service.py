from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class MarketSegmentationService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _text_for_company(self, company: Dict[str, Any]) -> str:
        parts = [
            company.get("company", ""),
            company.get("company_display", ""),
            company.get("industry_ai", ""),
            company.get("company_type_ai", ""),
            company.get("sample_description", ""),
            " ".join(company.get("notes_ai", []) or []) if isinstance(company.get("notes_ai"), list) else str(company.get("notes_ai") or ""),
        ]
        return " ".join(str(x) for x in parts if x).lower()

    def _segment_company(self, company: Dict[str, Any]) -> str:
        text = self._text_for_company(company)
        company_type = str(company.get("company_type_ai") or "").lower()
        industry = str(company.get("industry_ai") or "").lower()

        gig_hints = [
            "survey",
            "market research",
            "data entry",
            "side gig",
            "focus groups",
            "product testing",
            "warm leads",
        ]
        speculative_hints = [
            "forex",
            "crypto",
            "trading",
            "funded trading",
            "profit split",
        ]
        commercial_ops_hints = [
            "customer service",
            "call center",
            "sales representative",
            "insurance",
            "credentialing",
            "recruiting",
            "staffing",
            "provider recruiting",
        ]
        tech_hints = [
            "software",
            "developer",
            "engineering",
            "cloud",
            "devops",
            "data engineer",
            "full stack",
            "backend",
            "frontend",
            "qa automation",
            "llm",
            "genai",
            "ai strategy",
            "platform",
            "rag",
            "mlops",
        ]

        if any(hint in text for hint in gig_hints):
            return "gig_remote_labor"

        if any(hint in text for hint in speculative_hints):
            return "speculative_remote_labor"

        if company_type in {"staffing_agency", "consulting"}:
            if any(hint in text for hint in tech_hints):
                return "partner_tech_services"
            return "partner_general_services"

        if company_type == "product_company":
            if any(hint in text for hint in tech_hints):
                return "tech_product_hiring"
            return "digital_product_noncore"

        if any(hint in text for hint in tech_hints):
            return "broad_tech_hiring"

        if any(hint in text for hint in commercial_ops_hints):
            return "commercial_ops_remote"

        if industry in {"healthcare", "insurance", "customer_service", "market research"}:
            return "broad_remote_nontech"

        return "unclassified_remote"

    def segment_companies(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        counts = Counter()

        for company in companies:
            segment = self._segment_company(company)
            counts[segment] += 1

            record = dict(company)
            record["market_segment"] = segment
            rows.append(record)

        self.ctx.metrics["market_segments_detected"] = len(counts)
        for key, value in counts.items():
            self.ctx.metrics[f"market_segment_{key}_count"] = value

        return rows

    def build_segment_summary(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        segmented = self.segment_companies(companies)
        summary: Dict[str, Dict[str, Any]] = {}

        for company in segmented:
            segment = company.get("market_segment", "unclassified_remote")
            item = summary.setdefault(
                segment,
                {
                    "market_segment": segment,
                    "companies": 0,
                    "avg_score": 0.0,
                    "avg_vendor_prob": 0.0,
                    "top_examples": [],
                },
            )
            item["companies"] += 1
            item["avg_score"] += float(company.get("score") or 0)
            item["avg_vendor_prob"] += float(company.get("vendor_acceptance_probability_ai") or 0)

            if len(item["top_examples"]) < 5:
                item["top_examples"].append(company.get("company"))

        rows = list(summary.values())
        for row in rows:
            count = max(int(row["companies"]), 1)
            row["avg_score"] = round(row["avg_score"] / count, 2)
            row["avg_vendor_prob"] = round(row["avg_vendor_prob"] / count, 2)
            row["top_examples"] = " | ".join(str(x) for x in row["top_examples"] if x)

        rows.sort(key=lambda r: (r["companies"], r["avg_score"]), reverse=True)
        self.ctx.metrics["market_segment_summary_rows"] = len(rows)
        return rows
