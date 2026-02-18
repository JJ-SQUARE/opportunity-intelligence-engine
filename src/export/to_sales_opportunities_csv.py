from typing import Any, Dict, List
import pandas as pd


def export_sales_opportunities_csv(items: List[Dict[str, Any]], path: str) -> str:
    rows = []
    for c in items:
        rows.append(
            {
                "priority_band": c.get("priority_band"),
                "score": c.get("score"),
                "vendor_prob": c.get("vendor_acceptance_probability_ai"),
                "company": c.get("company"),
                "resolved_domain": c.get("resolved_domain") or c.get("domain_guess"),
                "industry": c.get("industry_ai"),
                "company_type": c.get("company_type_ai"),

                "total_openings": c.get("total_openings"),
                "urgency_signal": c.get("urgency_signal"),
                "contractor_signal": c.get("contractor_signal"),
                "remote_friendly_signal": c.get("remote_friendly_signal"),
                "nearshore_friendly_signal": c.get("nearshore_friendly_signal"),
                "us_only_signal": c.get("us_only_signal"),

                # contexto útil
                "country_focus": c.get("country_focus"),
                "sample_titles": " | ".join((c.get("titles") or [])[:6]),
                "sample_locations": " | ".join((c.get("locations") or [])[:6]),
                "notes_ai": " | ".join(c.get("notes_ai") or []),
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path