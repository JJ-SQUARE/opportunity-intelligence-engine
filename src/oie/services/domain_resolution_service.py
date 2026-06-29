from __future__ import annotations

from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from oie.orchestration.run_context import RunContext
from oie.services.domain_confidence_service import DomainConfidenceService
from oie.services.provider_control_service import ProviderControlService
from oie.services.serpapi_search_service import SerpAPISearchService
from oie.services.provider_execution_service import ProviderExecutionError
from oie.utils.domain_filters import is_job_board_domain, normalize_domain
from oie.utils.company_identity_utils import is_actionable_company_name
from oie.services.domain_ai_validation_service import DomainAIValidationService
from oie.utils.company_name_extraction import extract_actionable_company_name


PLACEHOLDER_COMPANY_VALUES = {
    "",
    "unknown",
    "confidential",
    "stealth",
    "undisclosed",
    "n/a",
    "na",
}

BLOCKED_DOMAINS = {
    "linkedin.com",
    "www.linkedin.com",
    "lnkd.in",
    "indeed.com",
    "www.indeed.com",
    "glassdoor.com",
    "www.glassdoor.com",
    "ziprecruiter.com",
    "www.ziprecruiter.com",
    "greenhouse.io",
    "boards.greenhouse.io",
    "lever.co",
    "jobs.lever.co",
    "workable.com",
    "apply.workable.com",
    "teamtailor.com",
    "jobs.teamtailor.com",
    "breezy.hr",
    "app.breezy.hr",
    "jobgether.com",
    "www.jobgether.com",
    "multitrabajos.com",
    "www.multitrabajos.com",
    "vacantesdigitales.com",
    "www.vacantesdigitales.com",
    "computrabajo.com",
    "www.computrabajo.com",
    "talenteca.com",
    "www.talenteca.com",
    "grabjobs.co",
    "www.grabjobs.co",
    "jobleads.com",
    "www.jobleads.com",
    "dailyremote.com",
    "www.dailyremote.com",
    "lensa.com",
    "www.lensa.com",
    "bebee.com",
    "www.bebee.com",
    "builtinchicago.org",
    "www.builtinchicago.org",
    "oficinaempleo.com",
    "www.oficinaempleo.com",
    "quierolaburo.com",
    "www.quierolaburo.com",
    "t.co",
    "bit.ly",
    "goo.gl",
    "google.com",
    "www.google.com",
}


