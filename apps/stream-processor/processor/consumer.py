import json

import structlog
from confluent_kafka import Consumer, KafkaError, Message

from processor.config import Config
from processor.detector import AnomalyDetector
from processor.alerter import AlertPublisher
from processor.state import WindowState

logger = structlog.get_logger(__name__)


class StreamProcessor:
    """Kafka consumer group with graceful shutdown and anomaly detection."""

    def __init__(self, config: Config) -> None:
        self._config = config
        self._state = WindowState(config.window_size_seconds)
        self._detector = AnomalyDetector(config, self._state)
        self._alerter = AlertPublisher(config)
        self._consumer = self._create_consumer()
        self._running = False
        self._processed_count = 0
        self._detection_interval = 10  # Run detection every N messages

    def _create_consumer(self) -> Consumer:
        return Consumer({
            "bootstrap.servers": self._config.kafka_brokers,
            "group.id": self._config.consumer_group,
            "auto.offset.reset": "latest",
            "enable.auto.commit": False,  # Manual offset commit for reliability
            "max.poll.interval.ms": 300000,
            "session.timeout.ms": 30000,
        })

    def _process_message(self, msg: Message) -> None:
        try:
            raw = msg.value()
            if raw is None:
                return
            payload = json.loads(raw.decode("utf-8"))
            service = payload.get("service", "unknown")
            latency_ms = float(payload.get("latency_ms", 0))
            error = bool(payload.get("error", False))

            self._detector.record(service, latency_ms, error)
            self._processed_count += 1

            if self._processed_count % self._detection_interval == 0:
                violations = self._detector.detect()
                for violation in violations:
                    self._alerter.publish(violation)

            if self._processed_count % 1000 == 0:
                logger.info("Processed events", count=self._processed_count)
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to process message", error=str(e))

    def run(self) -> None:
        self._consumer.subscribe([self._config.metrics_topic])
        self._running = True
        logger.info(
            "Stream processor started",
            topic=self._config.metrics_topic,
            consumer_group=self._config.consumer_group,
        )
        try:
            while self._running:
                msg = self._consumer.poll(timeout=self._config.consumer_timeout_ms / 1000)
                if msg is None:
                    continue
                err = msg.error()
                if err:
                    if err.code() == KafkaError._PARTITION_EOF:  # type: ignore[attr-defined]
                        continue
                    logger.error("Consumer error", error=err)
                    continue
                self._process_message(msg)
                # Manual offset commit after successful processing
                self._consumer.commit(asynchronous=False)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        logger.info("Shutting down stream processor", total_processed=self._processed_count)
        self._consumer.close()
        self._alerter.close()

    def stop(self) -> None:
        self._running = False
