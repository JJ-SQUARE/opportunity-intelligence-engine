from oie.providers.adapters.openai_adapter import OpenAIAdapter


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

