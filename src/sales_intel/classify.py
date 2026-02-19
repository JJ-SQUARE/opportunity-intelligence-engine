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
    Returns: (end_clients, partners, competitive)
    - end_clients: targets directos (product companies)
    - partners: consultoras / staffing con fit alto (también pueden ser clientes)
    - competitive: watchlist (competencia / players a vigilar)
    """

    sales_cfg = cfg.get("sales", {})
    comp_cfg = cfg.get("competitive", {})
    seg_cfg = cfg.get("segmentation", {})  # <--- nuevo en YAML

    # thresholds
    high_min = float(sales_cfg.get("high_min_score", 14))
    med_min = float(sales_cfg.get("medium_min_score", 11))
    vendor_min = float(sales_cfg.get("vendor_prob_min", 70))
    require_not_us_only = bool(sales_cfg.get("require_not_us_only", True))
    max_medium = int(sales_cfg.get("max_medium", 25))

    # segmentation config
    mode = (seg_cfg.get("mode", "split") or "split").lower()  # split | include_all | exclude
    end_client_types = set(seg_cfg.get("end_client_types", ["product_company", "marketplace"]))
    partner_types = set(seg_cfg.get("partner_types", ["consulting", "staffing_agency"]))

    allow_unknown_end_clients = bool(seg_cfg.get("allow_unknown_end_clients", True))
    unknown_min_score = float(seg_cfg.get("unknown_min_score", 16))
    unknown_min_vendor_prob = float(seg_cfg.get("unknown_min_vendor_prob", 70))

    # sales exclude types (optional legacy behavior)
    exclude_types = set(sales_cfg.get("exclude_company_types", []))

    # Competitive watchlist config
    comp_enabled = bool(comp_cfg.get("enabled", True))
    comp_types = set(comp_cfg.get("include_company_types", ["staffing_agency"]))
    comp_min_openings = int(comp_cfg.get("min_openings", 2))

    end_candidates: List[Dict[str, Any]] = []
    partner_candidates: List[Dict[str, Any]] = []
    competitive: List[Dict[str, Any]] = []

    for c in companies:
        score = float(c.get("score") or 0)
        company_type = (c.get("company_type_ai") or "unknown").strip().lower()
        vendor_prob = float(c.get("vendor_acceptance_probability_ai") or 0)
        us_only = bool(c.get("us_only_signal"))
        openings = int(c.get("total_openings") or 0)

        # ---- Competitive watchlist ----
        if comp_enabled and company_type in comp_types and openings >= comp_min_openings:
            cc = dict(c)
            cc["priority_band"] = classify_priority(score, high_min, med_min)
            cc["segment"] = "competitive"
            competitive.append(cc)

        # ---- Global sales eligibility (aplica a end y partners) ----
        if company_type in exclude_types:
            continue
        if require_not_us_only and us_only:
            continue
        if vendor_prob < vendor_min:
            continue

        sc = dict(c)
        sc["priority_band"] = classify_priority(score, high_min, med_min)

        # ---- Segmentation rules ----
        is_end_client = company_type in end_client_types
        is_partner = company_type in partner_types

        is_unknown_end = (
            allow_unknown_end_clients
            and company_type == "unknown"
            and score >= unknown_min_score
            and vendor_prob >= unknown_min_vendor_prob
        )

        if mode == "exclude":
            # solo end clients
            if is_end_client or is_unknown_end:
                sc["segment"] = "end_client"
                end_candidates.append(sc)
            continue

        if mode == "include_all":
            # todo a un solo bucket (end_candidates), pero marcamos segmento
            if is_end_client or is_unknown_end:
                sc["segment"] = "end_client"
            elif is_partner:
                sc["segment"] = "partner"
            else:
                sc["segment"] = "other"
            end_candidates.append(sc)
            continue

        # default: split
        if is_end_client or is_unknown_end:
            sc["segment"] = "end_client"
            end_candidates.append(sc)
        elif is_partner:
            sc["segment"] = "partner"
            partner_candidates.append(sc)
        else:
            # no es end client ni partner -> lo ignoramos (o podrías mandarlo a competitive si quieres)
            continue

    def finalize(candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        candidates.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
        high = [x for x in candidates if x["priority_band"] == "HIGH"]
        medium = [x for x in candidates if x["priority_band"] == "MEDIUM"][:max_medium]
        final = high + medium
        final.sort(key=lambda x: float(x.get("score") or 0), reverse=True)
        return final

    end_clients = finalize(end_candidates)

    # partners: misma regla (HIGH + top MEDIUM) pero puedes darle otro max si quieres
    partners = finalize(partner_candidates) if mode == "split" else []

    # Competitive ordenado por openings desc y score desc
    competitive.sort(
        key=lambda x: (int(x.get("total_openings") or 0), float(x.get("score") or 0)),
        reverse=True,
    )

    return end_clients, partners, competitive