from __future__ import annotations

import importlib
import re
from typing import Any, Dict, List
from urllib.parse import unquote, urlparse

from oie.collectors.base import BaseJobCollector


PLACEHOLDER_COMPANIES = {
    "",
    "unknown",
    "confidential",
    "stealth",
    "undisclosed",
    "n/a",
    "na",
}

TITLE_COMPANY_PATTERNS = [
    re.compile(r"^(?P<company>.+?)\s+hiring\s+.+$", re.IGNORECASE),
    re.compile(r"^(?P<title>.+?)\s+at\s+(?P<company>.+)$", re.IGNORECASE),
    re.compile(r"^(?P<company>.+?)\s+is\s+hiring\s+.+$", re.IGNORECASE),
]


class LinkedInSerpAPICollector(BaseJobCollector):
    collector_name = "linkedin_serpapi"

    def _load_legacy_callable(self):
        function_candidates = [
            ("collectors.discovery.linkedin_serpapi", "collect_jobs"),
            ("collectors.discovery.linkedin", "collect_jobs"),
            ("collectors.linkedin_serpapi", "collect_jobs"),
        ]

        for module_name, function_name in function_candidates:
            try:
                module = importlib.import_module(module_name)
                fn = getattr(module, function_name, None)
                if callable(fn):
                    return ("function", fn)
            except Exception:
                continue

        class_candidates = [
            ("collectors.discovery.linkedin_serpapi", "LinkedInSerpApiCollector"),
        ]

        for module_name, class_name in class_candidates:
            try:
                module = importlib.import_module(module_name)
                cls = getattr(module, class_name, None)
                if cls is not None:
                    instance = cls()
                    collect_method = getattr(instance, "collect", None)
                    if callable(collect_method):
                        return ("method", collect_method)
            except Exception:
                continue

        return None

    def _load_legacy_collector(self):
        legacy_target = self._load_legacy_callable()
        if legacy_target is None:
            return None

        target_type, target = legacy_target
        if target_type == "method":
            return lambda payload: target(payload)
        return target

    def _clean_company_candidate(self, value: str) -> str:
        candidate = (value or "").strip()
        if not candidate:
            return ""

        candidate = re.sub(r"\s+", " ", candidate).strip(" -|,.;:")
        lowered = candidate.lower()

        if lowered in PLACEHOLDER_COMPANIES:
            return ""

        # Limpia ruido típico de títulos
        candidate = re.sub(r"\b(remote|remoto|latam|latin america)\b", "", candidate, flags=re.IGNORECASE)
        candidate = re.sub(r"\s+", " ", candidate).strip(" -|,.;:")

        lowered = candidate.lower()
        if lowered in PLACEHOLDER_COMPANIES:
            return ""

        if len(candidate) <= 4 and candidate.isalpha():
            return candidate.upper()

        return candidate

    def _company_from_title(self, title: str) -> str:
        value = (title or "").strip()
        if not value:
            return ""

        for pattern in TITLE_COMPANY_PATTERNS:
            match = pattern.match(value)
            if match:
                company = match.groupdict().get("company", "")
                cleaned = self._clean_company_candidate(company)
                if cleaned:
                    return cleaned

        return ""

    def _company_from_url(self, url: str) -> str:
        value = (url or "").strip()
        if not value:
            return ""

        try:
            parsed = urlparse(value)
            slug = unquote(parsed.path.rsplit("/", 1)[-1])
        except Exception:
            return ""

        if not slug:
            return ""

        match = re.search(r"-at-([a-z0-9\-]+?)(?:-\d+)?$", slug, flags=re.IGNORECASE)
        if not match:
            return ""

        raw_company = match.group(1).replace("-", " ").strip()
        cleaned = self._clean_company_candidate(raw_company)
        if not cleaned:
            return ""

        if len(cleaned) <= 4 and cleaned.replace(" ", "").isalpha():
            return cleaned.upper()

        return " ".join(part.capitalize() if len(part) > 3 else part.upper() for part in cleaned.split())

    def _best_company(self, raw_job: Dict[str, Any]) -> str:
        direct = self._clean_company_candidate(raw_job.get("company", ""))
        if direct:
            return direct

        from_title = self._company_from_title(raw_job.get("title", ""))
        if from_title:
            return from_title

        from_job_url = self._company_from_url(raw_job.get("job_url", "") or raw_job.get("url", ""))
        if from_job_url:
            return from_job_url

        return ""

    def _normalize_job(self, raw_job: Dict[str, Any]) -> Dict[str, Any]:
        company = self._best_company(raw_job)

        return {
            "title": raw_job.get("title", ""),
            "company": company,
            "location": raw_job.get("location", ""),
            "job_url": raw_job.get("job_url", "") or raw_job.get("url", ""),
            "apply_url": raw_job.get("apply_url", ""),
            "description": raw_job.get("description", ""),
            "source": self.collector_name,
            "detected_at": raw_job.get("detected_at", ""),
            "url": raw_job.get("url", ""),
            "source_meta": raw_job.get("source_meta", {}) or {},
            "raw": raw_job,
        }

    def collect(self) -> List[Dict[str, Any]]:
        legacy_collect_fn = self._load_legacy_collector()
        if legacy_collect_fn is None:
            return []

        queries = self.config.get("queries", []) or []
        run = self.config.get("run", {}) or {}
        source_config = self.config.get("source_config", {}) or {}

        payload = {
            "queries": queries,
            "run": run,
            "source_config": source_config,
            "collector_cfg": source_config,
        }

        try:
            raw_jobs = legacy_collect_fn(payload) or []
        except TypeError:
            try:
                raw_jobs = legacy_collect_fn(
                    queries=queries,
                    num_pages=run.get("num_pages", 3),
                    sleep_s=run.get("sleep_s", 1.0),
                    gl=source_config.get("gl", "us"),
                    hl=source_config.get("hl", "en"),
                ) or []
            except TypeError:
                raw_jobs = legacy_collect_fn() or []

        return [self._normalize_job(job) for job in raw_jobs]
