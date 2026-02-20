# Real-Time Observability Platform

A production-grade, self-hosted observability stack showcasing SRE best practices. Python microservices simulate realistic workloads, Kafka provides durable event streaming, and the full stack deploys on Kubernetes via production-quality Helm charts with HPA, PDB, and comprehensive Prometheus/Grafana monitoring.

**Stack:** Python 3.11 · Apache Kafka · Kubernetes · Helm · Prometheus · Grafana · Alertmanager

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Observability Platform                        │
│                                                                  │
│  ┌──────────────────┐    metrics.raw     ┌──────────────────┐   │
│  │ workload-         │ ──────────────────▶│ stream-processor │   │
│  │ simulator        │                    │                  │   │
│  │                  │    logs.raw        │ • Anomaly detect │   │
│  │ • 4 services     │ ──────────────────▶│ • Sliding window │   │
│  │ • 3 regions      │                    │ • Alert dedup    │   │
│  │ • Configurable   │                    └────────┬─────────┘   │
│  │   error rates    │                             │alerts.fired  │
│  └──────────────────┘                             ▼             │
│                           metrics.raw    ┌──────────────────┐   │
│                         ──────────────▶  │ metrics-bridge   │   │
│                                          │                  │   │
│                                          │ • FastAPI        │   │
│                                          │ • /metrics HTTP  │   │
│                                          └────────┬─────────┘   │
│                                                   │ scrape/15s  │
│  ┌──────────────────┐   ┌──────────────────────┐  │             │
│  │ Alertmanager     │◀──│ Prometheus           │◀─┘             │
│  │ • Slack/PD       │   │ • PrometheusRules    │                │
│  └──────────────────┘   │ • ServiceMonitor     │                │
│                          └──────────┬───────────┘               │
│                                     │                            │
│                          ┌──────────▼───────────┐               │
│                          │ Grafana               │               │
│                          │ • Golden Signals      │               │
│                          │ • SLO Dashboard       │               │
│                          │ • Kafka Consumer Lag  │               │
│                          │ • Kubernetes Platform │               │
│                          └───────────────────────┘               │
└─────────────────────────────────────────────────────────────────┘
```

## Key SRE Concepts Demonstrated

| Concept | Implementation |
|---------|---------------|
| Golden Signals | Latency (P50/P95/P99), Traffic (RPS), Errors (rate), Saturation (CPU/mem) |
| SLO/SLI | 99.9% availability + latency SLOs with 30-day rolling windows |
| Error Budget Burn | Multiburn multiwindow (1h/6h) alerts per Google SRE Workbook |
| Event Streaming | Kafka with consumer groups, manual offset commits, DLQ |
| Anomaly Detection | Sliding window P99 and error rate rules with consecutive violation tracking |
| Zero-Downtime Deploys | `maxUnavailable: 0` rolling updates + PodDisruptionBudgets |
| Auto-Scaling | HPA on CPU (upgrade path to KEDA + Kafka lag) |
| Security | Non-root containers, read-only filesystem, no automount SA tokens |
| IaC | All config version-controlled in Helm charts with dev/prod value overlays |
| Runbooks | Per-alert markdown runbooks with triage steps and escalation paths |

## Repository Structure

```
observability-platform/
├── apps/
│   ├── workload-simulator/     # Python — emits metric events to Kafka
│   ├── stream-processor/       # Python — anomaly detection, alert publishing
│   └── metrics-bridge/         # FastAPI — Kafka → Prometheus /metrics
├── helm/
│   ├── observability-platform/ # Umbrella chart (Kafka + kube-prometheus-stack)
│   ├── workload-simulator/     # App chart with HPA + PDB
│   ├── stream-processor/       # App chart with HPA + PDB
│   └── metrics-bridge/         # App chart with ServiceMonitor
├── k8s/
│   ├── namespaces.yaml
│   ├── rbac.yaml
│   └── network-policies.yaml
├── dashboards/                 # Grafana dashboard JSON (dashboards-as-code)
│   ├── golden-signals.json
│   ├── kafka-consumer-lag.json
│   ├── slo-dashboard.json
│   └── kubernetes-platform.json
├── runbooks/                   # Per-alert markdown runbooks
├── docs/
│   ├── slos/                   # SLO definitions (api-service.yaml)
│   └── adr/                    # Architecture Decision Records
├── tests/                      # Smoke tests (end-to-end pipeline validation)
├── scripts/                    # load_test.py
├── Makefile                    # Build, test, deploy, and clean automation
└── kind-config.yaml            # Local cluster configuration
```

## Quick Start

### Using Makefile (recommended)

From zero to a running platform in 3 commands:

```bash
# 1. Install Python dependencies
make install

# 2. Run tests to verify everything works
make test

