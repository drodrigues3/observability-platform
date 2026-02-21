from typing import List

import structlog

from processor.config import Config
from processor.rules import Rule, RuleViolation, HighLatencyRule, HighErrorRateRule, TrafficDropRule
from processor.state import WindowState

logger = structlog.get_logger(__name__)


class AnomalyDetector:
    """Evaluates rules against sliding windows and returns violations."""

    def __init__(self, config: Config, state: WindowState) -> None:
        self._state = state
        self._rules: List[Rule] = [
            HighLatencyRule(config.latency_p99_threshold_ms),
            HighErrorRateRule(config.error_rate_threshold),
            TrafficDropRule(config.traffic_drop_threshold, config.window_size_seconds),
        ]
        self._consecutive_violations: dict[str, int] = {}
        self._required_consecutive = config.consecutive_windows_for_alert

    def record(self, service: str, latency_ms: float, error: bool) -> None:
        self._state.record(service, latency_ms, error)

    def detect(self) -> List[RuleViolation]:
        """Run all rules against all service windows, return confirmed violations."""
        violations = []
        for service in self._state.get_all_services():
            window = self._state.get_window(service)
            if window is None:
                continue
            for rule in self._rules:
                violation = rule.evaluate(service, window)
                key = f"{service}:{rule.__class__.__name__}"
                if violation:
                    count = self._consecutive_violations.get(key, 0) + 1
                    self._consecutive_violations[key] = count
                    if count >= self._required_consecutive:
                        violations.append(violation)
                        logger.warning(
                            "Anomaly detected",
                            rule=violation.rule_name,
                            service=service,
                            value=round(violation.value, 4),
                            threshold=violation.threshold,
                            consecutive_windows=count,
                        )
                else:
                    self._consecutive_violations[key] = 0
        return violations
