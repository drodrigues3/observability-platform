from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List


class Config(BaseSettings):
    kafka_brokers: str = Field(default="kafka:9092", env="KAFKA_BROKERS")
    metrics_topic: str = Field(default="metrics.raw", env="METRICS_TOPIC")
    logs_topic: str = Field(default="logs.raw", env="LOGS_TOPIC")
    events_per_second: int = Field(default=10, env="EVENTS_PER_SECOND")
    error_rate: float = Field(default=0.02, env="ERROR_RATE")
    latency_spike_probability: float = Field(default=0.05, env="LATENCY_SPIKE_PROBABILITY")
    services: List[str] = Field(
        default=["api-service", "auth-service", "payment-service", "user-service"],
        env="SERVICES",
    )
    regions: List[str] = Field(
        default=["us-east-1", "us-west-2", "eu-west-1"],
        env="REGIONS",
    )
    producer_retry_max: int = Field(default=3, env="PRODUCER_RETRY_MAX")
    producer_flush_timeout: int = Field(default=10, env="PRODUCER_FLUSH_TIMEOUT")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
