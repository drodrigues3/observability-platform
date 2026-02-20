from collections import deque
from unittest.mock import MagicMock, patch

import pytest

from simulator.config import Config
from simulator.models import MetricEvent, LogEvent
from simulator.producer import KafkaProducerWrapper


@pytest.fixture
def config():
    return Config()


@pytest.fixture
def mock_producer():
    with patch("simulator.producer.Producer") as MockProducer:
        mock = MockProducer.return_value
        mock.produce = MagicMock()
        mock.poll = MagicMock()
        mock.flush = MagicMock()
        yield mock


@pytest.fixture
def wrapper(config, mock_producer):
    with patch("simulator.producer.Producer", return_value=mock_producer):
        return KafkaProducerWrapper(config)


@pytest.fixture
def sample_metric():
    return MetricEvent(
        service="api-service",
        latency_ms=100.0,
        status_code=200,
        endpoint="/api/v1/users",
        region="us-east-1",
        error=False,
    )


@pytest.fixture
def sample_log():
    return LogEvent(
        service="api-service",
        level="ERROR",
        message="Request failed with status 500",
    )


class TestKafkaProducerWrapper:
    def test_publish_metric_success(self, wrapper, mock_producer, sample_metric):
        result = wrapper.publish_metric(sample_metric)
        assert result is True
        mock_producer.produce.assert_called_once()
        call_kwargs = mock_producer.produce.call_args
        assert call_kwargs[1]["topic"] == "metrics.raw"
        assert call_kwargs[1]["key"] == b"api-service"

    def test_publish_log_success(self, wrapper, mock_producer, sample_log):
        result = wrapper.publish_log(sample_log)
        assert result is True
        mock_producer.produce.assert_called_once()
        call_kwargs = mock_producer.produce.call_args
        assert call_kwargs[1]["topic"] == "logs.raw"

    def test_publish_metric_kafka_error_retries(self, wrapper, mock_producer, sample_metric):
        from confluent_kafka import KafkaException

        mock_producer.produce.side_effect = KafkaException(
            MagicMock(str=lambda self: "Broker unavailable")
        )
        result = wrapper.publish_metric(sample_metric)
        assert result is False
        # Should have retried producer_retry_max times + original attempt
        assert mock_producer.produce.call_count == wrapper._config.producer_retry_max + 1

    def test_dlq_on_max_retries(self, wrapper, mock_producer, sample_metric):
        from confluent_kafka import KafkaException

        mock_producer.produce.side_effect = KafkaException(
            MagicMock(str=lambda self: "Broker unavailable")
        )
        wrapper.publish_metric(sample_metric)
        assert wrapper.get_dlq_size() == 1

    def test_flush(self, wrapper, mock_producer):
        wrapper.flush(timeout=5)
        mock_producer.flush.assert_called_once_with(5)

    def test_close_flushes(self, wrapper, mock_producer):
        wrapper.close()
        mock_producer.flush.assert_called_once()

    def test_dlq_bounded_size(self, wrapper):
        assert wrapper._dlq.maxlen == 1000
