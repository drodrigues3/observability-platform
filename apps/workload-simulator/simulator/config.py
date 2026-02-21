from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    kafka_brokers: str = Field(default="kafka:9092")
    metrics_topic: str = Field(default="metrics.raw")
    logs_topic: str = Field(default="logs.raw")
    events_per_second: int = Field(default=10)
    error_rate: float = Field(default=0.02)
    latency_spike_probability: float = Field(default=0.05)
    services: List[str] = Field(
        default=["api-service", "auth-service", "payment-service", "user-service"],
    )
    regions: List[str] = Field(
        default=["us-east-1", "us-west-2", "eu-west-1"],
    )
    producer_retry_max: int = Field(default=3)
    producer_flush_timeout: int = Field(default=10)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
