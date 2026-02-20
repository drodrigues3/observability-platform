import json
from datetime import datetime, timezone

from simulator.models import MetricEvent, LogEvent, AlertEvent


class TestMetricEvent:
    def test_required_fields(self):
        event = MetricEvent(
            service="api-service",
            latency_ms=120.5,
            status_code=200,
            endpoint="/api/v1/users",
            region="us-east-1",
            error=False,
        )
        assert event.service == "api-service"
        assert event.latency_ms == 120.5
        assert event.status_code == 200
        assert event.error is False
        assert event.request_id  # auto-generated UUID
        assert event.timestamp  # auto-generated

    def test_json_serialization(self):
        event = MetricEvent(
            service="api-service",
            latency_ms=50.0,
            status_code=200,
            endpoint="/health",
            region="us-west-2",
            error=False,
        )
        data = json.loads(event.model_dump_json())
        assert data["service"] == "api-service"
        assert data["latency_ms"] == 50.0
        assert "timestamp" in data
        assert "request_id" in data

    def test_error_event(self):
        event = MetricEvent(
            service="payment-service",
            latency_ms=1500.0,
            status_code=500,
            endpoint="/payments/charge",
            region="eu-west-1",
            error=True,
        )
        assert event.error is True
        assert event.status_code == 500

    def test_optional_rps(self):
        event = MetricEvent(
            service="api-service",
            latency_ms=100.0,
            status_code=200,
            endpoint="/health",
            region="us-east-1",
            error=False,
            rps=42.5,
        )
        assert event.rps == 42.5

    def test_unique_request_ids(self):
        events = [
            MetricEvent(
                service="api-service",
                latency_ms=100.0,
                status_code=200,
                endpoint="/health",
                region="us-east-1",
                error=False,
            )
            for _ in range(10)
        ]
        ids = {e.request_id for e in events}
        assert len(ids) == 10


class TestLogEvent:
    def test_basic_log(self):
        event = LogEvent(
            service="api-service",
            level="ERROR",
            message="Connection timeout",
        )
        assert event.level == "ERROR"
        assert event.message == "Connection timeout"
        assert event.trace_id is None

    def test_log_with_trace(self):
        event = LogEvent(
            service="api-service",
            level="INFO",
            message="Request handled",
            trace_id="abc123",
            span_id="span456",
            request_id="req789",
        )
        assert event.trace_id == "abc123"
        assert event.span_id == "span456"

    def test_json_serialization(self):
        event = LogEvent(service="auth-service", level="WARN", message="Slow query")
        data = json.loads(event.model_dump_json())
        assert data["service"] == "auth-service"
        assert data["level"] == "WARN"


class TestAlertEvent:
    def test_basic_alert(self):
        alert = AlertEvent(
            alert_name="HighLatencyP99",
            service="api-service",
            severity="warning",
        )
        assert alert.alert_name == "HighLatencyP99"
        assert alert.severity == "warning"
        assert alert.fingerprint  # auto-generated
        assert alert.labels == {}
        assert alert.annotations == {}

    def test_alert_with_labels(self):
        alert = AlertEvent(
            alert_name="HighErrorRate",
            service="payment-service",
            severity="critical",
            labels={"team": "payments", "env": "prod"},
            annotations={"summary": "Error rate above 5%"},
        )
        assert alert.labels["team"] == "payments"
        assert "summary" in alert.annotations
