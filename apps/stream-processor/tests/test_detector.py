import pytest

from processor.config import Config
from processor.detector import AnomalyDetector
from processor.state import WindowState


@pytest.fixture
def config():
    return Config(
        latency_p99_threshold_ms=500.0,
        error_rate_threshold=0.05,
        traffic_drop_threshold=0.5,
        window_size_seconds=60,
        consecutive_windows_for_alert=2,
    )


@pytest.fixture
def state():
    return WindowState(window_size_seconds=60)


@pytest.fixture
def detector(config, state):
    return AnomalyDetector(config, state)


class TestAnomalyDetector:
    def test_no_violations_healthy_traffic(self, detector):
        for _ in range(100):
            detector.record("api-service", latency_ms=100.0, error=False)
        violations = detector.detect()
        assert len(violations) == 0

    def test_high_latency_requires_consecutive_windows(self, detector):
        for _ in range(100):
            detector.record("api-service", latency_ms=1000.0, error=False)
        # First detection: 1 consecutive violation — not enough (need 2)
        violations = detector.detect()
        assert len(violations) == 0
        # Second detection: 2 consecutive — should fire
        violations = detector.detect()
        latency_violations = [v for v in violations if v.rule_name == "HighLatencyP99"]
        assert len(latency_violations) == 1

    def test_high_error_rate_requires_consecutive_windows(self, detector):
        # All errors
        for _ in range(100):
            detector.record("api-service", latency_ms=100.0, error=True)
        detector.detect()  # 1st
        violations = detector.detect()  # 2nd
        error_violations = [v for v in violations if v.rule_name == "HighErrorRate"]
        assert len(error_violations) == 1
        assert error_violations[0].severity == "critical"

    def test_consecutive_counter_resets_on_healthy(self, detector):
        # Record unhealthy latency
        for _ in range(100):
            detector.record("api-service", latency_ms=1000.0, error=False)
        detector.detect()  # 1 consecutive

        # Now send healthy traffic and re-detect
        state = detector._state
        window = state.get_window("api-service")
        window.samples.clear()
        for _ in range(100):
            detector.record("api-service", latency_ms=50.0, error=False)
        violations = detector.detect()
        # Counter should have reset — no violations
        latency_violations = [v for v in violations if v.rule_name == "HighLatencyP99"]
        assert len(latency_violations) == 0

    def test_multiple_services_independent(self, detector):
        for _ in range(100):
            detector.record("api-service", latency_ms=1000.0, error=False)
            detector.record("auth-service", latency_ms=50.0, error=False)
        detector.detect()
        violations = detector.detect()
        # Only api-service should have latency violations
        services_with_violations = {v.service for v in violations}
        assert "api-service" in services_with_violations
        assert "auth-service" not in services_with_violations

    def test_record_delegates_to_state(self, detector, state):
        detector.record("api-service", latency_ms=150.0, error=False)
        window = state.get_window("api-service")
        assert window is not None
        assert len(window.samples) == 1
