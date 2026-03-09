from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CircuitBreaker:
    provider: str
    failure_count: int = 0
    is_open: bool = False
    failure_threshold: int = 3

    def can_execute(self) -> bool:
        return not self.is_open

    def record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            self.is_open = True

    def record_success(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.failure_count = 0
        self.is_open = False
