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

CLASSIFICATION_RULE_KEYWORDS = {
    "competitor": {
        "bairesdev",
        "globant",
        "softserve",
    },
    "staffing": {
        "staffing",
        "staffing and recruiting",
        "recruiting",
        "recruitment",
        "talent solutions",
        "talent acquisition",
        "headhunting",
        "executive search",
    },
    "outsourcing": {
        "outsourcing",
        "outsource",
        "outstaffing",
        "staff augmentation",
        "nearshore software",
        "nearshore development",
        "dedicated teams",
        "software outsourcing",
        "technology outsourcing",
    },
    "consulting": {
        "consulting",
        "consultancy",
        "professional services",
        "advisory",
        "technology consulting",
        "software consulting",
        "software consultancy",
        "software development services",
        "digital transformation services",
        "systems integrator",
        "it services",
    },
    "marketplace": {
        "marketplace",
        "two-sided marketplace",
        "talent marketplace",
    },
    "job_board": {
        "job board",
        "jobs board",
        "career portal",
        "job search",
        "find jobs",
        "empleos",
        "vacantes",
    },
}

END_CLIENT_CLASSIFICATION_HINTS = {
    "saas",
    "platform",
    "software product",
    "builds software products",
    "product company",
    "banking and financial services",
    "insurance",
    "healthcare",
    "life sciences",
    "logistics",
    "transportation",
    "airlines",
    "aviation",
    "computer software",
    "software company",
    "fintech",
    "proptech",
    "healthtech",
    "edtech",
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

    def _enrichment_validation_prompts(self, payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a Senior Company Data Validation Analyst for Tekton Labs.
Your task is to validate whether an Apollo company enrichment result belongs to the intended company.

Return ONLY a valid JSON object with this exact schema:
{
  "is_match": true,
  "confidence": 0.0,
  "decision": "accepted|review|rejected",
  "reason": "max 1 línea"
}

Rules:
- Accept only when the enriched organization clearly matches the company name/domain.
- Reject if Apollo data appears to describe a different company, job board, staffing firm, or unrelated domain.
- Use review when evidence is partial, generic, ambiguous, or incomplete.
- Never hallucinate missing evidence.
""".strip()

        user_prompt = f"""
Validate this Apollo enrichment result.

company_display: {payload.get("company_display") or payload.get("company") or ""}
resolved_domain: {payload.get("resolved_domain") or ""}
domain_validation_status: {payload.get("domain_validation_status") or ""}
company_type_ai: {payload.get("company_type_ai") or ""}
classification_confidence_ai: {payload.get("classification_confidence_ai") or ""}

apollo_enrichment:
{self._truncate(json.dumps(payload.get("apollo_enrichment") or {}, ensure_ascii=False), 5000)}

Return strict JSON only.
""".strip()

        return system_prompt, user_prompt

    def validate_company_enrichment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._enrichment_validation_prompts(payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            confidence = float(result.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0

        decision = str(result.get("decision") or "review").strip().lower()
        if decision not in {"accepted", "review", "rejected"}:
            decision = "review"

        return {
            "enrichment_ai_match": bool(result.get("is_match")),
            "enrichment_ai_confidence": max(0.0, min(confidence, 1.0)),
            "enrichment_ai_decision": decision,
            "enrichment_ai_reason": str(result.get("reason") or "").strip(),
            "enrichment_ai_provider": self.provider_name,
            "enrichment_ai_model": self._openai_model(),
            "enrichment_ai_mode": "live_api",
        }


    def _buyer_persona_prompts(self, company_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a Senior B2B Buyer Persona Analyst for Tekton Labs.

Your task is to infer the best target buyer personas for outbound prospecting into a company.

Return ONLY a valid JSON object with this exact schema:
{
  "buyer_personas": [
    {
      "persona": "CTO",
      "priority": "high|medium|low",
      "rationale": "max 1 línea",
      "target_titles": ["CTO", "VP Engineering"],
      "title_search_patterns": ["engineering leadership", "digital transformation"],
      "pain_alignment": "max 1 línea",
      "recommended_channel": "email|linkedin|phone|multi_channel"
    }
  ],
  "reason": "max 2 líneas"
}

Rules:
- Recommend only personas relevant to Tekton Labs services: engineering staffing, agile delivery, modernization, cloud, AI, managed IT.
- Prefer decision makers and strong influencers.
- Use company industry, jobs, pain signals, company size, and enrichment evidence.
- Never hallucinate specific people.
- Keep target_titles concise and searchable.
- Include title_search_patterns as AI-generated semantic matching hints, not regex syntax.
- Include why this persona aligns to the company's likely pain.
- Recommend the most practical outbound channel.
""".strip()

        user_prompt = f"""
Generate buyer personas for this company.

company_display: {company_payload.get("company_display") or company_payload.get("company") or ""}
company_type_ai: {company_payload.get("company_type_ai") or ""}
industry: {company_payload.get("industry") or ""}
company_size: {company_payload.get("company_size") or company_payload.get("employee_range") or ""}
resolved_domain: {company_payload.get("resolved_domain") or ""}
linkedin_company_url: {company_payload.get("linkedin_company_url") or ""}
company_description: {self._truncate(company_payload.get("company_description") or "", 1800)}
opportunity_score: {company_payload.get("opportunity_score") or 0}
opportunity_label: {company_payload.get("opportunity_label") or ""}
recommended_service: {company_payload.get("recommended_service") or company_payload.get("primary_service_fit") or ""}

jobs_summary:
{self._truncate(json.dumps(company_payload.get("jobs") or [], ensure_ascii=False), 5000)}

Return strict JSON only.
""".strip()

        return system_prompt, user_prompt

    def generate_buyer_personas(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._buyer_persona_prompts(company_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        personas = result.get("buyer_personas") or []
        if not isinstance(personas, list):
            personas = []

        normalized_personas: List[Dict[str, Any]] = []
        for item in personas[:5]:
            if not isinstance(item, dict):
                continue

            priority = str(item.get("priority") or "medium").strip().lower()
            if priority not in {"high", "medium", "low"}:
                priority = "medium"

            titles = item.get("target_titles") or item.get("suggested_titles") or []
            if not isinstance(titles, list):
                titles = []
            clean_titles = [str(title).strip() for title in titles if str(title or "").strip()][:8]

            patterns = item.get("title_search_patterns") or []
            if not isinstance(patterns, list):
                patterns = []
            clean_patterns = [str(pattern).strip() for pattern in patterns if str(pattern or "").strip()][:8]

            normalized_personas.append(
                {
                    "persona": str(item.get("persona") or "").strip(),
                    "priority": priority,
                    "rationale": str(item.get("rationale") or "").strip(),
                    "target_titles": clean_titles,
                    "suggested_titles": clean_titles,
                    "title_search_patterns": clean_patterns,
                    "pain_alignment": str(item.get("pain_alignment") or "").strip(),
                    "recommended_channel": str(item.get("recommended_channel") or "").strip(),
                }
            )

        return {
            "buyer_personas_ai": normalized_personas,
            "buyer_personas_ai_reason": str(result.get("reason") or "").strip(),
            "buyer_personas_ai_provider": self.provider_name,
            "buyer_personas_ai_model": self._openai_model(),
            "buyer_personas_ai_mode": "live_api",
        }


    def _company_scoring_prompts(self, company_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = '''
Act as a Senior B2B Sales Analyst for Tekton Labs.

Your task is to STRICTLY qualify outbound prospecting opportunities based on REAL commercial viability, not hiring noise.

You are NOT scoring interest. You are scoring probability of creating a real sales opportunity for Tekton Labs.

Tekton Labs sells:
- Talent as a Service: senior engineers / technical experts integrated quickly into client teams.
- Agile Solution Delivery: end-to-end product delivery, modernization, cloud, AI, and engineering squads.
- Managed IT Services: operation, support, maintenance, and continuity for critical platforms.

Return ONLY a valid JSON object. No markdown, no prose outside JSON.

Required schema:
{
  "opportunity_score": 0,
  "icp_bucket": "strong|medium|weak",
  "commercial_bucket": "high|medium|low",
  "pain_urgency": "high|medium|low",
  "buyer_persona_fit": "high|medium|low",
  "recommended_service": "talent_as_a_service|agile_solution_delivery|managed_it_services|mixed|unknown",
  "reason": "max 2 líneas"
}

NON-NEGOTIABLE SCORING RULES:

1. ICP first:
If icp_bucket is weak, opportunity_score MUST be below 45 and commercial_bucket MUST be low.

2. Vendor / competitor penalty:
If company_type_ai is competitor, staffing, consulting, outsourcing, software factory, marketplace, or job_board:
- commercial_bucket MUST be low.
- opportunity_score MUST be below 40.
- Do not reward hiring volume from vendor-like companies.

3. Hiring volume is not enough:
Many open roles, remote roles, or contractor roles must NOT produce high scores unless there is strong ICP, real pain, and buyer relevance.

4. Buyer persona gating:
If buyer_persona_fit is low, opportunity_score MUST be <= 55.

5. Reachability and credibility:
If domain, LinkedIn, enrichment, or domain validation signals are weak/missing, do not return high unless ICP and pain evidence are exceptionally clear.

6. Conservative default:
If evidence is incomplete, ambiguous, generic, or mostly inferred, return low or medium. Never hallucinate missing facts.

Commercial bucket consistency:
- high: score >= 75 AND icp_bucket=strong AND pain_urgency=high AND buyer_persona_fit is medium/high.
- medium: score 45-74 OR good but incomplete evidence.
- low: score <45 OR weak ICP OR vendor-like target.

Target buyer personas:
CTO, COO, CDO, VP Engineering, Head of Engineering, Engineering Director, Engineering Manager, IT Manager, Innovation Manager, Digital Channels Manager.

Priority ICP industries:
BFSI, banking, financial services, insurance, airlines, aerospace, technology, healthcare, life sciences, logistics, transportation.

High-value pain signals:
Cloud migration, legacy modernization, AI initiatives, platform rebuilds, microservices, urgent senior technical hiring, multiple strategic engineering roles, new technical leadership, expansion.

Negative signals:
Junior-only hiring, trainees, internships, no agencies, direct hire only, layoffs, hiring freeze, budget cuts, unclear company identity, job boards, staffing, consulting, outsourcing.
'''.strip()

        scoring_context = company_payload.get("scoring_context") or {}

        user_prompt = f'''
Evaluate this company for Tekton Labs outbound sales.

ICP / commercial context:
{self._truncate(json.dumps(scoring_context, ensure_ascii=False), 4000)}

company_display: {company_payload.get("company_display") or company_payload.get("company") or ""}
company_type_ai: {company_payload.get("company_type_ai") or ""}
classification_confidence_ai: {company_payload.get("classification_confidence_ai") or ""}
classification_reason: {company_payload.get("classification_reason") or ""}
industry: {company_payload.get("industry") or ""}
company_size: {company_payload.get("company_size") or company_payload.get("employee_range") or ""}
resolved_domain: {company_payload.get("resolved_domain") or ""}
domain_confidence: {company_payload.get("domain_confidence") or ""}
domain_validation_status: {company_payload.get("domain_validation_status") or ""}
domain_ai_decision: {company_payload.get("domain_ai_decision") or ""}
domain_ai_confidence: {company_payload.get("domain_ai_confidence") or ""}
linkedin_company_url: {company_payload.get("linkedin_company_url") or ""}
enrichment_source: {company_payload.get("enrichment_source") or ""}
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

Score ONLY based on real commercial potential.

Ignore hiring volume if ICP fit is weak.

If data is incomplete, ambiguous, generic, or low credibility, assume LOW confidence and score conservatively.

Return strict JSON only.
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

        commercial_bucket = str(
            result.get("commercial_bucket")
            or result.get("opportunity_label")
            or "low"
        ).strip().lower()
        icp_bucket = str(result.get("icp_bucket") or "weak").strip().lower()
        pain_urgency = str(result.get("pain_urgency") or "low").strip().lower()
        recommended_service = str(
            result.get("recommended_service")
            or result.get("primary_service_fit")
            or "unknown"
        ).strip().lower()
        reason = str(
            result.get("reason")
            or result.get("one_liner_reason")
            or ""
        ).strip()

        bucket_to_score = {"strong": 28, "medium": 16, "weak": 6}
        urgency_to_score = {"high": 22, "medium": 12, "low": 4}

        return {
            "opportunity_score": opportunity_score,
            "icp_bucket": icp_bucket,
            "commercial_bucket": commercial_bucket,
            "pain_urgency": pain_urgency,
            "recommended_service": recommended_service,
            "reason": reason,
            "opportunity_label": commercial_bucket,
            "score_icp_fit": int(result.get("score_icp_fit", bucket_to_score.get(icp_bucket, 6)) or 0),
            "score_pain_urgency": int(result.get("score_pain_urgency", urgency_to_score.get(pain_urgency, 4)) or 0),
            "score_region_fit": int(result.get("score_region_fit", 0) or 0),
            "score_company_scale": int(result.get("score_company_scale", 0) or 0),
            "score_role_seniority_mix": int(result.get("score_role_seniority_mix", 0) or 0),
            "score_penalty_competitor": int(result.get("score_penalty_competitor", 0) or 0),
            "score_penalty_negative_signals": int(result.get("score_penalty_negative_signals", 0) or 0),
            "primary_service_fit": recommended_service,
            "buyer_persona_fit": str(result.get("buyer_persona_fit") or "low").strip().lower(),
            "opportunity_score_reason": reason,
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
  "lead_role_type": "primary_decision_maker|technical_influencer|business_sponsor|operations_stakeholder|fallback_contact",
  "why_selected": "max 1 línea",
  "outreach_angle": "max 1 línea",
  "expected_relevance": "high|medium|low",
  "risk_or_uncertainty": "max 1 línea",
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

Classify each contact as one of:
- primary_decision_maker
- technical_influencer
- business_sponsor
- operations_stakeholder
- fallback_contact

Evaluate seniority, area, decision power, relation to detected pain, available channel, and fit with the suggested buyer persona.

Do not discard useful leads only because their title is not in a rigid title list. Use the full buyer persona context.

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
target_persona: {lead_payload.get("target_persona") or ""}
suggested_titles: {lead_payload.get("suggested_titles") or ""}
title_search_patterns: {lead_payload.get("title_search_patterns") or ""}
search_reason: {lead_payload.get("search_reason") or ""}
pain_alignment: {lead_payload.get("pain_alignment") or ""}
priority: {lead_payload.get("priority") or ""}
recommended_channel: {lead_payload.get("recommended_channel") or ""}
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
            "lead_role_type": str(result.get("lead_role_type") or "fallback_contact").strip().lower(),
            "why_selected": str(result.get("why_selected") or "").strip(),
            "outreach_angle": str(result.get("outreach_angle") or "").strip(),
            "expected_relevance": str(result.get("expected_relevance") or "").strip().lower(),
            "risk_or_uncertainty": str(result.get("risk_or_uncertainty") or "").strip(),
            "lead_score_reason": str(result.get("lead_score_reason") or "").strip(),
            "lead_scoring_provider": self.provider_name,
            "lead_scoring_model": self._openai_model(),
            "lead_scoring_mode": "live_api",
        }

    def _urgency_gate_prompts(self, job_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a job posting freshness and urgency analyst.
Your task is to estimate how recent and urgent a job posting is.

Return ONLY a valid JSON object with this exact schema:
{
  "days_old_estimate": 0,
  "freshness_score": 0.0,
  "freshness_bucket": "same_day|this_week|last_2_weeks|this_month|1_to_3_months|3_to_6_months|older_than_6_months|unknown",
  "urgency_score": 0.0,
  "should_advance": true,
  "reason": ""
}

Rules:
- days_old_estimate: best estimate of days since posting. Use 0 for today/just posted/hours ago.
- freshness_score: 0.0 to 10.0. Same day=10, this week=8, 2 weeks=7, this month=6, 1-3 months=4, 3-6 months=2, older=0, unknown=5.
- urgency_score: 0.0 to 10.0. Score based on urgency signals in description: "ASAP", "immediate", "urgent", "contratación inmediata", "urgente", etc.
- should_advance=false only when days_old_estimate > 180 AND urgency_score < 2.
- When posted_at is missing and no urgency signals exist, use freshness_score=5.0 and should_advance=true.
- reason: brief explanation of the freshness/urgency assessment.
""".strip()

        posted_at = str(job_payload.get("posted_at_raw") or job_payload.get("detected_at") or "").strip()
        description = self._truncate(job_payload.get("description") or "", 800)

        user_prompt = f"""
Evaluate the freshness and urgency of this job posting.

posted_at: {posted_at or "unknown"}
title: {job_payload.get("title") or ""}
company: {job_payload.get("company") or ""}
description_snippet: {description}
""".strip()

        return system_prompt, user_prompt

    def analyze_urgency(self, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._urgency_gate_prompts(job_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            freshness_score = float(result.get("freshness_score", 5.0) or 5.0)
            urgency_score = float(result.get("urgency_score", 0.0) or 0.0)
            days_old = int(result.get("days_old_estimate", -1) or -1)
        except Exception:
            freshness_score = 5.0
            urgency_score = 0.0
            days_old = -1

        return {
            "days_old_estimate": days_old,
            "freshness_score": max(0.0, min(freshness_score, 10.0)),
            "freshness_bucket": str(result.get("freshness_bucket") or "unknown").strip(),
            "urgency_score": max(0.0, min(urgency_score, 10.0)),
            "should_advance": bool(result.get("should_advance", True)),
            "reason": str(result.get("reason") or "").strip(),
            "urgency_provider": self.provider_name,
            "urgency_model": self._openai_model(),
        }

    def _job_gate_prompts(self, job_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a commercial filter for Tekton Labs, a nearshore software development company.
Your task is to quickly decide if a job posting comes from a company worth investigating further.

Tekton Labs sells software development services to end clients and product companies.
We are NOT interested in: staffing agencies, outsourcing/nearshore competitors, job boards,
aggregators, confidential postings, or noise.

Return ONLY a valid JSON object with this exact schema:
{
  "should_advance": true,
  "company_type": "end_client|product_company|consulting|staffing_agency|outsourcing|nearshore|job_board|competitor|confidential|noise|unknown",
  "confidence": 0.0,
  "block_reason": ""
}

Rules:
- should_advance=true for end_client, product_company, unknown (when insufficient evidence to block).
- should_advance=false for staffing_agency, outsourcing, nearshore, job_board, competitor, confidential, noise.
- competitor means a company that sells software development services similar to Tekton Labs.
- outsourcing/nearshore means a company that places developers with other companies.
- confidence is how sure you are about company_type (0.0 to 1.0).
- block_reason explains why blocked, empty string if advancing.
- When in doubt, let it advance (should_advance=true). Apollo will confirm later.
- Use conservative judgment: only block when evidence is clear.
""".strip()

        user_prompt = f"""
Evaluate this job posting.

company: {job_payload.get("company") or ""}
title: {job_payload.get("title") or job_payload.get("job_title") or ""}
source: {job_payload.get("source") or ""}
job_url: {job_payload.get("job_url") or job_payload.get("url") or ""}
description: {self._truncate(job_payload.get("description") or "", 1200)}
""".strip()

        return system_prompt, user_prompt

    def gate_job(self, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._job_gate_prompts(job_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            confidence = float(result.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0

        return {
            "should_advance": bool(result.get("should_advance", True)),
            "company_type": str(result.get("company_type") or "unknown").strip().lower(),
            "confidence": max(0.0, min(confidence, 1.0)),
            "block_reason": str(result.get("block_reason") or "").strip(),
            "job_gate_provider": self.provider_name,
            "job_gate_model": self._openai_model(),
            "job_gate_mode": "live_api",
        }

    def _job_gate_prompts(self, job_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a commercial filter for Tekton Labs, a nearshore software development company.
Your task is to quickly decide if a job posting comes from a company worth investigating further.

Tekton Labs sells software development services to end clients and product companies.
We are NOT interested in: staffing agencies, outsourcing/nearshore competitors, job boards,
aggregators, confidential postings, or noise.

Return ONLY a valid JSON object with this exact schema:
{
  "should_advance": true,
  "company_type": "end_client|product_company|consulting|staffing_agency|outsourcing|nearshore|job_board|competitor|confidential|noise|unknown",
  "confidence": 0.0,
  "block_reason": ""
}

Rules:
- should_advance=true for end_client, product_company, unknown (when insufficient evidence to block).
- should_advance=false for staffing_agency, outsourcing, nearshore, job_board, competitor, confidential, noise.
- competitor means a company that sells software development services similar to Tekton Labs.
- outsourcing/nearshore means a company that places developers with other companies.
- confidence is how sure you are about company_type (0.0 to 1.0).
- block_reason explains why blocked, empty string if advancing.
- When in doubt, let it advance (should_advance=true). Apollo will confirm later.
- Use conservative judgment: only block when evidence is clear.
""".strip()

        user_prompt = f"""
Evaluate this job posting.

company: {job_payload.get("company") or ""}
title: {job_payload.get("title") or job_payload.get("job_title") or ""}
source: {job_payload.get("source") or ""}
job_url: {job_payload.get("job_url") or job_payload.get("url") or ""}
description: {self._truncate(job_payload.get("description") or "", 1200)}
""".strip()

        return system_prompt, user_prompt

    def gate_job(self, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._job_gate_prompts(job_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            confidence = float(result.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0

        return {
            "should_advance": bool(result.get("should_advance", True)),
            "company_type": str(result.get("company_type") or "unknown").strip().lower(),
            "confidence": max(0.0, min(confidence, 1.0)),
            "block_reason": str(result.get("block_reason") or "").strip(),
            "job_gate_provider": self.provider_name,
            "job_gate_model": self._openai_model(),
            "job_gate_mode": "live_api",
        }

    def _job_intelligence_prompts(self, job_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a Senior Job Intelligence Analyst for Tekton Labs.
Your task is to interpret one collected job record and return only structured JSON.

Return ONLY a valid JSON object with this exact schema:
{
  "is_real_job": true,
  "is_contaminated": false,
  "real_company_name": "",
  "confidence": 0.0,
  "usable_for_scoring": true,
  "role": "",
  "seniority": "",
  "tech_stack": [],
  "budget": "",
  "workplace_type": "",
  "commercial_signals": [],
  "canonical_company_name": "",
  "company_type": "end_client|product_company|consulting|staffing_agency|marketplace|job_board|competitor|confidential|noise|unknown",
  "official_domain_guess": "",
  "commercial_relevance": "high|medium|low|blocked",
  "should_advance": true,
  "advance_reason": ""
}

Rules:
- Identify whether the record is a real job posting or a contaminated SERP snippet.
- If the snippet mentions another company different from the apparent employer, set is_contaminated=true.
- real_company_name must be the company that is actually hiring when inferable.
- usable_for_scoring=false when the job is contaminated, fake, aggregator-only, or insufficient.
- tech_stack and commercial_signals must be arrays of concise strings.
- Use conservative judgment when evidence is missing.
- Act like a human first-pass commercial filter for Tekton Labs.
- canonical_company_name must be the best normalized hiring company name, not the job board/wrapper.
- company_type must classify the real entity: end_client, product_company, consulting, staffing_agency, marketplace, job_board, competitor, confidential, noise, or unknown.
- official_domain_guess should be the likely corporate domain only when inferable; never use job boards, LinkedIn job URLs, or apply wrappers as corporate domains.
- commercial_relevance=blocked and should_advance=false for job boards, staffing marketplaces, confidential/noise, fake jobs, or aggregator-only records.
- product_company and end_client should usually advance when the job is real and the company is identifiable.
- staffing_agency, consulting, marketplace, and competitor may be real but should usually be low/blocked unless clearly useful for benchmark or partner analysis.
- advance_reason must briefly explain why this job/company should advance or be blocked.
""".strip()

        user_prompt = f"""
Analyze this collected job record.

source: {job_payload.get("source") or ""}
title: {job_payload.get("title") or job_payload.get("job_title") or ""}
company: {job_payload.get("company") or ""}
location: {job_payload.get("location") or ""}
description: {self._truncate(job_payload.get("description") or "", 2500)}
job_url: {job_payload.get("job_url") or job_payload.get("url") or ""}
apply_url: {job_payload.get("apply_url") or ""}
source_meta: {self._truncate(json.dumps(job_payload.get("source_meta") or {}, ensure_ascii=False), 1500)}
raw: {self._truncate(json.dumps(job_payload.get("raw") or {}, ensure_ascii=False), 2500)}
""".strip()

        return system_prompt, user_prompt

    def analyze_job_intelligence(self, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._job_intelligence_prompts(job_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            confidence = float(result.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0

        tech_stack = result.get("tech_stack") or []
        commercial_signals = result.get("commercial_signals") or []
        if not isinstance(tech_stack, list):
            tech_stack = []
        if not isinstance(commercial_signals, list):
            commercial_signals = []

        return {
            "is_real_job": bool(result.get("is_real_job")),
            "is_contaminated": bool(result.get("is_contaminated")),
            "real_company_name": str(result.get("real_company_name") or "").strip(),
            "confidence": max(0.0, min(confidence, 1.0)),
            "usable_for_scoring": bool(result.get("usable_for_scoring")),
            "role": str(result.get("role") or "").strip(),
            "seniority": str(result.get("seniority") or "").strip(),
            "tech_stack": [str(item).strip() for item in tech_stack if str(item).strip()],
            "budget": str(result.get("budget") or "").strip(),
            "workplace_type": str(result.get("workplace_type") or "").strip(),
            "commercial_signals": [str(item).strip() for item in commercial_signals if str(item).strip()],
            "canonical_company_name": str(result.get("canonical_company_name") or result.get("real_company_name") or "").strip(),
            "company_type": str(result.get("company_type") or "unknown").strip().lower(),
            "official_domain_guess": str(result.get("official_domain_guess") or "").strip().lower(),
            "commercial_relevance": str(result.get("commercial_relevance") or "low").strip().lower(),
            "should_advance": bool(result.get("should_advance", result.get("usable_for_scoring"))),
            "advance_reason": str(result.get("advance_reason") or "").strip(),
            "job_intelligence_provider": self.provider_name,
            "job_intelligence_model": self._openai_model(),
            "job_intelligence_mode": "live_api",
        }

    def _company_identity_prompts(self, company_payload: Dict[str, Any]) -> tuple[str, str]:
        system_prompt = """
Act as a Senior Company Identity Analyst for Tekton Labs.
Your task is to determine the real hiring company behind collected SERP/job records.

Return ONLY a valid JSON object with this exact schema:
{
  "company_name": "",
  "source": "title|snippet|url|content|job_intelligence|unknown",
  "confidence": 0.0,
  "is_contaminated": false,
  "is_ambiguous": false,
  "usable_for_commercial": true,
  "reason": ""
}

Rules:
- Prefer job_intelligence when present and confident.
- Mark contaminated=true when the visible company appears to come from another job, wrapper, job board, or unrelated snippet.
- Mark ambiguous=true when there is not enough evidence to create a commercial company.
- usable_for_commercial=false when contaminated, ambiguous, placeholder, or not a real company.
- Use conservative judgment when evidence is missing.
""".strip()

        user_prompt = f"""
Resolve the company identity for this aggregated company/job signal.

company_display: {company_payload.get("company_display") or ""}
company: {company_payload.get("company") or ""}
resolved_domain: {company_payload.get("resolved_domain") or ""}
domain_source: {company_payload.get("domain_source") or ""}
domain_validation_status: {company_payload.get("domain_validation_status") or ""}
linkedin_company_url: {company_payload.get("linkedin_company_url") or ""}
company_description: {self._truncate(company_payload.get("company_description") or "", 1500)}
jobs: {self._truncate(json.dumps(company_payload.get("jobs") or [], ensure_ascii=False), 4500)}
sources: {company_payload.get("sources") or []}
""".strip()

        return system_prompt, user_prompt

    def resolve_company_identity(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        system_prompt, user_prompt = self._company_identity_prompts(company_payload)
        result = self._chat_completion_json(system_prompt, user_prompt)

        try:
            confidence = float(result.get("confidence", 0.0) or 0.0)
        except Exception:
            confidence = 0.0

        source = str(result.get("source") or "unknown").strip().lower()
        if source not in {"title", "snippet", "url", "content", "job_intelligence", "unknown"}:
            source = "unknown"

        return {
            "company_name": str(result.get("company_name") or "").strip(),
            "source": source,
            "confidence": max(0.0, min(confidence, 1.0)),
            "is_contaminated": bool(result.get("is_contaminated")),
            "is_ambiguous": bool(result.get("is_ambiguous")),
            "usable_for_commercial": bool(result.get("usable_for_commercial")),
            "reason": str(result.get("reason") or "").strip(),
            "provider": self.provider_name,
            "model": self._openai_model(),
            "mode": "live_api",
        }

    # aliases defensivos para no depender del nombre exacto usado por el service
    def score_company(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.score_company_opportunity(company_payload)

    def score_opportunity(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.score_company_opportunity(company_payload)

    def _company_classification_text(self, company_payload: Dict[str, Any]) -> str:
        jobs = company_payload.get("jobs") or []
        jobs_blob = json.dumps(jobs, ensure_ascii=False) if isinstance(jobs, list) else str(jobs or "")
        return " ".join(
            [
                str(company_payload.get("company_display") or ""),
                str(company_payload.get("company") or ""),
                str(company_payload.get("company_description") or ""),
                str(company_payload.get("industry") or ""),
                str(company_payload.get("resolved_domain") or ""),
                str(company_payload.get("linkedin_company_url") or ""),
                jobs_blob,
            ]
        ).lower()

    def _has_end_client_classification_evidence(self, company_payload: Dict[str, Any], text: str) -> bool:
        if not text.strip():
            return False

        if any(hint in text for hint in CLASSIFICATION_RULE_KEYWORDS.get("competitor", set())):
            return False

        for classification in ("staffing", "outsourcing", "consulting", "job_board", "marketplace"):
            keywords = CLASSIFICATION_RULE_KEYWORDS.get(classification, set())
            if any(keyword in text for keyword in keywords):
                return False

        industry = str(company_payload.get("industry") or "").strip().lower()
        description = str(company_payload.get("company_description") or "").strip().lower()
        jobs = company_payload.get("jobs") or []

        hint_hits = sum(1 for hint in END_CLIENT_CLASSIFICATION_HINTS if hint in text)
        has_product_language = any(term in description for term in ("product", "platform", "saas", "software"))
        has_build_language = any(term in description for term in ("builds", "develops", "operates", "offers", "provides"))
        has_clear_industry = bool(industry and any(hint in industry for hint in END_CLIENT_CLASSIFICATION_HINTS))
        has_hiring_signal = bool(jobs)

        if hint_hits >= 2:
            return True

        if has_clear_industry and (has_product_language or has_build_language or has_hiring_signal):
            return True

        if has_product_language and has_build_language:
            return True

        return False

    def _rule_based_company_classification(self, company_payload: Dict[str, Any]) -> tuple[str, float]:
        text = self._company_classification_text(company_payload)
        domain = str(company_payload.get("resolved_domain") or "").strip().lower()

        if self._is_aggregator_domain(domain):
            return "job_board", 0.95

        for classification in ("competitor", "staffing", "outsourcing", "consulting", "job_board", "marketplace"):
            keywords = CLASSIFICATION_RULE_KEYWORDS.get(classification, set())
            if any(keyword in text for keyword in keywords):
                confidence = 0.95 if classification in {"competitor", "job_board"} else 0.9
                return classification, confidence

        if self._has_end_client_classification_evidence(company_payload, text):
            return "end_client", 0.72

        if text.strip():
            return "unknown", 0.2

        return "unknown", 0.0

    def classify_company(self, company_payload: Dict[str, Any]) -> Dict[str, Any]:
        company_name = company_payload.get("company_display") or company_payload.get("company") or "unknown"

        system_prompt = """
Act as a Senior B2B Company Classification Analyst for Tekton Labs.

Classify the company using commercial evidence, not only keyword rules.

Return ONLY valid JSON with this exact schema:
{
  "company_name": "",
  "classification": "end_client|product_company|staffing|consulting|marketplace|job_board|competitor|unknown",
  "confidence": 0.0,
  "reason": "max 1 line"
}

Definitions:
- product_company: SaaS, software platform, workflow/product/AI platform, venture-backed or product-led company selling its own product.
- end_client: non-vendor company hiring for its own internal/product/IT teams.
- staffing: recruiting, staffing agency, talent acquisition, headhunting, staff augmentation seller.
- consulting: software consulting, outsourcing, nearshore services, systems integrator, professional services.
- marketplace: talent marketplace, freelance marketplace, contributor platform.
- job_board: job board, job aggregator, career portal/wrapper.
- competitor: company competing directly with Tekton Labs services.
- unknown: insufficient or conflicting evidence.

Rules:
- Prefer product_company for real SaaS/product/platform companies even when industry is missing.
- Do not classify real product companies as unknown only because Apollo/enrichment data is incomplete.
- Penalize/identify staffing, consulting, marketplaces, job boards, and competitors clearly.
- Use job descriptions, enrichment, LinkedIn, domain, tech stack, and hiring signals.
- Never hallucinate missing facts.
""".strip()

        user_prompt = f"""
Classify this company.

company_display: {company_payload.get("company_display") or ""}
company: {company_payload.get("company") or ""}
ai_company_gate_company_type: {company_payload.get("ai_company_gate_company_type") or ""}
ai_company_gate_relevance: {company_payload.get("ai_company_gate_relevance") or ""}
industry: {company_payload.get("industry") or ""}
company_size: {company_payload.get("company_size") or company_payload.get("employee_range") or ""}
resolved_domain: {company_payload.get("resolved_domain") or ""}
domain_validation_status: {company_payload.get("domain_validation_status") or ""}
linkedin_company_url: {company_payload.get("linkedin_company_url") or ""}
company_description: {self._truncate(company_payload.get("company_description") or "", 1800)}
jobs: {self._truncate(json.dumps(company_payload.get("jobs") or [], ensure_ascii=False), 5000)}

Return strict JSON only.
""".strip()

        try:
            result = self._chat_completion_json(system_prompt, user_prompt)
            classification = str(result.get("classification") or "unknown").strip().lower()
            if classification not in {
                "end_client",
                "product_company",
                "staffing",
                "consulting",
                "marketplace",
                "job_board",
                "competitor",
                "unknown",
            }:
                classification = "unknown"

            try:
                confidence = float(result.get("confidence", 0.0) or 0.0)
            except Exception:
                confidence = 0.0

            return {
                "company_name": str(result.get("company_name") or company_name).strip(),
                "classification": classification,
                "confidence": max(0.0, min(confidence, 1.0)),
                "provider": self.provider_name,
                "mode": "live_api",
                "reason": str(result.get("reason") or "").strip(),
            }
        except Exception:
            classification, confidence = self._rule_based_company_classification(company_payload)
            return {
                "company_name": company_name,
                "classification": classification,
                "confidence": confidence,
                "provider": self.provider_name,
                "mode": "fallback_heuristic_rules",
                "reason": "AI classification failed; fallback heuristic classification used.",
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

        strong_text_proof = any(
            marker in text
            for marker in (
                "official",
                "sitio oficial",
                "about us",
                "nosotros",
            )
        )
        weak_single_token_brand = (
            len(core_tokens) == 1
            and len(core_tokens[0]) <= 4
        )

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

        if (
            weak_single_token_brand
            and domain_hits >= 1
            and text_hits >= 1
            and total_hits <= 1
            and not strong_text_proof
        ):
            return {
                "selected_domain": domain,
                "decision": "review",
                "confidence": 0.62,
                "reason": "ambiguous_short_brand_match",
            }

        if domain_hits >= 1 and text_hits >= 1 and (len(core_tokens) >= 2 or strong_text_proof or total_hits >= 2):
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
