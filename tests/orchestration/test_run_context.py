from oie.orchestration.run_context import RunContext


def test_run_context_create_generates_unique_run_ids():
    ctx1 = RunContext.create(config={}, flags={})
    ctx2 = RunContext.create(config={}, flags={})

    assert ctx1.run_id != ctx2.run_id
    assert "T" in ctx1.run_date
    assert "T" in ctx2.run_date
