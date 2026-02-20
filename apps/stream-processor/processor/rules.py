from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from processor.state import ServiceWindow


@dataclass
class RuleViolation:
    rule_name: str
    service: str
    severity: str
    value: float
    threshold: float
    message: str


class Rule(ABC):
    @abstractmethod
    def evaluate(self, service: str, window: ServiceWindow) -> Optional[RuleViolation]:
        ...


class HighLatencyRule(Rule):
    """Fires when P99 latency exceeds threshold."""

    def __init__(self, threshold_ms: float) -> None:
        self._threshold = threshold_ms

    def evaluate(self, service: str, window: ServiceWindow) -> Optional[RuleViolation]:
        p99 = window.get_p99_latency()
        if p99 is not None and p99 > self._threshold:
            return RuleViolation(
                rule_name="HighLatencyP99",
                service=service,
                severity="warning",
                value=p99,
                threshold=self._threshold,
                message=f"P99 latency {p99:.1f}ms exceeds threshold {self._threshold}ms",
            )
        return None


class HighErrorRateRule(Rule):
    """Fires when error rate exceeds threshold."""

    def __init__(self, threshold: float) -> None:
        self._threshold = threshold

    def evaluate(self, service: str, window: ServiceWindow) -> Optional[RuleViolation]:
        error_rate = window.get_error_rate()
        if error_rate is not None and error_rate > self._threshold:
            return RuleViolation(
                rule_name="HighErrorRate",
                service=service,
                severity="critical",
                value=error_rate,
                threshold=self._threshold,
                message=f"Error rate {error_rate:.1%} exceeds threshold {self._threshold:.1%}",
            )
        return None


class TrafficDropRule(Rule):
    """Fires when RPS drops more than threshold% vs baseline."""

    def __init__(self, threshold: float, window_size: int) -> None:
        self._threshold = threshold
        self._window_size = window_size

    def evaluate(self, service: str, window: ServiceWindow) -> Optional[RuleViolation]:
        current_rps = window.get_rps(self._window_size)
        if current_rps is None:
            return None

        baseline = window.baseline_rps
        if baseline is None:
            window.baseline_rps = current_rps
            return None

        drop = (baseline - current_rps) / baseline if baseline > 0 else 0.0
        if drop > self._threshold:
            return RuleViolation(
                rule_name="TrafficDrop",
                service=service,
                severity="warning",
                value=drop,
                threshold=self._threshold,
                message=f"RPS dropped {drop:.1%} from baseline {baseline:.1f} to {current_rps:.1f}",
            )

        # Gradually update baseline using exponential moving average
        window.baseline_rps = baseline * 0.95 + current_rps * 0.05
        return None
