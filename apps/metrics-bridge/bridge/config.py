from pydantic import Field
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    kafka_brokers: str = Field(default="kafka:9092")
    metrics_topic: str = Field(default="metrics.raw")
    consumer_group: str = Field(default="metrics-bridge-group")
    server_host: str = Field(default="0.0.0.0")
    server_port: int = Field(default=8080)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
