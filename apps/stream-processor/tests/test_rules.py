import time

import pytest

from processor.state import ServiceWindow, MetricSample
from processor.rules import HighLatencyRule, HighErrorRateRule, TrafficDropRule


def make_window(latencies: list[float], errors: list[bool] | None = None) -> ServiceWindow:
    """Helper: build a ServiceWindow from lists of latencies and error flags."""
    window = ServiceWindow()
    if errors is None:
        errors = [False] * len(latencies)
    now = time.time()
    for i, (lat, err) in enumerate(zip(latencies, errors)):
        window.samples.append(MetricSample(timestamp=now - len(latencies) + i, latency_ms=lat, error=err))
    return window


class TestHighLatencyRule:
    def test_no_violation_under_threshold(self):
        rule = HighLatencyRule(threshold_ms=500.0)
        window = make_window([100, 200, 150, 300, 250])
        result = rule.evaluate("api-service", window)
        assert result is None

    def test_violation_above_threshold(self):
        rule = HighLatencyRule(threshold_ms=500.0)
        # All high latencies -> P99 well above 500
        window = make_window([600, 700, 800, 900, 1000])
        result = rule.evaluate("api-service", window)
        assert result is not None
        assert result.rule_name == "HighLatencyP99"
        assert result.severity == "warning"
        assert result.value >= 500.0

    def test_empty_window(self):
        rule = HighLatencyRule(threshold_ms=500.0)
        window = ServiceWindow()
        assert rule.evaluate("api-service", window) is None

    def test_threshold_boundary(self):
        rule = HighLatencyRule(threshold_ms=500.0)
        # Exactly at threshold — should NOT fire (> not >=)
        window = make_window([500.0] * 100)
        result = rule.evaluate("api-service", window)
        assert result is None


class TestHighErrorRateRule:
    def test_no_violation_under_threshold(self):
        rule = HighErrorRateRule(threshold=0.05)
        errors = [False] * 98 + [True, True]  # 2% error rate
        window = make_window([100] * 100, errors)
        assert rule.evaluate("api-service", window) is None

    def test_violation_above_threshold(self):
        rule = HighErrorRateRule(threshold=0.05)
        errors = [False] * 90 + [True] * 10  # 10% error rate
        window = make_window([100] * 100, errors)
        result = rule.evaluate("api-service", window)
        assert result is not None
        assert result.rule_name == "HighErrorRate"
        assert result.severity == "critical"
        assert result.value == pytest.approx(0.10)

    def test_empty_window(self):
        rule = HighErrorRateRule(threshold=0.05)
        window = ServiceWindow()
        assert rule.evaluate("api-service", window) is None

    def test_all_errors(self):
        rule = HighErrorRateRule(threshold=0.05)
        window = make_window([100] * 10, [True] * 10)
        result = rule.evaluate("api-service", window)
        assert result is not None
        assert result.value == 1.0


class TestTrafficDropRule:
    def test_first_evaluation_sets_baseline(self):
        rule = TrafficDropRule(threshold=0.5, window_size=60)
        window = make_window([100] * 60)
        result = rule.evaluate("api-service", window)
        assert result is None
        assert window.baseline_rps is not None

    def test_no_violation_stable_traffic(self):
        rule = TrafficDropRule(threshold=0.5, window_size=60)
        window = make_window([100] * 60)
        window.baseline_rps = 1.0  # 1 RPS baseline
        result = rule.evaluate("api-service", window)
        assert result is None

    def test_violation_on_traffic_drop(self):
        rule = TrafficDropRule(threshold=0.5, window_size=60)
        window = make_window([100] * 10)
        window.baseline_rps = 10.0  # baseline 10 RPS, current ~0.17 RPS
        result = rule.evaluate("api-service", window)
        assert result is not None
        assert result.rule_name == "TrafficDrop"
        assert result.severity == "warning"

    def test_baseline_ema_update(self):
        rule = TrafficDropRule(threshold=0.5, window_size=60)
        window = make_window([100] * 60)
        # Set baseline different from actual RPS (60/60=1.0) so EMA moves
        window.baseline_rps = 2.0
        rule.evaluate("api-service", window)
        # baseline should be updated via EMA: 2.0 * 0.95 + 1.0 * 0.05 = 1.95
        assert window.baseline_rps != 2.0
        assert window.baseline_rps == pytest.approx(1.95)

    def test_empty_window(self):
        rule = TrafficDropRule(threshold=0.5, window_size=60)
        window = ServiceWindow()
        window.baseline_rps = 10.0
        assert rule.evaluate("api-service", window) is None
