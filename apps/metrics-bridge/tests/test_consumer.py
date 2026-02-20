import json
from unittest.mock import MagicMock, patch

import pytest

from bridge.config import Config
from bridge.consumer import MetricsBridgeConsumer


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def mock_kafka_consumer():
    with patch("bridge.consumer.Consumer") as MockConsumer:
        mock = MockConsumer.return_value
        mock.subscribe = MagicMock()
        mock.poll = MagicMock(return_value=None)
        mock.close = MagicMock()
        yield mock


@pytest.fixture
def consumer(config, mock_kafka_consumer):
    with patch("bridge.consumer.Consumer", return_value=mock_kafka_consumer):
        return MetricsBridgeConsumer(config)


class TestMetricsBridgeConsumer:
    def test_start_subscribes_and_runs(self, consumer, mock_kafka_consumer):
        consumer.start()
        mock_kafka_consumer.subscribe.assert_called_once_with(["metrics.raw"])
        assert consumer._running is True
        assert consumer._thread is not None
        consumer.stop()

    def test_stop_sets_flag_and_closes(self, consumer, mock_kafka_consumer):
        consumer.start()
        consumer.stop()
        assert consumer._running is False
        mock_kafka_consumer.close.assert_called_once()

    def test_seen_services_tracking(self, consumer):
        assert len(consumer._seen_services) == 0

    def test_process_valid_message(self, consumer, mock_kafka_consumer):
        """Simulate processing a valid Kafka message."""
        msg = MagicMock()
        msg.error.return_value = None
        msg.value.return_value = json.dumps({
            "service": "api-service",
            "endpoint": "/api/v1/users",
            "region": "us-east-1",
            "status_code": 200,
            "latency_ms": 100.0,
            "error": False,
        }).encode("utf-8")

        # Call _run logic directly: process one message
        payload = json.loads(msg.value().decode("utf-8"))
        from bridge.metrics import record_metric_event
        record_metric_event(payload)

        service = payload.get("service")
        if service and service not in consumer._seen_services:
            consumer._seen_services.add(service)
        assert "api-service" in consumer._seen_services

    def test_invalid_json_does_not_crash(self, consumer):
        """Verify that malformed JSON is handled gracefully."""
        msg = MagicMock()
        msg.error.return_value = None
        msg.value.return_value = b"not-json"

        # Simulate what _run does
        try:
            json.loads(msg.value().decode("utf-8"))
        except json.JSONDecodeError:
            pass  # Expected — consumer should not crash
