# ADR-002: Stream-Processor Autoscaling Strategy

**Status:** Accepted
**Date:** 2024-01-01
**Deciders:** SRE Platform Team

---

## Context

The stream-processor consumes from the `metrics.raw` Kafka topic and must scale horizontally when the incoming event rate exceeds what the current replica count can handle. The scaling signal should reflect actual backpressure as accurately as possible while keeping operational complexity manageable.

Three approaches were evaluated:

| # | Approach | Scaling Signal |
|---|----------|---------------|
| 1 | CPU-based HPA | Pod CPU utilization |
| 2 | Prometheus Adapter + HPA | Kafka consumer lag exposed as a Kubernetes custom metric |
| 3 | KEDA + Kafka trigger | Kafka consumer lag queried directly by the KEDA operator |

---

## Option 1 — CPU-Based HPA

The simplest approach: a native `autoscaling/v2` HPA targets average CPU utilization.

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stream-processor
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stream-processor
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
```

**Strengths**
- Zero additional dependencies — built into every Kubernetes cluster.
- Easy to reason about and debug (`kubectl get hpa`).
- Sufficient for demo and low-to-medium throughput workloads.

**Weaknesses**
- CPU is a proxy metric, not the real scaling signal. If the stream-processor is I/O-bound (waiting on Kafka or network), CPU stays low even when consumer lag is growing.
- Reactive rather than predictive — lag must build up enough to raise CPU before scaling kicks in.

---

## Option 2 — Prometheus Adapter + Custom Metrics HPA

Exposes `kafka_consumer_group_lag` (already scraped by Prometheus via Kafka Exporter) through the Kubernetes Custom Metrics API (`custom.metrics.k8s.io`), then targets it from a native HPA.

```yaml
# Prometheus Adapter ConfigMap rule
rules:
  - seriesQuery: 'kafka_consumer_group_lag{topic="metrics.raw"}'
    resources:
      overrides:
        namespace: { resource: namespace }
    name:
      matches: "kafka_consumer_group_lag"
      as: "kafka_consumer_group_lag"
    metricsQuery: >-
      sum(kafka_consumer_group_lag{
        topic="metrics.raw",
        consumergroup="stream-processor-group"
      })

---
# HPA using the custom metric
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: stream-processor
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: stream-processor
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Object
      object:
        metric:
          name: kafka_consumer_group_lag
        describedObject:
          apiVersion: v1
          kind: Namespace
          name: observability
        target:
          type: Value
          value: "100"
```

**Strengths**
- Scales on the actual work signal (consumer lag) instead of a proxy.
- Uses Kubernetes-native HPA — no new operator CRDs.
- Good fit when Prometheus Adapter is already deployed for other custom metrics (e.g., request-rate HPA on the metrics-bridge).

**Weaknesses**
- Requires deploying and maintaining Prometheus Adapter if not already present.
- PromQL-to-custom-metric mapping rules must be maintained in sync with topic/consumer-group names.
- HPA minimum replicas is 1 — cannot scale to zero.
- Metric freshness depends on Prometheus scrape interval + Adapter cache (typically 30-60 s lag).

---

## Option 3 — KEDA + Kafka Trigger

KEDA is a dedicated autoscaling operator that queries Kafka broker metadata directly and manages an HPA under the hood via its `ScaledObject` CRD.

```yaml
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: stream-processor-scaler
spec:
  scaleTargetRef:
    name: stream-processor
  minReplicaCount: 0
  maxReplicaCount: 10
  triggers:
    - type: kafka
      metadata:
        bootstrapServers: kafka:9092
        consumerGroup: stream-processor-group
        topic: metrics.raw
        lagThreshold: "100"
```

**Strengths**
- Scales on real consumer lag with direct broker queries — no Prometheus in the scaling path.
- Supports **scale-to-zero**: replicas drop to 0 when no lag exists, saving resources.
- Polling interval is configurable per trigger (default 30 s, can go lower).
- 50+ built-in scalers — if the platform later adds SQS, Redis Streams, or other sources, the same operator handles them.

**Weaknesses**
- Requires installing the KEDA operator (Helm chart + CRDs).
- Another component to monitor, upgrade, and secure.
- `ScaledObject` is a KEDA-specific CRD — less portable than a plain HPA manifest.

---

## Comparison

| Aspect | CPU HPA | Prometheus Adapter + HPA | KEDA |
|--------|---------|--------------------------|------|
| **Scaling signal** | CPU utilization (proxy) | Kafka consumer lag (via Prometheus) | Kafka consumer lag (direct) |
| **Additional deps** | None | Prometheus Adapter | KEDA operator |
| **Scale-to-zero** | No | No | Yes |
| **Metric freshness** | kubelet cadence (~15 s) | Scrape interval + cache (~30-60 s) | Configurable polling (~30 s default) |
| **Metric sources** | CPU / memory only | Any Prometheus metric | 50+ scalers |
| **Operational complexity** | Low | Medium | Medium |
| **Kubernetes-native** | Yes | Yes (standard HPA) | Partially (CRD-managed HPA) |
| **Best for** | Simple workloads, demos | Teams already running Prometheus Adapter | Production event-driven workloads |

---

## Decision

**Start with CPU-based HPA (Option 1)** for the initial deployment. It requires zero additional infrastructure and is sufficient to demonstrate autoscaling behavior in the portfolio project.

**Upgrade path for production:**

1. If the team already operates **Prometheus Adapter** for other custom metrics, adopt **Option 2** — it adds lag-based scaling without a new operator.
2. Otherwise, deploy **KEDA (Option 3)** — it is simpler to configure for Kafka workloads, supports scale-to-zero, and extends naturally to other event sources.

---

## Consequences

- CPU HPA is deployed now; scaling may lag behind real backpressure under I/O-bound conditions.
- The Helm chart structure supports swapping the HPA for a `ScaledObject` without changing the Deployment template.
- Monitoring `KafkaConsumerLagHigh` alerts (defined in [prometheusrule.yaml](../../helm/observability-platform/templates/prometheusrule.yaml)) provides visibility into lag regardless of which scaling strategy is active.
