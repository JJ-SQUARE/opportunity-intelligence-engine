from typing import Any, Dict, List, Tuple


def classify_priority(score: float, high_min: float, medium_min: float) -> str:
    if score >= high_min:
        return "HIGH"
    if score >= medium_min:
        return "MEDIUM"
    return "LOW"


def build_sales_and_competitive_lists(
    companies: List[Dict[str, Any]],
    cfg: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:

    sales_cfg = cfg.get("sales", {})
    comp_cfg = cfg.get("competitive", {})

    high_min = float(sales_cfg.get("high_min_score", 14))
    med_min = float(sales_cfg.get("medium_min_score", 11))
    vendor_min = float(sales_cfg.get("vendor_prob_min", 70))
    exclude_types = set(sales_cfg.get("exclude_company_types", []))
    require_not_us_only = bool(sales_cfg.get("require_not_us_only", True))
    max_medium = int(sales_cfg.get("max_medium", 25))

    # Competitive
    comp_enabled = bool(comp_cfg.get("enabled", True))
    comp_types = set(comp_cfg.get("include_company_types", ["staffing_agency"]))
    comp_min_openings = int(comp_cfg.get("min_openings", 2))

    sales_candidates: List[Dict[str, Any]] = []
    competitive: List[Dict[str, Any]] = []

    for c in companies:
        score = float(c.get("score") or 0)
        company_type = c.get("company_type_ai") or "unknown"
        vendor_prob = float(c.get("vendor_acceptance_probability_ai") or 0)
        us_only = bool(c.get("us_only_signal"))

        # ---- Competitive watchlist ----
        if comp_enabled and company_type in comp_types and int(c.get("total_openings") or 0) >= comp_min_openings:
            cc = dict(c)
            cc["priority_band"] = classify_priority(score, high_min, med_min)
            competitive.append(cc)

        # ---- Sales eligibility ----
        if company_type in exclude_types:
            continue
        if require_not_us_only and us_only:
            continue
        if vendor_prob < vendor_min:
            continue

        sc = dict(c)
        sc["priority_band"] = classify_priority(score, high_min, med_min)
        sales_candidates.append(sc)

    # Ordenar por score desc
    sales_candidates.sort(key=lambda x: float(x.get("score") or 0), reverse=True)

    # Regla C: todos los HIGH + top N MEDIUM
    high = [c for c in sales_candidates if c["priority_band"] == "HIGH"]
    medium = [c for c in sales_candidates if c["priority_band"] == "MEDIUM"][:max_medium]

    sales_final = high + medium
    # volver a ordenar por score por si high/medium mezcló
    sales_final.sort(key=lambda x: float(x.get("score") or 0), reverse=True)

    # Competitive ordenado por openings desc y score desc
    competitive.sort(
        key=lambda x: (int(x.get("total_openings") or 0), float(x.get("score") or 0)),
        reverse=True,
    )

    return sales_final, competitive