# 3. Build images, create cluster, and deploy the full stack
make run
```

Then access the dashboards:

```bash
# Port-forward Grafana (3000), Prometheus (9090), metrics-bridge (8080)
make port-forward
# Grafana:    http://localhost:3000 (admin / observability123)
# Prometheus: http://localhost:9090
```

### All Makefile Targets

| Target | Description |
|--------|-------------|
| `make install` | Install all Python dependencies (Poetry) |
| `make test` | Run unit tests for all 3 apps |
| `make test-cov` | Run tests with coverage report (60% min) |
| `make lint` | Run ruff + mypy on all apps |
| `make lint-helm` | Lint all Helm charts |
| `make build` | Build Docker images for all apps |
| `make cluster` | Create kind cluster + namespaces + RBAC + network policies |
| `make deploy` | Update Helm deps, load images, deploy full stack |
| `make run` | **Full setup from zero** (cluster + build + deploy) |
| `make port-forward` | Port-forward Grafana, Prometheus, and metrics-bridge |
| `make smoke-test` | Run end-to-end smoke tests |
| `make load-test` | Spike to 100 RPS for 2 min |
| `make clean` | **Tear down everything** (Helm releases, kind cluster, images) |
| `make help` | Show all available targets |

### Manual Setup (step-by-step)

<details>
<summary>Expand for manual commands without Make</summary>

```bash
# 1. Create local Kubernetes cluster
kind create cluster --name observability --config kind-config.yaml

# 2. Create namespaces
kubectl apply -f k8s/namespaces.yaml

# 3. Add Helm repositories
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# 4. Update chart dependencies
cd helm/observability-platform && helm dependency update && cd ../..

# 5. Build application images
docker build -t workload-simulator:local ./apps/workload-simulator
docker build -t stream-processor:local ./apps/stream-processor
docker build -t metrics-bridge:local ./apps/metrics-bridge

# 6. Load images into kind
kind load docker-image workload-simulator:local --name observability
kind load docker-image stream-processor:local --name observability
kind load docker-image metrics-bridge:local --name observability

# 7. Deploy the full stack
helm upgrade --install obs ./helm/observability-platform \
  -f helm/observability-platform/values-dev.yaml \
  -n monitoring --create-namespace --wait

# 8. Deploy application workloads
helm upgrade --install workload-sim ./helm/workload-simulator -n observability --wait
helm upgrade --install stream-proc ./helm/stream-processor -n observability --wait
helm upgrade --install metrics-br ./helm/metrics-bridge -n observability --wait

# 9. Access Grafana
kubectl port-forward svc/obs-grafana 3000:80 -n monitoring
# Open: http://localhost:3000 (admin / observability123)

# 10. Run smoke tests
kubectl port-forward svc/metrics-bridge 8080:8080 -n observability &
kubectl port-forward svc/obs-kube-prometheus-stack-prometheus 9090:9090 -n monitoring &
python tests/smoke_test.py
```

</details>

## Component Overview

| Component | Language | Kafka Topics | Purpose |
|-----------|----------|-------------|---------|
| workload-simulator | Python 3.11 | → metrics.raw, logs.raw | Simulates HTTP API traffic with configurable error rates and latency spikes |
| stream-processor | Python 3.11 | ← metrics.raw, → alerts.fired | Consumes events, runs sliding window anomaly detection, publishes alerts |
| metrics-bridge | Python/FastAPI | ← metrics.raw | Bridges Kafka stream to Prometheus `/metrics` endpoint |

## SLO Summary

| Service | SLO | Target | Window |
|---------|-----|--------|--------|
| api-service | Availability | 99.9% | 30 days |
| api-service | Latency P99 < 500ms | 99.0% | 30 days |
| All services | Error Budget Burn | < 14x fast / 3x slow | Rolling |

## Alerting Rules

| Alert | Condition | Severity |
|-------|-----------|----------|
| HighLatencyP99 | P99 > 500ms for 5m | warning |
| HighErrorRate | Error rate > 5% for 3m | critical |
| KafkaConsumerLagHigh | Lag > 1000 msgs for 10m | warning |
| PodRestartingFrequently | >5 restarts in 15m | warning |
| ErrorBudgetBurnRateFast | 14x burn rate (1h window) | critical |
| ErrorBudgetBurnRateSlow | 3x burn rate (6h window) | warning |

## Runbooks

- [HighLatencyP99](runbooks/high-latency-p99.md)
- [HighErrorRate](runbooks/high-error-rate.md)
- [ErrorBudgetBurn](runbooks/error-budget-burn.md)

## Testing

```bash
make test          # Run all unit tests
make test-cov      # Run tests with coverage
make lint          # Ruff + mypy
make smoke-test    # End-to-end validation (requires a running cluster)
```

## Load Testing

Trigger HPA scaling and validate the platform handles load:

```bash
make load-test
# or manually:
python scripts/load_test.py --target-rps 100 --error-rate 0.1 --duration 120
```

Watch the Grafana dashboards respond in real time.

## Cleanup

Tear down all resources (Helm releases, kind cluster, Docker images):

```bash
make clean
```

## Architecture Decisions

- [ADR-001: Kafka over Prometheus Remote Write](docs/adr/ADR-001-kafka-over-remote-write.md)
- [ADR-002: CPU HPA vs KEDA Kafka Lag](docs/adr/ADR-002-consumer-lag-vs-cpu-hpa.md)

## Future Improvements

- KEDA integration for Kafka consumer lag-based autoscaling
- Chaos engineering script (random pod kills, network latency injection)
- Distributed tracing with OpenTelemetry + Tempo
- Multi-cluster federation with Thanos
- GitHub Actions CD pipeline for automated deployment
