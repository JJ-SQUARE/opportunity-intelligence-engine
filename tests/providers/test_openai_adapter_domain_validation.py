from oie.providers.adapters.openai_adapter import OpenAIAdapter


def test_openai_adapter_analyze_job_intelligence_normalizes_ai_response():
    adapter = OpenAIAdapter()

    def fake_chat(system_prompt, user_prompt):
        assert "Job Intelligence Analyst" in system_prompt
        assert "Senior Backend Engineer" in user_prompt
        return {
            "is_real_job": True,
            "is_contaminated": False,
            "real_company_name": "Acme",
            "confidence": 1.4,
            "usable_for_scoring": True,
            "role": "Backend Engineer",
            "seniority": "Senior",
            "tech_stack": ["Python", "AWS", ""],
            "budget": "USD $5,000",
            "workplace_type": "remote",
            "commercial_signals": ["cloud modernization"],
        }

    adapter._chat_completion_json = fake_chat
    result = adapter.analyze_job_intelligence(
        {
            "source": "linkedin_serpapi",
            "title": "Senior Backend Engineer",
            "company": "Acme",
            "description": "Python and AWS role.",
        }
    )

    assert result["is_real_job"] is True
    assert result["is_contaminated"] is False
    assert result["real_company_name"] == "Acme"
    assert result["confidence"] == 1.0
    assert result["usable_for_scoring"] is True
    assert result["tech_stack"] == ["Python", "AWS"]
    assert result["job_intelligence_provider"] == "openai"
    assert result["job_intelligence_mode"] == "live_api"


def test_openai_adapter_resolve_company_identity_normalizes_ai_response():
    adapter = OpenAIAdapter()

    def fake_chat(system_prompt, user_prompt):
        assert "Company Identity Analyst" in system_prompt
        assert "Wrong Wrapper" in user_prompt
        return {
            "company_name": "Acme Inc.",
            "source": "job_intelligence",
            "confidence": 1.5,
            "is_contaminated": False,
            "is_ambiguous": False,
            "usable_for_commercial": True,
            "reason": "AI job intelligence identifies Acme as the hiring company.",
        }

    adapter._chat_completion_json = fake_chat
    result = adapter.resolve_company_identity(
        {
            "company_display": "Wrong Wrapper",
            "company": "Wrong Wrapper",
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "job_intelligence": {
                        "real_company_name": "Acme Inc.",
                        "confidence": 0.91,
                    },
                }
            ],
        }
    )

    assert result["company_name"] == "Acme Inc."
    assert result["source"] == "job_intelligence"
    assert result["confidence"] == 1.0
    assert result["usable_for_commercial"] is True
    assert result["provider"] == "openai"
    assert result["mode"] == "live_api"


def test_validate_domain_candidates_accepts_clear_brand_match():
    adapter = OpenAIAdapter()

    result = adapter.validate_domain_candidates(
        {
            "company_name": "Sofka Technologies",
            "candidates": [
                {
                    "domain": "sofka.com.co",
                    "source": "serpapi_fallback",
                    "title": "Sofka official site",
                    "snippet": "Technology company official website",
                    "serp_rank": 1,
                }
            ],
        }
    )

    assert result["decision"] == "accepted"
    assert result["selected_domain"] == "sofka.com.co"
    assert result["confidence"] >= 0.8


def test_validate_domain_candidates_rejects_aggregator_domain():
    adapter = OpenAIAdapter()

    result = adapter.validate_domain_candidates(
        {
            "company_name": "Tenaris",
            "candidates": [
                {
                    "domain": "jobgether.com",
                    "source": "apply_url",
                    "title": "Tenaris job posting",
                    "snippet": "Apply now on Jobgether",
                    "serp_rank": None,
                }
            ],
        }
    )

    assert result["decision"] == "rejected"
    assert result["selected_domain"] is None


def test_validate_domain_candidates_reviews_partial_match():
    adapter = OpenAIAdapter()

    result = adapter.validate_domain_candidates(
        {
            "company_name": "Digital Solutions 324 SL",
            "candidates": [
                {
                    "domain": "digitalsolutions.com.sv",
                    "source": "serpapi_fallback",
                    "title": "Digital Solutions",
                    "snippet": "Business technology solutions",
                    "serp_rank": 1,
                }
            ],
        }
    )

    assert result["decision"] in {"review", "accepted"}

def test_validate_domain_candidates_reviews_suspicious_beta_subdomain():
    adapter = OpenAIAdapter()

    result = adapter.validate_domain_candidates(
        {
            "company_name": "Rimutee",
            "candidates": [
                {
                    "domain": "beta.rimutee.com",
                    "source": "serpapi_fallback",
                    "title": "Rimutee - Official Website",
                    "snippet": "Remote talent platform",
                    "serp_rank": 1,
                }
            ],
        }
    )

    assert result["decision"] == "review"
    assert result["selected_domain"] == "beta.rimutee.com"
    assert result["reason"] == "suspicious_subdomain"

def test_validate_domain_candidates_reviews_ambiguous_short_single_token_brand():
    adapter = OpenAIAdapter()

    result = adapter.validate_domain_candidates(
        {
            "company_name": "NOUS",
            "candidates": [
                {
                    "domain": "nous.example.com",
                    "source": "serpapi_fallback",
                    "title": "NOUS platform",
                    "snippet": "Innovation platform",
                    "serp_rank": 1,
                }
            ],
        }
    )

    assert result["decision"] == "review"
    assert result["selected_domain"] == "nous.example.com"
    assert result["reason"] == "ambiguous_short_brand_match"

