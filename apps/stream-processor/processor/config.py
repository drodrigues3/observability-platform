from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    kafka_brokers: str = Field(default="kafka:9092", env="KAFKA_BROKERS")
    metrics_topic: str = Field(default="metrics.raw", env="METRICS_TOPIC")
    alerts_topic: str = Field(default="alerts.fired", env="ALERTS_TOPIC")
    consumer_group: str = Field(default="stream-processor-group", env="CONSUMER_GROUP")
    consumer_timeout_ms: int = Field(default=1000, env="CONSUMER_TIMEOUT_MS")
    window_size_seconds: int = Field(default=60, env="WINDOW_SIZE_SECONDS")
    latency_p99_threshold_ms: float = Field(default=500.0, env="LATENCY_P99_THRESHOLD_MS")
    error_rate_threshold: float = Field(default=0.05, env="ERROR_RATE_THRESHOLD")
    traffic_drop_threshold: float = Field(default=0.5, env="TRAFFIC_DROP_THRESHOLD")
    alert_cooldown_seconds: int = Field(default=300, env="ALERT_COOLDOWN_SECONDS")
    consecutive_windows_for_alert: int = Field(default=3, env="CONSECUTIVE_WINDOWS_FOR_ALERT")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
