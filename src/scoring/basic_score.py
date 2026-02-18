from typing import Dict, Any


def basic_opportunity_score(company_data: Dict[str, Any]) -> float:
    """
    Simple heuristic scoring:
    - More openings = higher urgency
    - Multiple different titles = expansion signal
    """

    score = 0.0

    total_openings = company_data.get("total_openings", 0)
    unique_titles = len(company_data.get("titles", []))

    # Volume signal
    score += min(total_openings * 2, 10)

    # Diversity signal
    score += unique_titles * 1.5

    return round(score, 2)