def test_openai_adapter_validate_company_enrichment_normalizes_ai_response():
    adapter = OpenAIAdapter()

    def fake_chat(system_prompt, user_prompt):
        assert "Company Data Validation Analyst" in system_prompt
        assert "Apollo enrichment" in user_prompt
        assert "Acme Inc." in user_prompt
        return {
            "is_match": True,
            "confidence": 1.4,
            "decision": "accepted",
            "reason": "Apollo domain and company data match Acme.",
        }

    adapter._chat_completion_json = fake_chat
    result = adapter.validate_company_enrichment(
        {
            "company_display": "Acme Inc.",
            "resolved_domain": "acme.com",
            "apollo_enrichment": {
                "organization": {
                    "name": "Acme Inc.",
                    "website_url": "https://acme.com",
                    "industry": "Software",
                }
            },
        }
    )

    assert result["enrichment_ai_match"] is True
    assert result["enrichment_ai_confidence"] == 1.0
    assert result["enrichment_ai_decision"] == "accepted"
    assert result["enrichment_ai_reason"] == "Apollo domain and company data match Acme."
    assert result["enrichment_ai_provider"] == "openai"
    assert result["enrichment_ai_mode"] == "live_api"

def test_openai_adapter_generate_buyer_personas_normalizes_ai_response():
    adapter = OpenAIAdapter()

    def fake_chat(system_prompt, user_prompt):
        assert "B2B Buyer Persona Analyst" in system_prompt
        assert "Acme Inc." in user_prompt
        return {
            "buyer_personas": [
                {
                    "persona": "Engineering Leadership",
                    "priority": "high",
                    "rationale": "Owns software delivery and technical staffing needs.",
                    "target_titles": ["CTO", "VP Engineering", ""],
                    "title_search_patterns": ["engineering leadership", "software delivery leadership", ""],
                    "pain_alignment": "Multiple senior engineering roles suggest delivery capacity needs.",
                    "recommended_channel": "multi_channel",
                }
            ],
            "reason": "Engineering leadership is the strongest entry point.",
        }

    adapter._chat_completion_json = fake_chat
    result = adapter.generate_buyer_personas(
        {
            "company_display": "Acme Inc.",
            "industry": "Software",
            "company_size": "51-200",
            "opportunity_score": 72,
            "jobs": [{"title": "Senior Backend Engineer"}],
        }
    )

    assert result["buyer_personas_ai"][0]["persona"] == "Engineering Leadership"
    assert result["buyer_personas_ai"][0]["priority"] == "high"
    assert result["buyer_personas_ai"][0]["target_titles"] == ["CTO", "VP Engineering"]
    assert result["buyer_personas_ai"][0]["suggested_titles"] == ["CTO", "VP Engineering"]
    assert result["buyer_personas_ai"][0]["title_search_patterns"] == ["engineering leadership", "software delivery leadership"]
    assert result["buyer_personas_ai"][0]["pain_alignment"] == "Multiple senior engineering roles suggest delivery capacity needs."
    assert result["buyer_personas_ai"][0]["recommended_channel"] == "multi_channel"
    assert result["buyer_personas_ai_reason"] == "Engineering leadership is the strongest entry point."
    assert result["buyer_personas_ai_provider"] == "openai"
    assert result["buyer_personas_ai_mode"] == "live_api"


def test_openai_adapter_score_lead_normalizes_ai_intelligence_fields():
    adapter = OpenAIAdapter()

    def fake_chat(system_prompt, user_prompt):
        assert "lead_role_type" in system_prompt
        assert "target_persona: Engineering Leadership" in user_prompt
        assert "pain_alignment: Strategic engineering hiring need." in user_prompt
        return {
            "lead_relevance_score": 91,
            "lead_priority_label": "high",
            "lead_decision_maker_score": 36,
            "lead_icp_fit_score": 28,
            "lead_contact_completeness_score": 18,
            "lead_penalty_negative_title": 0,
            "lead_role_type": "primary_decision_maker",
            "why_selected": "Owns engineering capacity decisions.",
            "outreach_angle": "Discuss senior delivery capacity for strategic hiring.",
            "expected_relevance": "high",
            "risk_or_uncertainty": "Exact budget ownership is not confirmed.",
            "lead_score_reason": "Strong persona fit and reachable channel.",
        }

    adapter._chat_completion_json = fake_chat
    result = adapter.score_lead(
        {
            "company_display": "Acme Inc.",
            "industry": "Software",
            "resolved_domain": "acme.com",
            "company_type_ai": "end_client",
            "opportunity_score": 82,
            "contact_name": "Jane Doe",
            "contact_title": "VP Engineering",
            "email": "jane@acme.com",
            "linkedin_url": "https://linkedin.com/in/jane",
            "lead_source": "apollo_people",
            "lead_confidence": 0.9,
            "email_quality_score": 95,
            "target_persona": "Engineering Leadership",
            "suggested_titles": "CTO, VP Engineering",
            "title_search_patterns": "engineering leadership",
            "search_reason": "Owns software delivery and staffing needs.",
            "pain_alignment": "Strategic engineering hiring need.",
            "priority": "high",
            "recommended_channel": "multi_channel",
        }
    )

    assert result["lead_relevance_score"] == 91
    assert result["lead_priority_label"] == "high"
    assert result["lead_role_type"] == "primary_decision_maker"
    assert result["why_selected"] == "Owns engineering capacity decisions."
    assert result["outreach_angle"] == "Discuss senior delivery capacity for strategic hiring."
    assert result["expected_relevance"] == "high"
    assert result["risk_or_uncertainty"] == "Exact budget ownership is not confirmed."
    assert result["lead_scoring_provider"] == "openai"
    assert result["lead_scoring_mode"] == "live_api"

