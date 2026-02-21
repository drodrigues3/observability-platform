from bridge.metrics import record_metric_event


class TestRecordMetricEvent:
    def test_records_successful_request(self):
        payload = {
            "service": "api-service",
            "endpoint": "/api/v1/users",
            "region": "us-east-1",
            "status_code": 200,
            "latency_ms": 120.5,
            "error": False,
        }
        # Should not raise
        record_metric_event(payload)

    def test_records_error_request(self):
        payload = {
            "service": "api-service",
            "endpoint": "/api/v1/users",
            "region": "us-east-1",
            "status_code": 500,
            "latency_ms": 1500.0,
            "error": True,
        }
        record_metric_event(payload)

    def test_handles_missing_fields_with_defaults(self):
        payload: dict[str, object] = {}
        # Should not raise — uses defaults for all fields
        record_metric_event(payload)

    def test_handles_partial_payload(self):
        payload = {"service": "auth-service", "latency_ms": 50}
        record_metric_event(payload)

    def test_status_code_as_string_label(self):
        """Status code should be stored as a string label."""
        from bridge.metrics import REQUEST_TOTAL

        payload = {
            "service": "test-service",
            "endpoint": "/test",
            "region": "us-east-1",
            "status_code": 201,
            "latency_ms": 50,
            "error": False,
        }
        record_metric_event(payload)
        # Verify the label was created with string status_code
        sample_value = REQUEST_TOTAL.labels(
            service="test-service",
            endpoint="/test",
            region="us-east-1",
            status_code="201",
        )._value.get()
        assert sample_value >= 1

    def test_error_counter_increments_only_on_error(self):
        from bridge.metrics import ERROR_TOTAL

        before = ERROR_TOTAL.labels(
            service="error-test-svc",
            endpoint="/err",
            region="us-east-1",
        )._value.get()

        # Non-error request
        record_metric_event({
            "service": "error-test-svc",
            "endpoint": "/err",
            "region": "us-east-1",
            "status_code": 200,
            "latency_ms": 50,
            "error": False,
        })
        after_ok = ERROR_TOTAL.labels(
            service="error-test-svc",
            endpoint="/err",
            region="us-east-1",
        )._value.get()
        assert after_ok == before

        # Error request
        record_metric_event({
            "service": "error-test-svc",
            "endpoint": "/err",
            "region": "us-east-1",
            "status_code": 500,
            "latency_ms": 200,
            "error": True,
        })
        after_err = ERROR_TOTAL.labels(
            service="error-test-svc",
            endpoint="/err",
            region="us-east-1",
        )._value.get()
        assert after_err == before + 1
