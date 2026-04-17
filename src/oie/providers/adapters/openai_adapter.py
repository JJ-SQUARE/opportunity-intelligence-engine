from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List

import requests

from oie.providers.base import ProviderClient


AGGREGATOR_HINTS = {
    "jobgether",
    "multitrabajos",
    "vacantesdigitales",
    "computrabajo",
    "linkedin",
    "indeed",
    "glassdoor",
    "grabjobs",
    "talenteca",
    "jobleads",
    "oficinaempleo",
    "quierolaburo",
    "jooble",
    "jobrapido",
    "trabajo",
    "bumeran",
    "elempleo",
    "magneto365",
    "sercanto",
    "pangian",
    "adzuna",
    "ok.com",
}


class OpenAIAdapter(ProviderClient):
    provider_name = "openai"

    def _openai_api_key(self) -> str:
        return (
            os.getenv("OPENAI_API_KEY")
            or os.getenv("OIE_OPENAI_API_KEY")
            or ""
        ).strip()

    def _openai_model(self) -> str:
        return (
            os.getenv("OIE_OPENAI_MODEL")
            or os.getenv("OPENAI_MODEL")
            or "gpt-4.1-mini"
        ).strip()

    def _chat_completion_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        api_key = self._openai_api_key()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY no configurada")

        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": self._openai_model(),
                "temperature": 0.1,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        content = (
            payload.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "{}")
        )
        return json.loads(content)

    def _truncate(self, value: Any, limit: int = 1200) -> str:
        text = str(value or "").strip()
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    def _company_scoring_prompts(self, company_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = '''
Act as a Senior B2B Sales Analyst for Tekton Labs. Your task is to qualify outbound prospecting opportunities for the following services:
Talent as a Service
Agile Solution Delivery
Managed IT Services
Priority Strategy: Focus on the Ideal Customer Profile (ICP). Apply heavy penalties to direct competitors, staffing firms, software consultancies, and outsourcing shops, regardless of their hiring volume.
Output Format: Return ONLY a valid JSON object. Do not include preamble or conversational text. Use this exact schema:
{
  "opportunity_score": 0,
  "opportunity_label": "high|medium|low",
  "score_icp_fit": 0,
  "score_pain_urgency": 0,
  "score_region_fit": 0,
  "score_company_scale": 0,
  "score_role_seniority_mix": 0,
  "score_penalty_competitor": 0,
  "score_penalty_negative_signals": 0,
  "primary_service_fit": "talent_as_a_service|agile_solution_delivery|managed_it_services|mixed|unknown",
  "buyer_persona_fit": "high|medium|low",
  "one_liner_reason": "max 2 líneas"
}

Scoring Logic (Final Scale 0-100):
- score_icp_fit: 0-30
- score_pain_urgency: 0-25
- score_region_fit: 0-10
- score_company_scale: 0-10
- score_role_seniority_mix: 0-10
- score_penalty_competitor: 0 a -30
- score_penalty_negative_signals: 0 a -15

Interpretación:
- HIGH: >= 75 y además buen fit ICP + dolor real
- MEDIUM: 45-74
- LOW: < 45

Target Buyer Personas: Strategic C-Level and Directors with budget authority and urgent pain points. 

Focus on: CTO, COO, CDO, VP of Engineering, Engineering Manager/Director, IT Manager, Innovation Manager, and Digital Channels Manager.

Priority Industries: Focus on high-intent sectors: BFSI (key for legacy modernization) , Insurance, Aerospace/Airlines, Technology, Healthcare/Life Sciences, and Logistics/Transportation.

Company Scale: Strictly Enterprise and Mid-Market. Disregard small entities, local government, or low-scale municipal banks.

Geographic Focus: USA and Canada (Priority Market) and core LATAM regions: México, Panamá, Colombia, Chile, Ecuador, Argentina, Uruguay, Perú, Guatemala, El Salvador, Costa Rica, República Dominicana, Bolivia, and Paraguay.

High-Value Signals: (Urgency: Roles open +30 days, "Urgent hiring", or "Critical role".) AND (Tech Stack: Node, React, Python, Java, Cloud, and AI.) AND (Strategic Shifts: New leadership (CTO/VP) in last 3-6 months , geographic expansion, or legacy-to-cloud migration)

Medium Signals: Steady hiring; AI/IoT exploration; innovation webinars/events.

Negative Signals: Focus on juniors/trainees; "Direct hire only/No agencies"; layoffs; hiring freeze; budget cuts; direct competitors (Software factories, staffing, outsourcing).


Core Instructions:
- If the target is a competitor/staffing vendor, apply maximum penalty but do not discard.
- If the company size is ideal but the industry is non-core, retain but penalize.
- If data is missing, infer conservatively.
'''.strip()

        scoring_context = company_payload.get("scoring_context") or {}

        user_prompt = f'''
Evaluate this company for Tekton Labs outbound sales.

ICP / commercial context:
{self._truncate(json.dumps(scoring_context, ensure_ascii=False), 4000)}

company_display: {company_payload.get("company_display") or company_payload.get("company") or ""}
company_type_ai: {company_payload.get("company_type_ai") or ""}
classification_confidence_ai: {company_payload.get("classification_confidence_ai") or ""}
industry: {company_payload.get("industry") or ""}
company_size: {company_payload.get("company_size") or company_payload.get("employee_range") or ""}
resolved_domain: {company_payload.get("resolved_domain") or ""}
linkedin_company_url: {company_payload.get("linkedin_company_url") or ""}
company_description: {self._truncate(company_payload.get("company_description") or "", 1800)}

total_openings: {company_payload.get("total_openings") or 0}
remote_jobs: {company_payload.get("remote_jobs") or 0}
contractor_jobs: {company_payload.get("contractor_jobs") or 0}
remote_ratio: {company_payload.get("remote_ratio") or 0}
contractor_ratio: {company_payload.get("contractor_ratio") or 0}
multi_source_signal: {company_payload.get("multi_source_signal") or False}
sources: {company_payload.get("sources") or []}

jobs_summary:
{self._truncate(json.dumps(company_payload.get("jobs") or [], ensure_ascii=False), 5000)}

I need a score oriented toward the real commercial ICP, not gross vacancy volume.
'''.strip()

        return system_prompt, user_prompt

    def score_company_opportunity(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._company_scoring_prompts(company_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            opportunity_score = int(result.get("opportunity_score", 0) or 0)
        except Exception:
            opportunity_score = 0

        opportunity_score = max(0, min(opportunity_score, 100))

        return {
            "opportunity_score": opportunity_score,
            "opportunity_label": str(result.get("opportunity_label") or "low").strip().lower(),
            "score_icp_fit": int(result.get("score_icp_fit", 0) or 0),
            "score_pain_urgency": int(result.get("score_pain_urgency", 0) or 0),
            "score_region_fit": int(result.get("score_region_fit", 0) or 0),
            "score_company_scale": int(result.get("score_company_scale", 0) or 0),
            "score_role_seniority_mix": int(result.get("score_role_seniority_mix", 0) or 0),
            "score_penalty_competitor": int(result.get("score_penalty_competitor", 0) or 0),
            "score_penalty_negative_signals": int(result.get("score_penalty_negative_signals", 0) or 0),
            "primary_service_fit": str(result.get("primary_service_fit") or "unknown").strip().lower(),
            "buyer_persona_fit": str(result.get("buyer_persona_fit") or "low").strip().lower(),
            "opportunity_score_reason": str(result.get("one_liner_reason") or "").strip(),
            "scoring_provider": self.provider_name,
            "scoring_model": self._openai_model(),
            "scoring_mode": "live_api",
        }


    def _lead_scoring_prompts(self, lead_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = '''
Act as a Senior B2B Sales Analyst for Tekton Labs. Your task is to score an individual outbound contact for commercial outreach quality.

Return ONLY a valid JSON object with this exact schema:
{
  "lead_relevance_score": 0,
  "lead_priority_label": "high|medium|low",
  "lead_decision_maker_score": 0,
  "lead_icp_fit_score": 0,
  "lead_contact_completeness_score": 0,
  "lead_penalty_negative_title": 0,
  "lead_score_reason": "max 2 líneas"
}

Scoring Logic (Final Scale 0-100):
- lead_decision_maker_score: 0-40
- lead_icp_fit_score: 0-30
- lead_contact_completeness_score: 0-20
- lead_penalty_negative_title: 0 a -25

Interpretación:
- HIGH: >= 75
- MEDIUM: 45-74
- LOW: < 45

Prioritize technical and budget-relevant decision makers such as CTO, VP Engineering, Head of Engineering, Director of Engineering, Engineering Manager, IT Manager, Innovation Manager, and Digital Channels Manager.

Use conservative judgment when data is missing.
'''.strip()

        scoring_context = lead_payload.get("lead_scoring_context") or {}

        user_prompt = f'''
Evaluate this contact for Tekton Labs outbound sales.

lead_scoring_context:
{self._truncate(json.dumps(scoring_context, ensure_ascii=False), 3000)}

company_display: {lead_payload.get("company_display") or ""}
industry: {lead_payload.get("industry") or ""}
resolved_domain: {lead_payload.get("resolved_domain") or ""}
company_type_ai: {lead_payload.get("company_type_ai") or ""}
opportunity_score: {lead_payload.get("opportunity_score") or 0}

contact_name: {lead_payload.get("contact_name") or ""}
contact_title: {lead_payload.get("contact_title") or ""}
email: {lead_payload.get("email") or ""}
linkedin_url: {lead_payload.get("linkedin_url") or ""}
lead_source: {lead_payload.get("lead_source") or ""}
lead_confidence: {lead_payload.get("lead_confidence") or 0}
email_quality_score: {lead_payload.get("email_quality_score") or 0}
lead_capture_reason: {self._truncate(lead_payload.get("lead_capture_reason") or "", 800)}
'''.strip()

        return system_prompt, user_prompt

    def score_lead(self, lead_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._lead_scoring_prompts(lead_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            lead_relevance_score = int(result.get("lead_relevance_score", 0) or 0)
        except Exception:
            lead_relevance_score = 0

        lead_relevance_score = max(0, min(lead_relevance_score, 100))

        return {
            "lead_relevance_score": lead_relevance_score,
            "lead_priority_label": str(result.get("lead_priority_label") or "low").strip().lower(),
            "lead_decision_maker_score": int(result.get("lead_decision_maker_score", 0) or 0),
            "lead_icp_fit_score": int(result.get("lead_icp_fit_score", 0) or 0),
            "lead_contact_completeness_score": int(result.get("lead_contact_completeness_score", 0) or 0),
            "lead_penalty_negative_title": int(result.get("lead_penalty_negative_title", 0) or 0),
            "lead_score_reason": str(result.get("lead_score_reason") or "").strip(),
            "lead_scoring_provider": self.provider_name,
            "lead_scoring_model": self._openai_model(),
            "lead_scoring_mode": "live_api",
        }

    # aliases defensivos para no depender del nombre exacto usado por el service
    def score_company(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.score_company_opportunity(company_payload)

    def score_opportunity(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.score_company_opportunity(company_payload)

    def classify_company(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        company_name = company_payload.get("company_display") or company_payload.get("company") or "unknown"

        return {
            "company_name": company_name,
            "classification": "unknown",
            "confidence": 0.0,
            "provider": self.provider_name,
            "mode": "stub",
        }

    def _normalize_text(self, value: Any) -> str:
        return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()

    def _tokenize(self, value: Any) -> List[str]:
        text = self._normalize_text(value)
        if not text:
            return []
        return [token for token in text.split() if token]

    def _core_tokens(self, company_name: str) -> List[str]:
        stopwords = {
            "the",
            "and",
            "group",
            "holding",
            "holdings",
            "company",
            "companies",
            "global",
            "international",
            "latam",
            "mexico",
            "colombia",
            "ecuador",
            "spain",
            "españa",
            "sa",
            "sas",
            "s a",
            "llc",
            "inc",
            "corp",
            "co",
            "ltd",
            "sl",
            "s l",
            "de",
            "del",
        }
        tokens = self._tokenize(company_name)
        core = [t for t in tokens if t not in stopwords]
        return core or tokens[:1]

    def _is_aggregator_domain(self, domain: str) -> bool:
        normalized = self._normalize_text(domain)
        return any(hint in normalized for hint in AGGREGATOR_HINTS)

    def _candidate_text(self, candidate: Dict[str, Any]) -> str:
        return " ".join(
            [
                str(candidate.get("domain") or ""),
                str(candidate.get("title") or ""),
                str(candidate.get("snippet") or ""),
            ]
        ).lower()

    def _is_suspicious_subdomain(self, domain: str) -> bool:
        normalized = str(domain or "").strip().lower()
        if not normalized:
            return False

        parts = [p for p in normalized.split(".") if p]
        if len(parts) < 3:
            return False

        suspicious_prefixes = {
            "beta",
            "staging",
            "stage",
            "dev",
            "test",
            "qa",
            "sandbox",
            "preview",
            "demo",
            "internal",
        }

        return parts[0] in suspicious_prefixes

    def validate_domain_candidates(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        company_name = str(payload.get("company_name") or "").strip()
        candidates = payload.get("candidates") or []

        if not company_name or not candidates:
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "missing_company_or_candidates",
            }

        core_tokens = self._core_tokens(company_name)
        best_candidate = None
        best_score = -1.0

        for candidate in candidates:
            domain = str(candidate.get("domain") or "").strip().lower()
            title = str(candidate.get("title") or "")
            snippet = str(candidate.get("snippet") or "")
            source = str(candidate.get("source") or "")
            text = self._candidate_text(candidate)

            if not domain:
                continue

            if self._is_aggregator_domain(domain):
                candidate_score = -1.0
            else:
                token_hits = sum(1 for token in core_tokens if token and token in text)
                domain_hits = sum(1 for token in core_tokens if token and token in domain)
                official_bonus = 1 if "official" in text or "sitio oficial" in text else 0
                serp_bonus = 0.25 if source == "serpapi_fallback" else 0.0

                candidate_score = (domain_hits * 2.0) + token_hits + official_bonus + serp_bonus

            if candidate_score > best_score:
                best_score = candidate_score
                best_candidate = candidate

        if not best_candidate:
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.0,
                "reason": "no_viable_candidate",
            }

        domain = str(best_candidate.get("domain") or "").strip().lower()
        text = self._candidate_text(best_candidate)
        domain_hits = sum(1 for token in core_tokens if token and token in domain)
        text_hits = sum(1 for token in core_tokens if token and token in text)
        total_hits = len({token for token in core_tokens if token and token in text})

        if self._is_aggregator_domain(domain):
            return {
                "selected_domain": None,
                "decision": "rejected",
                "confidence": 0.05,
                "reason": "aggregator_domain",
            }

        if self._is_suspicious_subdomain(domain):
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.45,
                "reason": "suspicious_subdomain",
            }

        if domain_hits >= 1 and text_hits >= 1:
            return {
                "selected_domain": domain,
                "decision": "accepted",
                "confidence": 0.90,
                "reason": "brand_and_text_match",
            }

        if domain_hits >= 1 and total_hits >= 2:
            return {
                "selected_domain": domain,
                "decision": "accepted",
                "confidence": 0.82,
                "reason": "strong_partial_brand_match",
            }

        if domain_hits >= 1:
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.65,
                "reason": "domain_brand_match_only",
            }

        if total_hits >= 2:
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.60,
                "reason": "partial_brand_match",
            }

        if text_hits >= 1:
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.55,
                "reason": "text_brand_match_only",
            }

        return {
            "selected_domain": None,
            "decision": "rejected",
            "confidence": 0.10,
            "reason": "insufficient_brand_match",
        }
