from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    kafka_brokers: str = Field(default="kafka:9092")
    metrics_topic: str = Field(default="metrics.raw")
    alerts_topic: str = Field(default="alerts.fired")
    consumer_group: str = Field(default="stream-processor-group")
    consumer_timeout_ms: int = Field(default=1000)
    window_size_seconds: int = Field(default=60)
    latency_p99_threshold_ms: float = Field(default=500.0)
    error_rate_threshold: float = Field(default=0.05)
    traffic_drop_threshold: float = Field(default=0.5)
    alert_cooldown_seconds: int = Field(default=300)
    consecutive_windows_for_alert: int = Field(default=3)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
