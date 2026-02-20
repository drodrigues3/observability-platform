import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Dict, List, Optional


@dataclass
class MetricSample:
    timestamp: float
    latency_ms: float
    error: bool


@dataclass
class ServiceWindow:
    """Sliding window of metric samples per service."""

    samples: Deque[MetricSample] = field(default_factory=lambda: deque(maxlen=10000))
    consecutive_violations: Dict[str, int] = field(default_factory=dict)
    baseline_rps: Optional[float] = None

    def add_sample(self, latency_ms: float, error: bool) -> None:
        self.samples.append(MetricSample(
            timestamp=time.time(),
            latency_ms=latency_ms,
            error=error,
        ))

    def prune(self, window_seconds: int) -> None:
        """Remove samples older than window_seconds."""
        cutoff = time.time() - window_seconds
        while self.samples and self.samples[0].timestamp < cutoff:
            self.samples.popleft()

    def get_p99_latency(self) -> Optional[float]:
        if not self.samples:
            return None
        latencies = sorted(s.latency_ms for s in self.samples)
        idx = int(len(latencies) * 0.99)
        return latencies[min(idx, len(latencies) - 1)]

    def get_error_rate(self) -> Optional[float]:
        if not self.samples:
            return None
        errors = sum(1 for s in self.samples if s.error)
        return errors / len(self.samples)

    def get_rps(self, window_seconds: int) -> Optional[float]:
        if not self.samples:
            return None
        return len(self.samples) / window_seconds


class WindowState:
    """Manages sliding window state for all services."""

    def __init__(self, window_size_seconds: int) -> None:
        self._window_size = window_size_seconds
        self._windows: Dict[str, ServiceWindow] = {}

    def record(self, service: str, latency_ms: float, error: bool) -> None:
        if service not in self._windows:
            self._windows[service] = ServiceWindow()
        self._windows[service].add_sample(latency_ms, error)
        self._windows[service].prune(self._window_size)

    def get_window(self, service: str) -> Optional[ServiceWindow]:
        return self._windows.get(service)

    def get_all_services(self) -> List[str]:
        return list(self._windows.keys())
