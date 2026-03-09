from __future__ import annotations

from dataclasses import dataclass


class BudgetExceededError(RuntimeError):
    pass


@dataclass
class BudgetGuard:
    provider: str
    max_calls: int
    used_calls: int = 0

    def allow(self, amount: int = 1) -> bool:
        return (self.used_calls + amount) <= self.max_calls

    def consume(self, amount: int = 1) -> None:
        if not self.allow(amount):
            raise BudgetExceededError(
                f"Budget exceeded for provider={self.provider} max_calls={self.max_calls} used_calls={self.used_calls}"
            )
        self.used_calls += amount

    def remaining(self) -> int:
        return max(self.max_calls - self.used_calls, 0)
