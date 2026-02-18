from typing import Any, Dict, List
import pandas as pd


def export_competitive_watchlist_csv(items: List[Dict[str, Any]], path: str) -> str:
    rows = []
    for c in items:
        rows.append(
            {
                "priority_band": c.get("priority_band"),
                "score": c.get("score"),
                "company": c.get("company"),
                "resolved_domain": c.get("resolved_domain") or c.get("domain_guess"),
                "company_type": c.get("company_type_ai"),
                "industry": c.get("industry_ai"),
                "total_openings": c.get("total_openings"),
                "contractor_signal": c.get("contractor_signal"),
                "remote_friendly_signal": c.get("remote_friendly_signal"),
                "us_only_signal": c.get("us_only_signal"),
                "country_focus": c.get("country_focus"),
                "sample_titles": " | ".join((c.get("titles") or [])[:6]),
            }
        )

    df = pd.DataFrame(rows)
    df.to_csv(path, index=False)
    return path