import time

from oie.collectors.base import BaseJobCollector
from oie.orchestration.run_context import RunContext
from oie.services.collector_runner_service import CollectorRunnerService


class SlowCollector(BaseJobCollector):

    def __init__(self, name):
        self.collector_name = name

    def collect(self):
        time.sleep(0.2)
        return [{"source": self.collector_name}]


def test_collectors_run_in_parallel():

    ctx = RunContext.create(config={}, flags={})

    runner = CollectorRunnerService(ctx)

    runner.register_collectors([
        SlowCollector("a"),
        SlowCollector("b"),
        SlowCollector("c"),
    ])

    start = time.time()

    jobs = runner.run_enabled_collectors(["a", "b", "c"])

    duration = time.time() - start

    assert len(jobs) == 3

    # si fuera secuencial sería ~0.6
    assert duration < 0.45
