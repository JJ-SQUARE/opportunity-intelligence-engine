from __future__ import annotations

import json
from typing import Any, Dict, List

from oie.orchestration.run_context import RunContext
from oie.services.provider_control_service import ProviderControlService
from oie.services.provider_execution_service import (
    ProviderExecutionBlockedError,
    ProviderExecutionService,
)


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

        self.ai_enabled = bool(ctx.config.get("domain_ai_enabled", True)) if ctx.config else True
        self.max_calls = int(ctx.config.get("domain_ai_max_calls_per_run", 25)) if ctx.config else 25
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

        prompt = self._build_prompt(company_name, candidates)
        payload = {
            "company_name": company_name,
            "prompt": prompt,
            "candidates": candidates,
        }

        validate_fn = getattr(client, "validate_domain_candidates", None)
        complete_json_fn = getattr(client, "complete_json", None)

        exec_fn = None
        exec_arg = None

        if validate_fn is not None:
            exec_fn = validate_fn
            exec_arg = payload
        elif complete_json_fn is not None:
            exec_fn = complete_json_fn
            exec_arg = prompt
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
                exec_arg,
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

        except AttributeError as exc:
            if "get_circuit_breaker" not in str(exc):
                raise

            raw = exec_fn(exec_arg)
            self._used += 1
            self.ai_calls += 1
            self.ctx.metrics["domain_ai_validation_attempted"] = (
                    int(self.ctx.metrics.get("domain_ai_validation_attempted", 0)) + 1
            )
            self.ctx.metrics["domain_ai_calls"] = (
                    int(self.ctx.metrics.get("domain_ai_calls", 0)) + 1
            )
            parsed = self._parse_response(raw)

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

