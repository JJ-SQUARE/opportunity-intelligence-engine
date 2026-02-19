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
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Returns:
        end_clients,
        partners,
        competitive
    """

    sales_cfg = cfg.get("sales", {})
    comp_cfg = cfg.get("competitive", {})
    seg_cfg = cfg.get("segmentation", {})

    # ---- Thresholds ----
    high_min = float(sales_cfg.get("high_min_score", 14))
    med_min = float(sales_cfg.get("medium_min_score", 11))
    vendor_min = float(sales_cfg.get("vendor_prob_min", 70))
    require_not_us_only = bool(sales_cfg.get("require_not_us_only", True))
    max_medium = int(sales_cfg.get("max_medium", 25))

    exclude_types = {x.strip().lower() for x in sales_cfg.get("exclude_company_types", [])}

    # ---- Segmentation ----
    mode = (seg_cfg.get("mode", "split") or "split").strip().lower()
    partner_types = {x.strip().lower() for x in seg_cfg.get("partner_types", ["consulting", "staffing_agency"])}
    end_client_exclude_types = {x.strip().lower() for x in seg_cfg.get("end_client_exclude_types", ["staffing_agency"])}

    # ---- Competitive ----
    comp_enabled = bool(comp_cfg.get("enabled", True))
    comp_types = {x.strip().lower() for x in comp_cfg.get("include_company_types", ["staffing_agency"])}
    comp_min_openings = int(comp_cfg.get("min_openings", 2))

    end_candidates: List[Dict[str, Any]] = []
    partner_candidates: List[Dict[str, Any]] = []
    competitive: List[Dict[str, Any]] = []

    for c in companies:
        score = float(c.get("score") or 0)
        company_type = (c.get("company_type_ai") or "unknown").strip().lower()
        vendor_prob_raw = c.get("vendor_acceptance_probability_ai")
        vendor_prob = float(vendor_prob_raw) if vendor_prob_raw is not None else None
        us_only = bool(c.get("us_only_signal"))
        openings = int(c.get("total_openings") or 0)

        # ---- Competitive watchlist ----
        if comp_enabled and company_type in comp_types and openings >= comp_min_openings:
            cc = dict(c)
            cc["priority_band"] = classify_priority(score, high_min, med_min)
            cc["segment"] = "competitive"
            competitive.append(cc)

        # ---- Sales eligibility ----
        if company_type in exclude_types:
            continue
        if require_not_us_only and us_only:
            continue
        if vendor_prob is not None and vendor_prob < vendor_min:
            continue

        sc = dict(c)
        sc["priority_band"] = classify_priority(score, high_min, med_min)

        is_partner = company_type in partner_types
        is_end_client = company_type not in end_client_exclude_types

        # ---- Mode handling ----

        if mode == "exclude":
            # Solo end clients
            if is_end_client:
                sc["segment"] = "end_client"
                end_candidates.append(sc)
            continue

        if mode == "include_all":
            if is_partner:
                sc["segment"] = "partner"
            else:
                sc["segment"] = "end_client"
            end_candidates.append(sc)
            continue

        # ---- Default: split ----
        if is_partner:
            sc_partner = dict(sc)
            sc_partner["segment"] = "partner"
            partner_candidates.append(sc_partner)

        if is_end_client:
            sc_client = dict(sc)
            sc_client["segment"] = "end_client"
            end_candidates.append(sc_client)

    # ---- Finalize priority selection ----

    def finalize(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
        high = [x for x in candidates if x["priority_band"] == "HIGH"]
        medium = [x for x in candidates if x["priority_band"] == "MEDIUM"][:max_medium]
        final = high + medium
        final.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
        return final

    end_clients = finalize(end_candidates)
    partners = finalize(partner_candidates) if mode == "split" else []

    competitive.sort(
        key=lambda x: (int(x.get("total_openings") or 0), float(x.get("score") or 0)),
        reverse=True,
    )

    return end_clients, partners, competitive