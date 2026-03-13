from __future__ import annotations

import csv
import sys
from pathlib import Path
from collections import Counter

def read_rows(path: Path):
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def main(run_dir: str) -> int:
    run_path = Path(run_dir)

    jobs = read_rows(run_path / "jobs_enriched.csv")
    companies = read_rows(run_path / "companies_scored.csv")
    leads = read_rows(run_path / "leads.csv")
    sales = read_rows(run_path / "sales_opportunities.csv")
    partners = read_rows(run_path / "partner_opportunities.csv")
    watchlist = read_rows(run_path / "competitive_watchlist.csv")

    print(f"run_dir={run_dir}")
    print(f"jobs={len(jobs)}")
    print(f"companies={len(companies)}")
    print(f"leads={len(leads)}")
    print(f"sales={len(sales)}")
    print(f"partners={len(partners)}")
    print(f"watchlist={len(watchlist)}")

    type_counter = Counter(row.get("company_type_ai", "unknown") for row in companies)
    print("company_types=", dict(type_counter))

    top = sorted(
        companies,
        key=lambda r: (
            float(r.get("score") or 0),
            float(r.get("vendor_acceptance_probability_ai") or 0),
        ),
        reverse=True,
    )[:10]

    print("\nTOP COMPANIES")
    for row in top:
        print(
            f"- {row.get('company')} | "
            f"type={row.get('company_type_ai')} | "
            f"score={row.get('score')} | "
            f"vendor_prob={row.get('vendor_acceptance_probability_ai')} | "
            f"industry={row.get('industry_ai')}"
        )

    return 0

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
