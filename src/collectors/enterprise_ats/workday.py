from __future__ import annotations
from typing import Any, Dict, List
from collectors.registry import register

@register
class WorkdayATSCollector:
    name = "workday_ats"
    source = "career_portal"
    family = "enterprise_ats"
    def collect(self, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        return []