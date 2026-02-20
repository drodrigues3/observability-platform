from prometheus_client import Counter, Histogram, Gauge

# Request latency histogram with SLO-friendly buckets (ms)
REQUEST_LATENCY = Histogram(
    "workload_request_latency_ms",
    "HTTP request latency in milliseconds",
    ["service", "endpoint", "region"],
    buckets=[10, 25, 50, 100, 200, 300, 500, 750, 1000, 2500, 5000],
)

# Request counters for golden signals
REQUEST_TOTAL = Counter(
    "workload_requests_total",
    "Total number of HTTP requests",
    ["service", "endpoint", "region", "status_code"],
)

ERROR_TOTAL = Counter(
    "workload_errors_total",
    "Total number of errored requests",
    ["service", "endpoint", "region"],
)

# Gauge for live service discovery
ACTIVE_SERVICES = Gauge(
    "workload_active_services",
    "Number of unique services emitting metrics",
)


def record_metric_event(payload: dict) -> None:
    """Update Prometheus metrics from a raw Kafka metric event payload."""
    service = payload.get("service", "unknown")
    endpoint = payload.get("endpoint", "/")
    region = payload.get("region", "unknown")
    status_code = str(payload.get("status_code", 0))
    latency_ms = float(payload.get("latency_ms", 0))
    error = bool(payload.get("error", False))

    REQUEST_LATENCY.labels(service=service, endpoint=endpoint, region=region).observe(latency_ms)
    REQUEST_TOTAL.labels(
        service=service, endpoint=endpoint, region=region, status_code=status_code
    ).inc()
    if error:
        ERROR_TOTAL.labels(service=service, endpoint=endpoint, region=region).inc()
