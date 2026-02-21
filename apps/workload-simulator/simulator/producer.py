import time
from collections import deque
from typing import Any, Optional, Union

import structlog
from confluent_kafka import KafkaException, Message, Producer

from simulator.config import Config
from simulator.models import MetricEvent, LogEvent

logger = structlog.get_logger(__name__)


class KafkaProducerWrapper:
    """Kafka producer with retry logic and dead-letter queue."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._dlq: deque[MetricEvent] = deque(maxlen=1000)
        self._producer = self._create_producer()

    def _create_producer(self) -> Producer:
        conf: dict[str, Union[str, int, float, bool]] = {
            "bootstrap.servers": self._config.kafka_brokers,
            "acks": "all",
            "retries": self._config.producer_retry_max,
            "retry.backoff.ms": 500,
            "delivery.timeout.ms": 30000,
            "enable.idempotence": True,
            "client.id": "workload-simulator",
        }
        return Producer(conf)

    def _delivery_callback(self, err: Any, msg: Message) -> None:
        if err:
            logger.error(
                "Message delivery failed",
                topic=msg.topic(),
                error=str(err),
            )
        else:
            logger.debug(
                "Message delivered",
                topic=msg.topic(),
                partition=msg.partition(),
                offset=msg.offset(),
            )

    def publish_metric(self, event: MetricEvent, retries: int = 0) -> bool:
        """Publish a MetricEvent to Kafka with retry logic."""
        try:
            self._producer.produce(
                topic=self._config.metrics_topic,
                key=event.service.encode("utf-8"),
                value=event.model_dump_json().encode("utf-8"),
                on_delivery=self._delivery_callback,
            )
            self._producer.poll(0)
            logger.debug("Published metric event", service=event.service, latency_ms=event.latency_ms)
            return True
        except KafkaException as e:
            if retries < self._config.producer_retry_max:
                logger.warning("Retrying message publish", attempt=retries + 1, error=str(e))
                time.sleep(0.5 * (retries + 1))
                return self.publish_metric(event, retries + 1)
            else:
                logger.error("Max retries exceeded, sending to DLQ", error=str(e))
                self._dlq.append(event)
                return False

    def publish_log(self, event: LogEvent) -> bool:
        """Publish a LogEvent to Kafka."""
        try:
            self._producer.produce(
                topic=self._config.logs_topic,
                key=event.service.encode("utf-8"),
                value=event.model_dump_json().encode("utf-8"),
                on_delivery=self._delivery_callback,
            )
            self._producer.poll(0)
            return True
        except KafkaException as e:
            logger.error("Failed to publish log event", error=str(e))
            return False

    def flush(self, timeout: Optional[int] = None) -> None:
        timeout = timeout or self._config.producer_flush_timeout
        self._producer.flush(timeout)

    def get_dlq_size(self) -> int:
        return len(self._dlq)

    def close(self) -> None:
        self.flush()
        logger.info("Producer closed", dlq_size=self.get_dlq_size())
