from __future__ import annotations

import json
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionService,
)
from oie.utils.domain_filters import is_job_board_domain, normalize_domain


class DomainAIValidationService:
    def __init__(
            self,
            ctx: RunContext,
            provider_control_service: ProviderControlService,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.provider_execution_service = ProviderExecutionService(ctx, provider_control_service)

        config = ctx.config.get("domain_resolution", {}) if ctx.config else {}
        self.validation_limit = int(config.get("domain_ai_validation_limit", 10))
        self._used = 0

        self.ai_enabled = bool(config.get("domain_ai_enabled", ctx.config.get("domain_ai_enabled", True) if ctx.config else True))
        self.max_calls = int(config.get("domain_ai_max_calls_per_run", ctx.config.get("domain_ai_max_calls_per_run", 25) if ctx.config else 25))
        self.max_candidates = int(config.get("domain_ai_max_candidates", 3))
        self.min_candidate_score = float(config.get("domain_ai_min_candidate_score", 0.20))
        self.ai_calls = 0

    def can_validate(self) -> bool:
        return self._used < self.validation_limit

    def _build_prompt(
        self,
        company_name: str,
        candidates: List[Dict[str, Any]],
    ) -> str:
        safe_candidates: List[Dict[str, Any]] = []
        for c in candidates:
            safe_candidates.append(
                {
                    "domain": c.get("domain"),
                    "source": c.get("source"),
                    "score": c.get("score"),
                    "title": c.get("title"),
                    "snippet": c.get("snippet"),
                    "serp_rank": c.get("serp_rank"),
                    "confidence_reasons": c.get("confidence_reasons", []),
                }
            )

        return (
            "You are validating the most likely official company website domain.\n"
            "Choose ONLY from the candidate domains provided.\n"
            "Reject if evidence is insufficient.\n"
            "Never choose job boards, aggregators, LinkedIn, recruiter portals, or unrelated brands.\n"
            "Return strict JSON with keys: selected_domain, decision, confidence, reason.\n"
            "decision must be one of: accepted, review, rejected.\n\n"
            f"company_name: {company_name}\n"
            f"candidates: {json.dumps(safe_candidates, ensure_ascii=False)}"
        )

    def _normalize_ai_result(self, raw_result: Any) -> Dict[str, Any]:
        if raw_result is None:
            return {}

        if isinstance(raw_result, dict):
            return raw_result

        if isinstance(raw_result, str):
            raw_text = raw_result.strip()
            if not raw_text:
                return {}
            try:
                return json.loads(raw_text)
            except Exception:
                return {}

        try:
            return dict(raw_result)
        except Exception:
            return {}

    def _parse_response(self, raw: Any) -> Dict[str, Any]:
        data = self._normalize_ai_result(raw)

        selected_domain = data.get("selected_domain")
        decision = data.get("decision", "rejected")
        confidence = float(data.get("confidence", 0.0) or 0.0)
        reason = str(data.get("reason", "")).strip()

        if decision not in {"accepted", "review", "rejected"}:
            decision = "rejected"

        if selected_domain == "":
            selected_domain = None

        return {
            "selected_domain": selected_domain,
            "decision": decision,
            "confidence": max(0.0, min(confidence, 1.0)),
            "reason": reason,
        }


    def _candidate_domains(self, candidates: List[Dict[str, Any]]) -> set[str]:
        return {
            normalize_domain(candidate.get("domain") or "")
            for candidate in candidates
            if normalize_domain(candidate.get("domain") or "")
        }

    def _candidate_sort_key(self, candidate: Dict[str, Any]) -> tuple:
        reasons = set(candidate.get("confidence_reasons") or [])
        score = float(candidate.get("score", 0.0) or 0.0)
        serp_rank = candidate.get("serp_rank")
        normalized_rank = serp_rank if isinstance(serp_rank, int) and serp_rank > 0 else 999
        title = str(candidate.get("title") or "").strip()
        snippet = str(candidate.get("snippet") or "").strip()

        signal_strength = sum(
            1
            for key in (
                "full_join_match",
                "core_join_match",
                "primary_token_match",
                "core_hits_1",
                "core_hits_2plus",
                "text_core_hits_1",
                "text_core_hits_2plus",
            )
            if key in reasons
        )

        return (
            score,
            signal_strength,
            1 if title else 0,
            1 if snippet else 0,
            -normalized_rank,
        )

    def _is_candidate_ai_eligible(self, candidate: Dict[str, Any]) -> bool:
        domain = normalize_domain(candidate.get("domain") or "")
        source = str(candidate.get("source") or "").strip().lower()
        title = str(candidate.get("title") or "").strip()
        snippet = str(candidate.get("snippet") or "").strip()
        reasons = set(candidate.get("confidence_reasons") or [])
        raw_score = candidate.get("score", None)
        text = f"{title} {snippet}".strip().lower()

        if not domain:
            return False

        if is_job_board_domain(domain):
            return False

        # No exigir score cuando el candidato viene solo con señales/rationale
        # ya que varios tests y caminos reales mandan candidates sin score hidratado.
        if raw_score is not None:
            score = float(raw_score or 0.0)
            if score < self.min_candidate_score:
                return False

        if source in {"apply_url", "url"} and not (title or snippet):
            return False

        if not (title or snippet or reasons):
            return False

        has_brand_signal = bool(
            "full_join_match" in reasons
            or "core_join_match" in reasons
            or "primary_token_match" in reasons
            or "core_hits_1" in reasons
            or "core_hits_2plus" in reasons
            or "text_core_hits_1" in reasons
            or "text_core_hits_2plus" in reasons
            or candidate.get("confidence_brand_match", False)
        )

        has_official_context = bool(
            text
            and (
                "official" in text
                or "official site" in text
                or "official website" in text
                or "sitio oficial" in text
                or "company" in text
            )
        )

        if not has_brand_signal and not has_official_context:
            return False

        return True

    def _prefilter_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = [
            dict(candidate)
            for candidate in candidates
            if self._is_candidate_ai_eligible(candidate)
        ]
        filtered.sort(key=self._candidate_sort_key, reverse=True)
        return filtered[: max(1, self.max_candidates)]

    def _enforce_candidate_whitelist(
        self,
        parsed: Dict[str, Any],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        selected_domain = normalize_domain(parsed.get("selected_domain") or "")
        allowed_domains = self._candidate_domains(candidates)

        if selected_domain and selected_domain not in allowed_domains:
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "selected_domain_not_in_candidates",
            }

        if selected_domain and is_job_board_domain(selected_domain):
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "selected_domain_blocked",
            }

        normalized = dict(parsed)
        normalized["selected_domain"] = selected_domain or None
        return normalized

    def validate(
        self,
        company_name: str,
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not candidates:
            self.ctx.metrics["domain_ai_validation_skipped_no_candidates"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_no_candidates", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "no_candidates",
            }

        if not self.ai_enabled:
            self.ctx.metrics["domain_ai_validation_skipped_disabled"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_disabled", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "ai_disabled",
            }

        if self.ai_calls >= self.max_calls:
            self.ctx.metrics["domain_ai_budget_exhausted"] = (
                int(self.ctx.metrics.get("domain_ai_budget_exhausted", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "ai_budget_exhausted",
            }

        if not self.can_validate():
            self.ctx.metrics["domain_ai_validation_skipped_limit"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_limit", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "validation_limit_reached",
            }

        client = self.provider_control_service.registry.get_client("openai")
        if client is None:
            self.ctx.metrics["domain_ai_validation_skipped_no_client"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_no_client", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "missing_openai_client",
            }

        filtered_candidates = self._prefilter_candidates(candidates)
        if not filtered_candidates:
            self.ctx.metrics["domain_ai_validation_skipped_prefilter"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_prefilter", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "prefilter_rejected_candidates",
            }

        prompt = self._build_prompt(company_name, filtered_candidates)
        payload = {
            "company_name": company_name,
            "prompt": prompt,
            "candidates": filtered_candidates,
        }

        validate_fn = getattr(client, "validate_domain_candidates", None)
        complete_json_fn = getattr(client, "complete_json", None)

        exec_fn = None
        exec_args = ()
        fallback_call = None

        if validate_fn is not None:
            exec_fn = validate_fn
            exec_args = (payload,)
            fallback_call = lambda: validate_fn(payload)
        elif complete_json_fn is not None:
            exec_fn = complete_json_fn
            exec_args = (prompt,)
            fallback_call = lambda: complete_json_fn(prompt)
        else:
            self.ctx.metrics["domain_ai_validation_skipped_no_supported_method"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_no_supported_method", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "missing_supported_openai_method",
            }

        try:
            raw = self.provider_execution_service.execute(
                "openai",
                "domain_ai_validation",
                exec_fn,
                *exec_args,
                cost=1,
            )
            self._used += 1
            self.ai_calls += 1
            self.ctx.metrics["domain_ai_validation_attempted"] = (
                int(self.ctx.metrics.get("domain_ai_validation_attempted", 0)) + 1
            )
            self.ctx.metrics["domain_ai_calls"] = (
                int(self.ctx.metrics.get("domain_ai_calls", 0)) + 1
            )
            parsed = self._parse_response(raw)
            parsed = self._enforce_candidate_whitelist(parsed, filtered_candidates)

        except AttributeError as exc:
            if "get_circuit_breaker" not in str(exc):
                raise

            raw = fallback_call()
            self._used += 1
            self.ai_calls += 1
            self.ctx.metrics["domain_ai_validation_attempted"] = (
                int(self.ctx.metrics.get("domain_ai_validation_attempted", 0)) + 1
            )
            self.ctx.metrics["domain_ai_calls"] = (
                int(self.ctx.metrics.get("domain_ai_calls", 0)) + 1
            )
            parsed = self._parse_response(raw)
            parsed = self._enforce_candidate_whitelist(parsed, filtered_candidates)

        except ProviderExecutionBlockedError:
            self.ctx.metrics["domain_ai_validation_skipped_blocked"] = (
                int(self.ctx.metrics.get("domain_ai_validation_skipped_blocked", 0)) + 1
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "provider_blocked",
            }

        except Exception as exc:
            self.ctx.metrics["domain_ai_validation_errors"] = (
                int(self.ctx.metrics.get("domain_ai_validation_errors", 0)) + 1
            )
            self.ctx.add_provider_event(
                provider="openai",
                event_type="domain_ai_validation_error",
                message="domain_ai_validation_failed",
                metadata={
                    "company_name": company_name,
                    "error": repr(exc),
                },
            )
            return {
                "selected_domain": None,
                "decision": "review",
                "confidence": 0.0,
                "reason": "validation_error",
            }

        metric_key = f"domain_ai_validation_{parsed['decision']}"
        self.ctx.metrics[metric_key] = int(self.ctx.metrics.get(metric_key, 0)) + 1

        decision_metric_key = f"domain_ai_decision_{parsed['decision']}"
        self.ctx.metrics[decision_metric_key] = (
            int(self.ctx.metrics.get(decision_metric_key, 0)) + 1
        )

        self.ctx.add_provider_event(
            provider="openai",
            event_type="domain_ai_validation_decision",
            message="domain_ai_validation_completed",
            metadata={
                "company_name": company_name,
                "selected_domain": parsed["selected_domain"],
                "decision": parsed["decision"],
                "confidence": parsed["confidence"],
                "reason": parsed["reason"],
            },
        )

        return parsed

