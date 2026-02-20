from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    # Patch the consumer so it doesn't try to connect to Kafka
    with patch("main.consumer") as mock_consumer:
        mock_consumer.start = MagicMock()
        mock_consumer.stop = MagicMock()
        from main import app
        with TestClient(app) as c:
            yield c


class TestHealthEndpoints:
    def test_healthz(self, client):
        response = client.get("/healthz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_readyz(self, client):
        response = client.get("/readyz")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
        assert data["kafka_topic"] == "metrics.raw"


class TestMetricsEndpoint:
    def test_metrics_returns_prometheus_format(self, client):
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"] or \
               "text/plain" in response.headers.get("content-type", "")
        body = response.text
        # Should contain at least the standard process metrics from prometheus_client
        assert "process_" in body or "python_" in body or "workload_" in body

    def test_metrics_contains_custom_metrics(self, client):
        """After recording an event, /metrics should expose it."""
        from bridge.metrics import record_metric_event
        record_metric_event({
            "service": "test-svc",
            "endpoint": "/test",
            "region": "us-east-1",
            "status_code": 200,
            "latency_ms": 42.0,
            "error": False,
        })
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "workload_requests_total" in response.text
        assert "workload_request_latency_ms" in response.text
