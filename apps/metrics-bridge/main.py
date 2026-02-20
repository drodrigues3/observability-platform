from contextlib import asynccontextmanager

import structlog
import uvicorn
from fastapi import FastAPI
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from bridge.config import Config
from bridge.consumer import MetricsBridgeConsumer

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.BoundLogger,
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger(__name__)
config = Config()
consumer = MetricsBridgeConsumer(config)


@asynccontextmanager
async def lifespan(app: FastAPI):
    consumer.start()
    logger.info("Metrics bridge started", port=config.server_port)
    yield
    consumer.stop()
    logger.info("Metrics bridge stopped")


app = FastAPI(
    title="Metrics Bridge",
    description="Bridges Kafka metrics stream to Prometheus scrape endpoint",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/metrics", response_class=Response)
async def metrics():
    """Prometheus metrics endpoint — scraped by Prometheus via ServiceMonitor."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/healthz")
async def health():
    """Liveness probe endpoint."""
    return {"status": "ok"}


@app.get("/readyz")
async def ready():
    """Readiness probe endpoint — indicates Kafka consumer is connected."""
    return {"status": "ready", "kafka_topic": config.metrics_topic}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=config.server_host,
        port=config.server_port,
        log_config=None,  # Use structlog instead of uvicorn's default logger
    )
