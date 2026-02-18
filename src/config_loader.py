from typing import Any, Dict
import yaml


def load_config(path: str = "config/queries.yaml") -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)