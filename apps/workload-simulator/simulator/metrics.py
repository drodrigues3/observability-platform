import random
import threading
import time
from datetime import datetime, timezone

import structlog

from simulator.config import Config
from simulator.models import MetricEvent, LogEvent
from simulator.producer import KafkaProducerWrapper

logger = structlog.get_logger(__name__)

ENDPOINTS = {
    "api-service": ["/api/v1/users", "/api/v1/products", "/api/v1/orders", "/health"],
    "auth-service": ["/auth/login", "/auth/refresh", "/auth/logout", "/auth/verify"],
    "payment-service": ["/payments/charge", "/payments/refund", "/payments/status"],
    "user-service": ["/users/profile", "/users/preferences", "/users/search"],
}

# Normal latency range (ms): (low, high)
NORMAL_LATENCY_MS: dict[str, tuple[float, float]] = {
    "api-service": (50, 150),
    "auth-service": (20, 80),
    "payment-service": (100, 400),
    "user-service": (30, 100),
}


class MetricsGenerator:
    """Generates realistic metric events with configurable failure scenarios."""

    def __init__(self, config: Config, producer: KafkaProducerWrapper) -> None:
        self._config = config
        self._producer = producer
        self._lock = threading.Lock()

    def _generate_latency(self, service: str, is_spike: bool) -> float:
        lo, hi = NORMAL_LATENCY_MS.get(service, (50, 200))
        if is_spike:
            # Simulate P99 spike: 3-10x normal upper bound
            return random.uniform(hi * 3, hi * 10)
        # Normal: Gaussian distribution clipped to [lo, hi*2]
        mean = (lo + hi) / 2
        std = (hi - lo) / 4
        return max(lo, min(hi * 2, random.gauss(mean, std)))

    def _generate_status_code(self, is_error: bool) -> int:
        if is_error:
            return random.choice([500, 502, 503, 429, 400])
        return random.choice([200, 200, 200, 200, 201, 204])

    def _emit_event(self, service: str) -> None:
        is_spike = random.random() < self._config.latency_spike_probability
        is_error = random.random() < self._config.error_rate
        region = random.choice(self._config.regions)
        endpoints = ENDPOINTS.get(service, ["/"])
        endpoint = random.choice(endpoints)

        event = MetricEvent(
            service=service,
            timestamp=datetime.now(timezone.utc),
            latency_ms=round(self._generate_latency(service, is_spike), 2),
            status_code=self._generate_status_code(is_error),
            endpoint=endpoint,
            region=region,
            error=is_error,
        )
        self._producer.publish_metric(event)

        if is_error:
            log_event = LogEvent(
                service=service,
                level="ERROR",
                message=f"Request failed with status {event.status_code} on {endpoint}",
                request_id=event.request_id,
            )
            self._producer.publish_log(log_event)

    def run_service(self, service: str, stop_event: threading.Event) -> None:
        """Run the metrics generator loop for a single service."""
        interval = 1.0 / self._config.events_per_second
        logger.info("Starting simulator thread", service=service, interval_ms=interval * 1000)

        while not stop_event.is_set():
            start = time.monotonic()
            try:
                self._emit_event(service)
            except Exception as e:
                logger.exception("Unexpected error generating event", service=service, error=str(e))

            elapsed = time.monotonic() - start
            sleep_time = max(0.0, interval - elapsed)
            stop_event.wait(timeout=sleep_time)

        logger.info("Simulator thread stopped", service=service)
