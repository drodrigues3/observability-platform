import time
from unittest.mock import MagicMock, patch

import pytest

from processor.config import Config
from processor.alerter import AlertPublisher
from processor.rules import RuleViolation


@pytest.fixture
def config():
    return Config(alert_cooldown_seconds=300)


@pytest.fixture
def mock_kafka_producer():
    with patch("processor.alerter.Producer") as MockProducer:
        mock = MockProducer.return_value
        mock.produce = MagicMock()
        mock.poll = MagicMock()
        mock.flush = MagicMock()
        yield mock


@pytest.fixture
def alerter(config, mock_kafka_producer):
    with patch("processor.alerter.Producer", return_value=mock_kafka_producer):
        return AlertPublisher(config)


@pytest.fixture
def violation():
    return RuleViolation(
        rule_name="HighLatencyP99",
        service="api-service",
        severity="warning",
        value=750.0,
        threshold=500.0,
        message="P99 latency 750.0ms exceeds threshold 500.0ms",
    )


class TestAlertPublisher:
    def test_publish_success(self, alerter, mock_kafka_producer, violation):
        result = alerter.publish(violation)
        assert result is True
        mock_kafka_producer.produce.assert_called_once()
        call_kwargs = mock_kafka_producer.produce.call_args[1]
        assert call_kwargs["topic"] == "alerts.fired"

    def test_fingerprint_format(self, alerter, violation):
        fp = alerter._fingerprint(violation)
        assert fp == "HighLatencyP99:api-service"

    def test_cooldown_suppresses_duplicate(self, alerter, mock_kafka_producer, violation):
        alerter.publish(violation)
        # Second publish within cooldown should be suppressed
        result = alerter.publish(violation)
        assert result is False
        assert mock_kafka_producer.produce.call_count == 1

    def test_cooldown_expires(self, alerter, mock_kafka_producer, violation):
        alerter.publish(violation)
        # Fast-forward past cooldown
        fp = alerter._fingerprint(violation)
        alerter._active_alerts[fp] = time.time() - 301
        result = alerter.publish(violation)
        assert result is True
        assert mock_kafka_producer.produce.call_count == 2

    def test_different_alerts_not_suppressed(self, alerter, mock_kafka_producer, violation):
        alerter.publish(violation)
        other = RuleViolation(
            rule_name="HighErrorRate",
            service="api-service",
            severity="critical",
            value=0.10,
            threshold=0.05,
            message="Error rate 10.0% exceeds threshold 5.0%",
        )
        result = alerter.publish(other)
        assert result is True
        assert mock_kafka_producer.produce.call_count == 2

    def test_kafka_error_returns_false(self, alerter, mock_kafka_producer, violation):
        from confluent_kafka import KafkaException

        mock_kafka_producer.produce.side_effect = KafkaException(
            MagicMock(str=lambda self: "Connection refused")
        )
        result = alerter.publish(violation)
        assert result is False

    def test_close_flushes(self, alerter, mock_kafka_producer):
        alerter.close()
        mock_kafka_producer.flush.assert_called_once_with(timeout=10)
