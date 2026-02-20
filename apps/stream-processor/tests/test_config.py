from processor.config import Config


class TestConfig:
    def test_defaults(self):
        config = Config()
        assert config.kafka_brokers == "kafka:9092"
        assert config.metrics_topic == "metrics.raw"
        assert config.alerts_topic == "alerts.fired"
        assert config.consumer_group == "stream-processor-group"
        assert config.consumer_timeout_ms == 1000
        assert config.window_size_seconds == 60
        assert config.latency_p99_threshold_ms == 500.0
        assert config.error_rate_threshold == 0.05
        assert config.traffic_drop_threshold == 0.5
        assert config.alert_cooldown_seconds == 300
        assert config.consecutive_windows_for_alert == 3

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("WINDOW_SIZE_SECONDS", "120")
        monkeypatch.setenv("LATENCY_P99_THRESHOLD_MS", "250")
        monkeypatch.setenv("CONSECUTIVE_WINDOWS_FOR_ALERT", "5")
        config = Config()
        assert config.window_size_seconds == 120
        assert config.latency_p99_threshold_ms == 250.0
        assert config.consecutive_windows_for_alert == 5
