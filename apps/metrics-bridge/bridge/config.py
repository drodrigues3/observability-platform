from pydantic_settings import BaseSettings
from pydantic import Field


class Config(BaseSettings):
    kafka_brokers: str = Field(default="kafka:9092", env="KAFKA_BROKERS")
    metrics_topic: str = Field(default="metrics.raw", env="METRICS_TOPIC")
    consumer_group: str = Field(default="metrics-bridge-group", env="CONSUMER_GROUP")
    server_host: str = Field(default="0.0.0.0", env="SERVER_HOST")
    server_port: int = Field(default=8080, env="SERVER_PORT")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}
