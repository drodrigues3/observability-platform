import signal
import sys
import threading
from types import FrameType
from typing import Optional

import structlog

from simulator.config import Config
from simulator.metrics import MetricsGenerator
from simulator.producer import KafkaProducerWrapper

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)


def main() -> None:
    config = Config()
    producer = KafkaProducerWrapper(config)
    generator = MetricsGenerator(config, producer)

    stop_event = threading.Event()

    def handle_signal(signum: int, frame: Optional[FrameType]) -> None:
        logger.info("Received shutdown signal", signal=signum)
        stop_event.set()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info(
        "Starting workload simulator",
        kafka_brokers=config.kafka_brokers,
        events_per_second=config.events_per_second,
        services=config.services,
    )

    threads = []
    for service in config.services:
        t = threading.Thread(
            target=generator.run_service,
            args=(service, stop_event),
            name=f"simulator-{service}",
            daemon=True,
        )
        t.start()
        threads.append(t)

    stop_event.wait()
    logger.info("Shutting down gracefully...")
    producer.close()
    sys.exit(0)


if __name__ == "__main__":
    main()
