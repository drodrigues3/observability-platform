from pydantic import BaseModel, Field
from datetime import datetime, timezone
from typing import Optional
import uuid


class MetricEvent(BaseModel):
    service: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    latency_ms: float
    status_code: int
    endpoint: str
    region: str
    error: bool
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    rps: Optional[float] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class LogEvent(BaseModel):
    service: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: str
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    request_id: Optional[str] = None

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}


class AlertEvent(BaseModel):
    alert_name: str
    service: str
    severity: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    labels: dict[str, str] = Field(default_factory=dict)
    annotations: dict[str, str] = Field(default_factory=dict)
    fingerprint: str = Field(default_factory=lambda: str(uuid.uuid4()))

    model_config = {"json_encoders": {datetime: lambda v: v.isoformat()}}
