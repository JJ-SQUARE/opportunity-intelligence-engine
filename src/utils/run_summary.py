from typing import Any, Dict, List
import os


def write_run_summary(
    run_dir: str,
    jobs_count: int,
    companies_count: int,
    sales_list: List[Dict[str, Any]],
    competitive_list: List[Dict[str, Any]],
    leads_count: int,
) -> str:
    path = os.path.join(run_dir, "RUN_SUMMARY.txt")

    lines = []
    lines.append("RUN SUMMARY")
    lines.append("=" * 50)
    lines.append("")
    lines.append(f"Jobs collected: {jobs_count}")
    lines.append(f"Companies detected: {companies_count}")
    lines.append("")
    lines.append(f"Sales Opportunities: {len(sales_list)}")
    lines.append(f"Competitive Watchlist: {len(competitive_list)}")
    lines.append(f"Leads generated: {leads_count}")
    lines.append("")
    lines.append("TOP SALES OPPORTUNITIES")
    lines.append("-" * 50)

    for i, c in enumerate(sales_list[:10], start=1):
        company = c.get("company")
        score = c.get("score")
        band = c.get("priority_band")
        why = c.get("why_priority")
        domain = c.get("resolved_domain")

        lines.append(
            f"{i}. {company} | Score: {score} | {band} | {why} | {domain}"
        )

    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path