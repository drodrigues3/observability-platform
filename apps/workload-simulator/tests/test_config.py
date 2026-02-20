from simulator.config import Config


class TestConfig:
    def test_defaults(self):
        config = Config()
        assert config.kafka_brokers == "kafka:9092"
        assert config.metrics_topic == "metrics.raw"
        assert config.logs_topic == "logs.raw"
        assert config.events_per_second == 10
        assert config.error_rate == 0.02
        assert config.latency_spike_probability == 0.05
        assert len(config.services) == 4
        assert len(config.regions) == 3
        assert config.producer_retry_max == 3
        assert config.producer_flush_timeout == 10

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("KAFKA_BROKERS", "localhost:9093")
        monkeypatch.setenv("EVENTS_PER_SECOND", "50")
        monkeypatch.setenv("ERROR_RATE", "0.1")
        config = Config()
        assert config.kafka_brokers == "localhost:9093"
        assert config.events_per_second == 50
        assert config.error_rate == 0.1
