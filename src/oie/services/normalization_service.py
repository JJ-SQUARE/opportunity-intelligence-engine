from __future__ import annotations

import re
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext


class NormalizationService:
    def __init__(self, ctx: RunContext) -> None:
        self.ctx = ctx

    def _as_text(self, job: Dict[str, Any]) -> str:
        parts = [
            str(job.get("title") or ""),
            str(job.get("job_title") or ""),
            str(job.get("company") or ""),
            str(job.get("location") or ""),
            str(job.get("description") or ""),
            str(job.get("via") or ""),
            str(job.get("url") or ""),
        ]

        source_meta = job.get("source_meta") or {}
        if isinstance(source_meta, dict):
            parts.extend(
                [
                    str(source_meta.get("query_name") or ""),
                    str(source_meta.get("query_text") or ""),
                    str(source_meta.get("search_location") or ""),
                    str(source_meta.get("serp_location_used") or ""),
                    str(source_meta.get("serp_query_used") or ""),
                ]
            )

        raw = job.get("raw") or {}
        if isinstance(raw, dict):
            extensions = raw.get("extensions") or []
            if isinstance(extensions, list):
                parts.extend(str(x) for x in extensions if x is not None)

            detected_extensions = raw.get("detected_extensions") or {}
            if isinstance(detected_extensions, dict):
                parts.extend(str(v) for v in detected_extensions.values() if v is not None)

        return " \n ".join(p for p in parts if p).lower()

    def _detect_remote(self, job: Dict[str, Any], text: str) -> bool:
        location = str(job.get("location") or "").strip().lower()

        remote_patterns = [
            r"\bremote\b",
            r"\bwork from home\b",
            r"\bhome office\b",
            r"\b100%\s*remote\b",
            r"\bfully remote\b",
            r"\bremoto\b",
            r"\btrabajo remoto\b",
            r"\btrabajo 100%\s*remoto\b",
            r"\ben casa\b",
            r"\bdesde casa\b",
            r"\banywhere\b",
            r"\bteletrabajo\b",
        ]

        if location in {"anywhere", "remote", "remoto"}:
            return True

        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in remote_patterns)

    def _detect_contractor(self, text: str) -> bool:
        contractor_patterns = [
            r"\bcontract\b",
            r"\bcontractor\b",
            r"\bcontract position\b",
            r"\bcontract role\b",
            r"\bfreelance\b",
            r"\bprestación de servicios\b",
            r"\bprestacion de servicios\b",
            r"\bpor honorarios\b",
            r"\bservices agreement\b",
            r"\btemporary\b",
            r"\btemp\b",
            r"\bconsultor\b",
            r"\bconsultant\b",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in contractor_patterns)

    def _detect_full_time(self, text: str) -> bool:
        full_time_patterns = [
            r"\bfull[-\s]?time\b",
            r"\btiempo completo\b",
            r"\bjornada completa\b",
            r"\bpermanent\b",
            r"\bpor tiempo indeterminado\b",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in full_time_patterns)

    def _detect_us_only(self, text: str) -> bool:
        us_only_patterns = [
            r"\bu\.?s\.?\s+only\b",
            r"\bus only\b",
            r"\bmust be based in the us\b",
            r"\bonly candidates in the united states\b",
            r"\bsolo estados unidos\b",
            r"\bsolo eeuu\b",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in us_only_patterns)

    def _detect_nearshore_friendly(self, text: str) -> bool:
        patterns = [
            r"\blatam\b",
            r"\blatin america\b",
            r"\bnearshore\b",
            r"\bremoto desde latam\b",
            r"\bremote from latam\b",
            r"\bméxico\b",
            r"\bmexico\b",
            r"\bcolombia\b",
            r"\becuador\b",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _detect_offshore_mentioned(self, text: str) -> bool:
        patterns = [
            r"\boffshore\b",
            r"\boff-shore\b",
            r"\bexternal vendor\b",
            r"\boutsourcing\b",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def _count_urgency_hits(self, text: str) -> int:
        patterns = [
            r"\burgent\b",
            r"\basap\b",
            r"\binmediate\b",
            r"\bimmediately\b",
            r"\burgente\b",
            r"\binmediato\b",
            r"\bcontratación inmediata\b",
            r"\bcontratacion inmediata\b",
        ]
        return sum(1 for pattern in patterns if re.search(pattern, text, flags=re.IGNORECASE))

    def _detect_many_openings_signal(self, text: str) -> bool:
        patterns = [
            r"\bmultiple openings\b",
            r"\bseveral openings\b",
            r"\bvarias vacantes\b",
            r"\bmany openings\b",
            r"\b\d+\s+openings\b",
            r"\b\d+\s+positions\b",
            r"\b\d+\s+vacantes\b",
            r"# of positions",
        ]
        return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)

    def normalize(self, jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []

        for job in jobs:
            record = dict(job)
            text = self._as_text(record)

            record["is_remote"] = self._detect_remote(record, text)
            record["is_contractor"] = self._detect_contractor(text)
            record["is_full_time"] = self._detect_full_time(text)
            record["nearshore_friendly"] = self._detect_nearshore_friendly(text)
            record["offshore_mentioned"] = self._detect_offshore_mentioned(text)
            record["us_only"] = self._detect_us_only(text)
            record["urgency_hits"] = self._count_urgency_hits(text)
            record["many_openings_signal"] = self._detect_many_openings_signal(text)

            normalized.append(record)

        self.ctx.metrics["jobs_after_normalize"] = len(normalized)
        self.ctx.metrics["normalize_completed"] = True
        return normalized
