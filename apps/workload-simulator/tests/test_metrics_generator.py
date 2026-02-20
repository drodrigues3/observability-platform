import threading
from unittest.mock import MagicMock

import pytest

from simulator.config import Config
from simulator.metrics import MetricsGenerator, ENDPOINTS, NORMAL_LATENCY_MS


@pytest.fixture
def config():
    return Config(events_per_second=100, error_rate=0.0, latency_spike_probability=0.0)


@pytest.fixture
def mock_producer():
    producer = MagicMock()
    producer.publish_metric = MagicMock(return_value=True)
    producer.publish_log = MagicMock(return_value=True)
    return producer


@pytest.fixture
def generator(config, mock_producer):
    return MetricsGenerator(config, mock_producer)


class TestMetricsGenerator:
    def test_generate_normal_latency(self, generator):
        for service, (lo, hi) in NORMAL_LATENCY_MS.items():
            for _ in range(50):
                latency = generator._generate_latency(service, is_spike=False)
                assert lo <= latency <= hi * 2

    def test_generate_spike_latency(self, generator):
        for service, (lo, hi) in NORMAL_LATENCY_MS.items():
            for _ in range(20):
                latency = generator._generate_latency(service, is_spike=True)
                assert latency >= hi * 3

    def test_generate_status_code_success(self, generator):
        for _ in range(50):
            code = generator._generate_status_code(is_error=False)
            assert code in (200, 201, 204)

    def test_generate_status_code_error(self, generator):
        for _ in range(50):
            code = generator._generate_status_code(is_error=True)
            assert code in (500, 502, 503, 429, 400)

    def test_emit_event_publishes_metric(self, generator, mock_producer):
        generator._emit_event("api-service")
        mock_producer.publish_metric.assert_called_once()
        event = mock_producer.publish_metric.call_args[0][0]
        assert event.service == "api-service"
        assert event.endpoint in ENDPOINTS["api-service"]

    def test_emit_error_event_publishes_log(self, mock_producer):
        config = Config(error_rate=1.0, latency_spike_probability=0.0)
        gen = MetricsGenerator(config, mock_producer)
        gen._emit_event("api-service")
        mock_producer.publish_metric.assert_called_once()
        mock_producer.publish_log.assert_called_once()
        log_event = mock_producer.publish_log.call_args[0][0]
        assert log_event.level == "ERROR"

    def test_run_service_respects_stop_event(self, generator, mock_producer):
        stop = threading.Event()
        stop.set()  # Stop immediately
        generator.run_service("api-service", stop)
        # Should exit without producing anything
        mock_producer.publish_metric.assert_not_called()

    def test_unknown_service_uses_default_latency(self, generator):
        latency = generator._generate_latency("unknown-service", is_spike=False)
        # Default range is (50, 200)
        assert 50 <= latency <= 400

    def test_unknown_service_uses_default_endpoint(self, generator, mock_producer):
        generator._emit_event("unknown-service")
        event = mock_producer.publish_metric.call_args[0][0]
        assert event.endpoint == "/"

    def test_endpoints_coverage(self):
        assert "api-service" in ENDPOINTS
        assert "auth-service" in ENDPOINTS
        assert "payment-service" in ENDPOINTS
        assert "user-service" in ENDPOINTS
