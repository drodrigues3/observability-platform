import signal
import sys
from types import FrameType
from typing import Optional

import structlog

from processor.config import Config
from processor.consumer import StreamProcessor

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
    processor = StreamProcessor(config)

    def handle_signal(signum: int, frame: Optional[FrameType]) -> None:
        logger.info("Received shutdown signal", signal=signum)
        processor.stop()

    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    logger.info(
        "Starting stream processor",
        kafka_brokers=config.kafka_brokers,
        consumer_group=config.consumer_group,
        window_size_seconds=config.window_size_seconds,
    )
    processor.run()
    sys.exit(0)


if __name__ == "__main__":
    main()
