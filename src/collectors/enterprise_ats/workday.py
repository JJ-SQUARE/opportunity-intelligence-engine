from typing import Any, Dict, List
from collectors.base import BaseCollector, JobPosting
from collectors.registry import register

@register
class WorkdayCollector(BaseCollector):
    name = "workday"
    family = "enterprise_ats"

    def fetch(self, cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
        # TODO: implementar
        return []