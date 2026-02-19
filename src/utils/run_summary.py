from typing import Any, Dict, List
import os


def write_run_summary(
    run_dir: str,
    jobs_count: int,
    companies_count: int,
    end_clients: List[Dict[str, Any]],
    partners: List[Dict[str, Any]],
    competitive_list: List[Dict[str, Any]],
    leads_count: int,
) -> str:

    path = os.path.join(run_dir, "RUN_SUMMARY.txt")

    lines: List[str] = []

    lines.append("RUN SUMMARY")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"Jobs collected: {jobs_count}")
    lines.append(f"Companies detected: {companies_count}")
    lines.append("")
    lines.append(f"End Clients (Sales Opportunities): {len(end_clients)}")
    lines.append(f"Partners (Consulting / Agencies): {len(partners)}")
    lines.append(f"Competitive Watchlist: {len(competitive_list)}")
    lines.append(f"Leads generated: {leads_count}")
    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    # -------------------------
    # TOP END CLIENTS
    # -------------------------
    lines.append("TOP END CLIENT OPPORTUNITIES")
    lines.append("-" * 60)

    for i, c in enumerate(end_clients[:10], start=1):
        company = c.get("company")
        score = c.get("score")
        band = c.get("priority_band")
        domain = c.get("resolved_domain")
        vendor = c.get("vendor_acceptance_probability_ai")

        lines.append(
            f"{i}. {company} | Score: {score} | {band} | VendorProb: {vendor}% | {domain}"
        )

    lines.append("")
    lines.append("")

    # -------------------------
    # TOP PARTNERS
    # -------------------------
    lines.append("TOP PARTNER OPPORTUNITIES")
    lines.append("-" * 60)

    for i, c in enumerate(partners[:10], start=1):
        company = c.get("company")
        score = c.get("score")
        band = c.get("priority_band")
        domain = c.get("resolved_domain")
        openings = c.get("total_openings")

        lines.append(
            f"{i}. {company} | Score: {score} | {band} | Openings: {openings} | {domain}"
        )

    lines.append("")
    lines.append("")

    # -------------------------
    # TOP COMPETITIVE
    # -------------------------
    lines.append("TOP COMPETITIVE WATCHLIST")
    lines.append("-" * 60)

    for i, c in enumerate(competitive_list[:10], start=1):
        company = c.get("company")
        score = c.get("score")
        openings = c.get("total_openings")
        domain = c.get("resolved_domain")

        lines.append(
            f"{i}. {company} | Score: {score} | Openings: {openings} | {domain}"
        )

    lines.append("")
    lines.append("=" * 60)
    lines.append("")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return path