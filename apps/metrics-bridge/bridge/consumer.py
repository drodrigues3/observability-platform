import json
import threading

import structlog
from confluent_kafka import Consumer, KafkaError

from bridge.config import Config
from bridge.metrics import record_metric_event, ACTIVE_SERVICES

logger = structlog.get_logger(__name__)


class MetricsBridgeConsumer:
    """Background Kafka consumer that updates Prometheus metrics."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._consumer = Consumer({
            "bootstrap.servers": config.kafka_brokers,
            "group.id": config.consumer_group,
            "auto.offset.reset": "latest",
            "enable.auto.commit": True,
        })
        self._running = False
        self._thread: threading.Thread | None = None
        self._seen_services: set = set()

    def start(self) -> None:
        self._consumer.subscribe([self._config.metrics_topic])
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="kafka-consumer")
        self._thread.start()
        logger.info("Metrics bridge consumer started", topic=self._config.metrics_topic)

    def _run(self) -> None:
        while self._running:
            msg = self._consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() != KafkaError._PARTITION_EOF:
                    logger.error("Consumer error", error=msg.error())
                continue
            try:
                payload = json.loads(msg.value().decode("utf-8"))
                record_metric_event(payload)

                service = payload.get("service")
                if service and service not in self._seen_services:
                    self._seen_services.add(service)
                    ACTIVE_SERVICES.set(len(self._seen_services))
            except (json.JSONDecodeError, Exception) as e:
                logger.warning("Failed to process metric event", error=str(e))

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._consumer.close()
        logger.info("Metrics bridge consumer stopped")