class DomainResolutionService:
    def __init__(
        self,
        ctx: RunContext,
        provider_control_service: Optional[ProviderControlService] = None,
        serpapi_search_service: Optional[SerpAPISearchService] = None,
        domain_ai_validation_service: Optional[DomainAIValidationService] = None,
    ) -> None:
        self.ctx = ctx
        self.provider_control_service = provider_control_service
        self.serpapi_search_service = serpapi_search_service
        self.domain_ai_validation_service = domain_ai_validation_service

        config = ctx.config.get("domain_resolution", {}) if ctx.config else {}
        self.serpapi_fallback_limit = int(config.get("serpapi_fallback_limit", 25))
        self.review_threshold = float(config.get("review_threshold", 0.45))
        self.auto_accept_threshold = float(config.get("auto_accept_threshold", 0.80))
        self.ai_min_score_for_review = float(config.get("ai_min_score_for_review", self.review_threshold))
        self.ai_max_score_for_review = float(config.get("ai_max_score_for_review", 0.75))
        self._serpapi_fallback_count = 0

        self.confidence_service = DomainConfidenceService(
            auto_accept_threshold=self.auto_accept_threshold,
            review_threshold=self.review_threshold,
        )

    def _extract_domain(self, url: Optional[str]) -> Optional[str]:
        if not url:
            return None

        value = url.strip()
        if not value:
            return None

        if "://" not in value:
            value = f"https://{value}"

        try:
            parsed = urlparse(value)
            domain = normalize_domain(parsed.netloc or "")
            return domain or None
        except Exception:
            return None

    def _is_blocked_domain(self, domain: Optional[str]) -> bool:
        if not domain:
            return True
        if domain in BLOCKED_DOMAINS:
            return True
        if is_job_board_domain(domain):
            return True
        return False

    def _should_skip_generic_name(self, company_name: Optional[str]) -> bool:
        return self.confidence_service.is_generic_company_name(company_name)

    def _should_preserve_direct_aggregator_review(self, candidate: Dict[str, Any]) -> bool:
        domain = str(candidate.get("domain") or "").strip().lower()
        source = str(candidate.get("source") or "").strip().lower()

        if source not in {"apply_url", "url"}:
            return False

        # Preservamos review solo para wrappers/portales genéricos
        # que no representan una marca de empresa real.
        preservable_domains = {
            "google.com",
            "www.google.com",
            "linkedin.com",
            "www.linkedin.com",
            "lnkd.in",
            "indeed.com",
            "www.indeed.com",
            "glassdoor.com",
            "www.glassdoor.com",
            "ziprecruiter.com",
            "www.ziprecruiter.com",
        }
        return domain in preservable_domains

    def _can_attempt_domain_resolution(self, company_name: Optional[str]) -> bool:
        value = (company_name or "").strip().lower()
        if value in PLACEHOLDER_COMPANY_VALUES:
            return False
        return is_actionable_company_name(company_name)

    def _resolve_effective_company_name(self, company: Dict[str, Any]) -> Optional[str]:
        candidate = extract_actionable_company_name(
            company_display=company.get("company_display") or company.get("company"),
            title=company.get("title"),
            snippet=company.get("snippet") or company.get("description"),
            apply_url=company.get("apply_url"),
        )
        value = (candidate or "").strip().lower()
        if value in PLACEHOLDER_COMPANY_VALUES:
            return None
        return candidate

    def _is_suspicious_subdomain_candidate(self, candidate: Dict[str, Any]) -> bool:
        domain = str(candidate.get("domain") or "").strip().lower()
        if not domain:
            return False

        suspicious_subdomain_markers = (
            "beta.",
            "staging.",
            "stage.",
            "dev.",
            "test.",
            "qa.",
            "sandbox.",
            "preview.",
            "demo.",
            "internal.",
        )
        return any(domain.startswith(marker) for marker in suspicious_subdomain_markers)

    def _should_send_candidate_to_ai(
        self,
        company_name: Optional[str],
        candidate: Dict[str, Any],
        validation_status: str,
        score: float,
    ) -> bool:
        if validation_status not in {"review", "rejected"}:
            return False

        if not self._can_attempt_domain_resolution(company_name):
            return False

        domain = candidate.get("domain")
        if not domain:
            return False

        source = candidate.get("source")
        is_aggregator = self._is_aggregator_candidate(candidate)

        # No gastar AI en agregadores directos de apply/url
        if is_aggregator and source in {"apply_url", "url"}:
            return False

        if self.domain_ai_validation_service is None:
            return False

        # Camino normal: review en zona gris útil.
        # Excepción: subdominios sospechosos tipo beta/staging/dev/qa pueden venir
        # con score alto por match de marca, pero igual queremos validarlos con AI.
        if validation_status == "review":
            if score < self.ai_min_score_for_review:
                return False

            is_suspicious_subdomain = self._is_suspicious_subdomain_candidate(candidate)

            if score > self.ai_max_score_for_review and not is_suspicious_subdomain:
                return False

            reasons = set(candidate.get("confidence_reasons") or [])
            title = str(candidate.get("title") or "").strip()
            snippet = str(candidate.get("snippet") or "").strip()
            has_context = bool(title or snippet)

            # Para subdominios sospechosos dejamos pasar la validación AI aunque
            # no venga contexto adicional, porque justamente queremos que AI
            # arbitre estos casos de alto score pero potencialmente contaminados.
            if is_suspicious_subdomain:
                return True

            if not has_context:
                return False

            has_signal = bool(
                candidate.get("confidence_brand_match", False)
                or "text_core_hits_1" in reasons
                or "text_core_hits_2plus" in reasons
                or "core_hits_1" in reasons
                or "core_hits_2plus" in reasons
                or "primary_token_match" in reasons
                or "full_join_match" in reasons
                or "core_join_match" in reasons
                or source == "serpapi_fallback"
            )

            return has_signal

        # Camino extendido: rechazados SERPAPI con señales mínimas de marca/contexto.
        # Esto abre una segunda oportunidad a falsos negativos tipo marca↔dominio no triviales,
        # sin mandar todo a OpenAI.
        if source != "serpapi_fallback":
            return False

        if is_aggregator:
            return False

        serp_rank = candidate.get("serp_rank")
        if isinstance(serp_rank, int) and serp_rank > 3:
            return False

        if score < 0.20 or score > 0.75:
            return False

        title = str(candidate.get("title") or "").strip()
        snippet = str(candidate.get("snippet") or "").strip()
        if not (title or snippet):
            return False

        brand_match = bool(candidate.get("confidence_brand_match", False))
        reasons = set(candidate.get("confidence_reasons") or [])
        has_soft_signal = bool(
            brand_match
            or "token_hits_1" in reasons
            or "text_core_hits_1" in reasons
            or "text_core_hits_2plus" in reasons
            or "primary_token_match" in reasons
            or "core_hits_1" in reasons
            or "core_hits_2plus" in reasons
        )

        return has_soft_signal

    def _is_aggregator_candidate(self, candidate: Dict[str, Any]) -> bool:
        domain = candidate.get("domain")
        return self._is_blocked_domain(domain)

    def _build_direct_candidates(self, company: Dict[str, Any]) -> List[Dict[str, Any]]:
        candidates: List[Dict[str, Any]] = []

        ai_domain_guess = self._extract_domain(company.get("ai_company_gate_domain_guess"))
        if ai_domain_guess and not self._is_blocked_domain(ai_domain_guess):
            candidates.append(
                {
                    "domain": ai_domain_guess,
                    "source": "ai_company_gate_domain_guess",
                    "serp_rank": None,
                    "title": str(company.get("company_display") or company.get("company") or ""),
                    "snippet": str(company.get("description") or ""),
                    "is_aggregator": False,
                }
            )

        for source_field, url in [
            ("apply_url", company.get("apply_url")),
            ("url", company.get("url")),
        ]:
            domain = self._extract_domain(url)
            if not domain:
                continue

            candidates.append(
                {
                    "domain": domain,
                    "source": source_field,
                    "serp_rank": None,
                    "title": "",
                    "snippet": "",
                    "is_aggregator": self._is_blocked_domain(domain),
                }
            )

        return candidates

    def _classify_resolution_priority(self, company: Dict[str, Any]) -> int:
        company_name = self._resolve_effective_company_name(company)
        raw_company_name = company.get("company_display") or company.get("company") or ""

        apply_domain = self._extract_domain(company.get("apply_url"))
        url_domain = self._extract_domain(company.get("url"))

        apply_blocked = bool(apply_domain and self._is_blocked_domain(apply_domain))
        url_blocked = bool(url_domain and self._is_blocked_domain(url_domain))

        has_blocked_direct_source = apply_blocked or url_blocked
        has_actionable_name = bool(company_name and self._can_attempt_domain_resolution(company_name))
        raw_name_actionable = self._can_attempt_domain_resolution(raw_company_name)

        # Prioridad 0:
        # Casos de mayor valor: agregador/job-board con nombre de empresa accionable
        # (incluye nombres extraídos desde title/snippet/apply_url como "Tenaris")
        if has_blocked_direct_source and has_actionable_name:
            return 0

        # Prioridad 1:
        # Empresa accionable sin dominio directo útil, pero con posibilidad de resolver por SerpAPI
        if has_actionable_name and not (apply_domain or url_domain):
            return 1

        # Prioridad 2:
        # Nombre visible accionable, aunque no sea caso crítico de agregador
        if raw_name_actionable:
            return 2

        # Prioridad 3:
        # Confidencial / no accionable / ruido
        return 3


    def _resolve_domain_via_serpapi(self, company_name: Optional[str]) -> List[Dict[str, Any]]:
        if not company_name:
            return []

        if self._serpapi_fallback_count >= self.serpapi_fallback_limit:
            self.ctx.metrics["serpapi_domain_resolution_skipped_limit"] = True
            return []

        if self._should_skip_generic_name(company_name):
            self.ctx.metrics["serpapi_domain_resolution_skipped_generic_name"] = (
                int(self.ctx.metrics.get("serpapi_domain_resolution_skipped_generic_name", 0)) + 1
            )
            return []

        service = self.serpapi_search_service
        if service is None and self.provider_control_service is not None:
            service = SerpAPISearchService(self.ctx, self.provider_control_service)

        if service is None:
            self.ctx.metrics["serpapi_domain_resolution_skipped_no_service"] = True
            return []

        queries = [
            f"{company_name} official website",
            f"{company_name} company",
        ]

        candidates: List[Dict[str, Any]] = []
        seen_domains = set()

        def _has_accepted_candidate(rows: List[Dict[str, Any]]) -> bool:
            if not rows:
                return False
            best = self.confidence_service.pick_best_candidate(company_name, rows)
            return bool(best and best.get("validation_status") == "accepted")

        for query_index, query in enumerate(queries):
            if self._serpapi_fallback_count >= self.serpapi_fallback_limit:
                self.ctx.metrics["serpapi_domain_resolution_skipped_limit"] = True
                break

            try:
                payload = service.search_google(query, num=5) or {}
                self._serpapi_fallback_count += 1
            except ProviderExecutionError as exc:
                self.ctx.metrics["serpapi_domain_resolution_provider_errors"] = (
                    int(self.ctx.metrics.get("serpapi_domain_resolution_provider_errors", 0)) + 1
                )
                self.ctx.add_provider_event(
                    provider="serpapi",
                    event_type="domain_resolution_search_failed",
                    message="serpapi_domain_resolution_failed",
                    metadata={
                        "company_name": company_name,
                        "query": query,
                        "error": repr(exc),
                    },
                )
                continue

            organic_results = payload.get("organic_results") or []
            query_candidates: List[Dict[str, Any]] = []

            for idx, item in enumerate(organic_results, start=1):
                link = item.get("link") or ""
                domain = self._extract_domain(link)
                if not domain:
                    continue

                normalized = domain.strip().lower()
                if normalized in seen_domains:
                    continue
                seen_domains.add(normalized)

                candidate = {
                    "domain": domain,
                    "source": "serpapi_fallback",
                    "serp_rank": idx,
                    "title": item.get("title") or "",
                    "snippet": item.get("snippet") or "",
                }
                query_candidates.append(candidate)
                candidates.append(candidate)

            # Solo intentar la segunda query si la primera no dejó un candidato aceptable.
            if query_index == 0 and _has_accepted_candidate(query_candidates):
                break

        return candidates

    def _empty_outcome(self) -> Dict[str, Any]:
        return {
            "domain": None,
            "source": None,
            "score": 0.0,
            "candidate": None,
            "validation_status": "rejected",
            "review_required": False,
            "ai_validated": 0,
            "ai_decision": None,
            "ai_confidence": None,
            "ai_reason": None,
        }

    def _evaluate_best_candidate(
        self,
        company_name: Optional[str],
        candidates: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not candidates:
            return self._empty_outcome()

        pre_scored_single_candidate = (
            len(candidates) == 1
            and any(
                key in candidates[0]
                for key in (
                    "score",
                    "validation_status",
                    "review_required",
                    "confidence_blocked",
                )
            )
        )

        if pre_scored_single_candidate:
            best = dict(candidates[0])
        else:
            best = self.confidence_service.pick_best_candidate(company_name, candidates)

        if not best:
            return self._empty_outcome()

        domain = best.get("domain")
        source = best.get("source")
        score = float(best.get("score", 0.0) or 0.0)
        blocked = bool(best.get("confidence_blocked", False))
        validation_status = best.get("validation_status", "rejected")
        review_required = bool(best.get("review_required", validation_status == "review"))
        is_aggregator = self._is_aggregator_candidate(best)

        # Si el mejor candidato directo viene de un agregador/job board,
        # nunca lo aceptamos como dominio final de la empresa.
        # Solo preservamos review para wrappers genéricos tipo Google/LinkedIn;
        # job boards concretos deben quedar rechazados para que no tapen mejores candidatos.
        #
        # Ojo: estos candidatos suelen venir marcados como blocked por DomainConfidenceService,
        # así que esta rama debe ejecutarse ANTES del rechazo general por blocked.
        if is_aggregator and self._should_preserve_direct_aggregator_review(best):
            return {
                "domain": None,
                "source": source,
                "score": score,
                "candidate": domain,
                "validation_status": "review",
                "review_required": True,
                "ai_validated": 0,
                "ai_decision": None,
                "ai_confidence": None,
                "ai_reason": "direct_aggregator_candidate",
            }

        if blocked:
            if (
                not is_aggregator
                and source == "serpapi_fallback"
                and self.domain_ai_validation_service is not None
                and self._can_attempt_domain_resolution(company_name)
            ):
                ai_result = self.domain_ai_validation_service.validate(company_name or "", [best])
                if (
                    ai_result.get("decision") == "accepted"
                    and ai_result.get("selected_domain") == domain
                ):
                    return {
                        "domain": domain,
                        "source": source,
                        "score": max(score, float(ai_result.get("confidence", score) or score)),
                        "candidate": domain,
                        "validation_status": "accepted",
                        "review_required": False,
                        "ai_validated": 1,
                        "ai_decision": ai_result.get("decision"),
                        "ai_confidence": ai_result.get("confidence"),
                        "ai_reason": ai_result.get("reason"),
                    }

            rejected_status = "rejected"
            return {
                "domain": None,
                "source": source,
                "score": 0.0,
                "candidate": domain,
                "validation_status": rejected_status,
                "review_required": False,
                "ai_validated": 0,
                "ai_decision": None,
                "ai_confidence": None,
                "ai_reason": "aggregator_or_job_board_domain" if is_aggregator else None,
            }

        ai_validated = 0
        ai_decision = None
        ai_confidence = None
        ai_reason = None

        if self._should_send_candidate_to_ai(
            company_name,
            best,
            validation_status,
            score,
        ):
            ai_result = self.domain_ai_validation_service.validate(
                company_name or "",
                [best],
            )
            ai_validated = 1
            ai_decision = ai_result.get("decision")
            ai_confidence = ai_result.get("confidence")
            ai_reason = ai_result.get("reason")

            if (
                ai_result.get("decision") == "accepted"
                and ai_result.get("selected_domain") == domain
            ):
                validation_status = "accepted"
                review_required = False
                score = max(score, float(ai_result.get("confidence", score)))

        return {
            "domain": domain if validation_status in {"accepted", "accepted_ai_validated"} else None,
            "source": source,
            "score": score,
            "candidate": domain,
            "validation_status": validation_status,
            "review_required": review_required,
            "ai_validated": ai_validated,
            "ai_decision": ai_decision,
            "ai_confidence": ai_confidence,
            "ai_reason": ai_reason,
        }

    def _resolve_company_domain(self, company: Dict[str, Any]) -> Dict[str, Any]:
        company_name = self._resolve_effective_company_name(company)

        if not self._can_attempt_domain_resolution(company_name):
            self.ctx.metrics["domain_resolution_skipped_non_actionable_company_name"] = (
                int(self.ctx.metrics.get("domain_resolution_skipped_non_actionable_company_name", 0)) + 1
            )
            return self._empty_outcome()

        direct_candidates = self._build_direct_candidates(company)
        best_direct = self._evaluate_best_candidate(company_name, direct_candidates)

        # Si el directo ya quedó aceptado con dominio válido, lo usamos.
        if best_direct["validation_status"] in {"accepted", "accepted_ai_validated"}:
            return best_direct

        # Si el directo es review (por ejemplo, apply_url de agregador),
        # intentamos resolver el dominio real vía SerpAPI.
        serp_candidates = self._resolve_domain_via_serpapi(company_name)
        best_serp = self._evaluate_best_candidate(company_name, serp_candidates)

        if best_serp["validation_status"] in {"accepted", "accepted_ai_validated"}:
            return best_serp

        if best_serp["candidate"]:
            if best_serp["validation_status"] == "rejected":
                self.ctx.metrics["serpapi_domain_resolution_rejected_low_confidence"] = (
                    int(self.ctx.metrics.get("serpapi_domain_resolution_rejected_low_confidence", 0)) + 1
                )
            if best_direct["validation_status"] == "review" and best_serp["validation_status"] == "rejected":
                self.ctx.metrics["domain_resolution_preserved_direct_review"] = (
                    int(self.ctx.metrics.get("domain_resolution_preserved_direct_review", 0)) + 1
                )
                return best_direct
            return best_serp

        if best_direct["validation_status"] == "review":
            self.ctx.metrics["domain_resolution_preserved_direct_review"] = (
                int(self.ctx.metrics.get("domain_resolution_preserved_direct_review", 0)) + 1
            )
            return best_direct

        if best_direct["candidate"]:
            return best_direct

        return self._empty_outcome()

    def resolve_domains(self, companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        resolved: List[Dict[str, Any]] = []
        resolved_count = 0
        accepted_count = 0
        review_count = 0
        rejected_count = 0

        indexed_companies = list(enumerate(companies))

        urgent: List[tuple[int, Dict[str, Any]]] = []
        medium: List[tuple[int, Dict[str, Any]]] = []
        normal: List[tuple[int, Dict[str, Any]]] = []

        for item in indexed_companies:
            priority = self._classify_resolution_priority(item[1])
            if priority == 0:
                urgent.append(item)
            elif priority == 1:
                medium.append(item)
            else:
                normal.append(item)

        ordered_results: Dict[int, Dict[str, Any]] = {}

        for bucket in (urgent, medium, normal):
            for idx, company in bucket:
                outcome = self._resolve_company_domain(company)

                domain = outcome.get("domain")
                source_field = outcome.get("source")
                confidence = float(outcome.get("score", 0.0))
                candidate = outcome.get("candidate")
                validation_status = outcome.get("validation_status", "rejected")
                review_required = bool(outcome.get("review_required", False))
                ai_validated = int(outcome.get("ai_validated", 0))

                record = dict(company)
                record["resolved_domain"] = domain
                record["domain_source"] = source_field
                record["domain_confidence"] = confidence
                record["domain_candidate"] = candidate
                record["domain_validation_status"] = validation_status
                record["domain_review_required"] = 1 if review_required else 0
                record["domain_ai_validated"] = ai_validated
                record["domain_ai_decision"] = outcome.get("ai_decision")
                record["domain_ai_confidence"] = outcome.get("ai_confidence")
                record["domain_ai_reason"] = outcome.get("ai_reason")

                if validation_status in {"accepted", "accepted_ai_validated"}:
                    accepted_count += 1
                elif validation_status == "review":
                    review_count += 1
                else:
                    rejected_count += 1

                if domain:
                    resolved_count += 1

                ordered_results[idx] = record

        for idx in range(len(companies)):
            resolved.append(ordered_results[idx])

        self.ctx.metrics["companies_with_domain"] = resolved_count
        self.ctx.metrics["domain_resolution_accepted"] = accepted_count
        self.ctx.metrics["domain_resolution_review"] = review_count
        self.ctx.metrics["domain_resolution_rejected"] = rejected_count
        self.ctx.metrics["domain_resolution_completed"] = True
        return resolved
