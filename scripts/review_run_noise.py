from __future__ import annotations

import csv
import sys
from pathlib import Path

NOISE_HINTS = [
    "survey",
    "market research",
    "data entry",
    "customer service representative",
    "supplemental life insurance",
    "warm leads",
    "forex",
    "crypto",
    "trading",
    "side gig",
    "part time",
    "focus groups",
    "product testing",
    "call center",
]

def main(run_dir: str) -> int:
    companies_csv = Path(run_dir) / "companies_scored.csv"
    jobs_csv = Path(run_dir) / "jobs_enriched.csv"

    if not companies_csv.exists():
        print(f"missing: {companies_csv}")
        return 1

    print(f"reviewing run: {run_dir}")
    print("-" * 80)

    with companies_csv.open(newline="", encoding="utf-8") as f:
        companies = list(csv.DictReader(f))

    print("COMPANIES")
    for row in companies:
        notes = (row.get("notes_ai") or "").lower()
        desc = (row.get("sample_description") or "").lower()
        combined = notes + " " + desc
        noise_hits = [hint for hint in NOISE_HINTS if hint in combined]

        print(
            f"- company={row.get('company')} "
            f"type={row.get('company_type_ai')} "
            f"score={row.get('score')} "
            f"vendor_prob={row.get('vendor_acceptance_probability_ai')} "
            f"noise_hits={len(noise_hits)}"
        )
        if noise_hits:
            print(f"  hints={noise_hits}")

    if jobs_csv.exists():
        print("-" * 80)
        print("JOBS")
        with jobs_csv.open(newline="", encoding="utf-8") as f:
            jobs = list(csv.DictReader(f))
        for row in jobs[:20]:
            text = ((row.get("description") or "") + " " + (row.get("company") or "")).lower()
            noise_hits = [hint for hint in NOISE_HINTS if hint in text]
            print(
                f"- company={row.get('company')} "
                f"source={row.get('source')} "
                f"remote={row.get('is_remote')} "
                f"contractor={row.get('is_contractor')} "
                f"noise_hits={len(noise_hits)}"
            )
            if noise_hits:
                print(f"  hints={noise_hits}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))
