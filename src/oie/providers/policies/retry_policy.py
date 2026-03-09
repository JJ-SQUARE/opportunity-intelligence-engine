from __future__ import annotations

from dataclasses import dataclass


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    base_delay_seconds: float = 0.25
    backoff_multiplier: float = 2.0

    def get_delay(self, attempt_number: int) -> float:
        if attempt_number <= 1:
            return 0.0
        return self.base_delay_seconds * (self.backoff_multiplier ** (attempt_number - 2))
