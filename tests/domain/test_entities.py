from oie.domain.entities import (
    CompanyProfile,
    Decision,
    DecisionHistory,
    Evidence,
    JobPosting,
    OpportunityCandidate,
    OpportunityScore,
)
def test_opportunity_candidate_accepts_core_domain_entities():
    job = JobPosting(
        title="Senior Python Engineer",
        company="Acme",
        job_url="https://example.com/jobs/1",
        source="test",
    )
    company = CompanyProfile(
        company_display="Acme",
        company_normalized="acme",
        resolved_domain="acme.com",
    )
    evidence = Evidence(source="job_posting", value="Hiring senior Python engineers")
    score = OpportunityScore(score=87.5, label="high", reasons=["Strong hiring signal"])
    decision = Decision(
        stage="company_gate",
        decision="accepted",
        confidence=0.92,
        reason="Real hiring company",
        evidence=[evidence],
    )
    candidate = OpportunityCandidate(
        id="opp_1",
        source_job=job,
        company=company,
        evidence=[evidence],
        scores=[score],
    )
    candidate.decision_history.add(decision)
    assert candidate.id == "opp_1"
    assert candidate.source_job is job
    assert candidate.company is company
    assert candidate.evidence == [evidence]
    assert candidate.scores == [score]
    assert candidate.decision_history.decisions == [decision]
def test_decision_history_starts_empty_and_accumulates_decisions():
    history = DecisionHistory()
    decision = Decision(
        stage="freshness_gate",
        decision="rejected",
        confidence=0.7,
        reason="Job posting appears stale",
    )
    history.add(decision)
    assert history.decisions == [decision]
