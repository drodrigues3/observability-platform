# ADR-001: Kafka for Telemetry Ingestion over Direct Prometheus Remote Write

**Status:** Accepted
**Date:** 2024-01-01
**Deciders:** SRE Platform Team

---

## Context

We needed to choose a telemetry ingestion mechanism for the workload simulator to get metrics into the observability stack. The two primary candidates were:

1. **Direct Prometheus Remote Write** — Simulators push metrics directly to Prometheus
2. **Apache Kafka** — Simulators publish JSON events to Kafka; a stream processor consumes and transforms them

## Decision

We chose **Apache Kafka** as the event streaming backbone.

## Consequences

### Positive

- **Decoupling:** Producers (simulators) and consumers (processors, bridge) are fully independent — new consumers can be added without modifying producers
- **Durability:** Events are persisted to disk; stream processor resumes from last committed offset after restart
- **Stream processing:** Enables stateful sliding window operations (P99 calculation, alert deduplication) that are not practical with direct Prometheus remote write
- **Scalability:** Consumer groups allow horizontal scaling of the stream processor independently of producers
- **Multi-consumer:** The same event stream feeds both the anomaly detector and the metrics bridge simultaneously
- **Realistic architecture:** Kafka is the industry standard for observability pipelines at scale

### Negative

- **Operational complexity:** Running Kafka adds a stateful dependency requiring proper sizing and monitoring
- **Local development overhead:** Requires Kafka running locally
- **Additional latency:** Kafka introduces 10-100ms additional latency vs. direct write — acceptable for observability

## Alternatives Considered

| Option | Rejected Because |
|--------|-----------------|
| Direct Prometheus remote write | No stream processing capability; tight coupling; no replay |
| Redis Streams | Weaker durability; smaller ecosystem |
| HTTP push to metrics-bridge | No durability; coupling; no fanout to multiple consumers |
