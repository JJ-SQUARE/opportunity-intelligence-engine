from typing import Any, Dict, List
import pandas as pd


def export_jobs_csv(jobs: List[Dict[str, Any]], path: str) -> str:
    df = pd.DataFrame(jobs)
    df.to_csv(path, index=False)
    return path