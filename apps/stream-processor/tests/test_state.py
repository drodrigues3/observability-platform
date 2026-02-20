import time

import pytest

from processor.state import MetricSample, ServiceWindow, WindowState


class TestMetricSample:
    def test_fields(self):
        sample = MetricSample(timestamp=1000.0, latency_ms=120.5, error=False)
        assert sample.timestamp == 1000.0
        assert sample.latency_ms == 120.5
        assert sample.error is False


class TestServiceWindow:
    def test_add_sample(self):
        window = ServiceWindow()
        window.add_sample(latency_ms=100.0, error=False)
        window.add_sample(latency_ms=200.0, error=True)
        assert len(window.samples) == 2

    def test_prune_removes_old_samples(self):
        window = ServiceWindow()
        now = time.time()
        # Add an old sample manually
        window.samples.append(MetricSample(timestamp=now - 120, latency_ms=100, error=False))
        # Add a recent sample
        window.samples.append(MetricSample(timestamp=now - 5, latency_ms=200, error=False))
        window.prune(window_seconds=60)
        assert len(window.samples) == 1
        assert window.samples[0].latency_ms == 200

    def test_get_p99_latency_empty(self):
        window = ServiceWindow()
        assert window.get_p99_latency() is None

    def test_get_p99_latency(self):
        window = ServiceWindow()
        # Add 100 samples: 0, 1, 2, ..., 99
        for i in range(100):
            window.samples.append(
                MetricSample(timestamp=time.time(), latency_ms=float(i), error=False)
            )
        p99 = window.get_p99_latency()
        assert p99 == 99.0  # idx = int(100 * 0.99) = 99

    def test_get_p99_latency_single_sample(self):
        window = ServiceWindow()
        window.add_sample(latency_ms=42.0, error=False)
        assert window.get_p99_latency() == 42.0

    def test_get_error_rate_empty(self):
        window = ServiceWindow()
        assert window.get_error_rate() is None

    def test_get_error_rate(self):
        window = ServiceWindow()
        for _ in range(8):
            window.add_sample(latency_ms=100, error=False)
        for _ in range(2):
            window.add_sample(latency_ms=100, error=True)
        assert window.get_error_rate() == pytest.approx(0.2)

    def test_get_error_rate_all_errors(self):
        window = ServiceWindow()
        for _ in range(5):
            window.add_sample(latency_ms=100, error=True)
        assert window.get_error_rate() == 1.0

    def test_get_rps_empty(self):
        window = ServiceWindow()
        assert window.get_rps(window_seconds=60) is None

    def test_get_rps(self):
        window = ServiceWindow()
        for _ in range(120):
            window.add_sample(latency_ms=100, error=False)
        assert window.get_rps(window_seconds=60) == pytest.approx(2.0)

    def test_maxlen_enforced(self):
        window = ServiceWindow()
        for i in range(15000):
            window.add_sample(latency_ms=float(i), error=False)
        assert len(window.samples) == 10000


class TestWindowState:
    def test_record_creates_window(self):
        state = WindowState(window_size_seconds=60)
        state.record("api-service", latency_ms=100, error=False)
        assert "api-service" in state.get_all_services()

    def test_record_multiple_services(self):
        state = WindowState(window_size_seconds=60)
        state.record("api-service", latency_ms=100, error=False)
        state.record("auth-service", latency_ms=50, error=False)
        assert set(state.get_all_services()) == {"api-service", "auth-service"}

    def test_get_window_existing(self):
        state = WindowState(window_size_seconds=60)
        state.record("api-service", latency_ms=100, error=False)
        window = state.get_window("api-service")
        assert window is not None
        assert len(window.samples) == 1

    def test_get_window_nonexistent(self):
        state = WindowState(window_size_seconds=60)
        assert state.get_window("missing") is None
