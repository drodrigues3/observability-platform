from bridge.config import Config


class TestConfig:
    def test_defaults(self):
        config = Config()
        assert config.kafka_brokers == "kafka:9092"
        assert config.metrics_topic == "metrics.raw"
        assert config.consumer_group == "metrics-bridge-group"
        assert config.server_host == "0.0.0.0"
        assert config.server_port == 8080

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BROKERS", "localhost:9093")
        monkeypatch.setenv("SERVER_PORT", "9090")
        monkeypatch.setenv("CONSUMER_GROUP", "custom-group")
        config = Config()
        assert config.kafka_brokers == "localhost:9093"
        assert config.server_port == 9090
        assert config.consumer_group == "custom-group"
