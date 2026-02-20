import json
import time
from datetime import datetime, timezone
from typing import Dict

import structlog
from confluent_kafka import Producer, KafkaException

from processor.config import Config
from processor.rules import RuleViolation

logger = structlog.get_logger(__name__)


class AlertPublisher:
    """Publishes alert events to Kafka with deduplication and cooldown."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._active_alerts: Dict[str, float] = {}  # fingerprint -> last_fired_time
        self._producer = Producer({
            "bootstrap.servers": config.kafka_brokers,
            "acks": "all",
            "client.id": "stream-processor-alerter",
        })

    def _fingerprint(self, violation: RuleViolation) -> str:
        return f"{violation.rule_name}:{violation.service}"

    def publish(self, violation: RuleViolation) -> bool:
        """Publish an alert, respecting cooldown window for deduplication."""
        fingerprint = self._fingerprint(violation)
        now = time.time()
        last_fired = self._active_alerts.get(fingerprint, 0)

        if now - last_fired < self._config.alert_cooldown_seconds:
            logger.debug("Alert suppressed by cooldown", fingerprint=fingerprint)
            return False

        alert_payload = {
            "alert_name": violation.rule_name,
            "service": violation.service,
            "severity": violation.severity,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "fingerprint": fingerprint,
            "labels": {
                "service": violation.service,
                "alertname": violation.rule_name,
                "severity": violation.severity,
            },
            "annotations": {
                "summary": violation.message,
                "value": str(round(violation.value, 4)),
                "threshold": str(violation.threshold),
            },
        }

        try:
            self._producer.produce(
                topic=self._config.alerts_topic,
                key=fingerprint.encode("utf-8"),
                value=json.dumps(alert_payload).encode("utf-8"),
            )
            self._producer.poll(0)
            self._active_alerts[fingerprint] = now
            logger.info(
                "Alert published",
                alert_name=violation.rule_name,
                service=violation.service,
                severity=violation.severity,
            )
            return True
        except KafkaException as e:
            logger.error("Failed to publish alert", error=str(e))
            return False

    def close(self) -> None:
        self._producer.flush(timeout=10)
