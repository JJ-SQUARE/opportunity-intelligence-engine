from typing import Any, Dict, List
import pandas as pd

def export_companies_csv(companies: List[Dict[str, Any]], path: str) -> str:
    # No exportamos jobs completos (pesado). Solo campos útiles.
    rows = []
    for c in companies:
        rows.append(
            {
                "company": c.get("company"),
                "total_openings": c.get("total_openings"),
                "score": c.get("score"),
                "country_focus": c.get("country_focus"),
                "remote_friendly_signal": c.get("remote_friendly_signal"),
                "nearshore_friendly_signal": c.get("nearshore_friendly_signal"),
                "contractor_signal": c.get("contractor_signal"),
                "urgency_signal": c.get("urgency_signal"),
                "domain_guess": c.get("domain_guess"),
                "company_type_ai": c.get("company_type_ai"),
                "industry_ai": c.get("industry_ai"),
                "vendor_acceptance_probability_ai": c.get("vendor_acceptance_probability_ai"),
                "notes_ai": " | ".join(c.get("notes_ai") or []),
                "us_only_signal": c.get("us_only_signal"),
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path