from typing import Any, Dict, List
import pandas as pd


def export_leads_csv(leads: List[Dict[str, Any]], path: str) -> str:
    df = pd.DataFrame(leads)
    df.to_csv(path, index=False)
    return path