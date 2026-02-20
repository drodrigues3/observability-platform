# Runbook: HighLatencyP99

**Alert:** `HighLatencyP99`
**Severity:** Warning
**SLO Impact:** Latency SLO — consuming error budget

---

## What It Means

P99 latency for one or more services has exceeded **500ms** for the past **5 minutes**. This means 1 in 100 users is experiencing significantly degraded response times.

## Impact

- Degraded user experience for the slowest requests
- Active consumption of the latency error budget
- Potential SLO breach if sustained for extended periods

## Triage Steps

```bash
# 1. Identify affected service from alert labels
kubectl get pods -n observability

# 2. Check current P99 in Grafana
# Navigate to: Golden Signals > Request Latency (P50/P95/P99)

# 3. Check workload-simulator logs for anomalies
kubectl logs -l app=workload-simulator -n observability --tail=100

# 4. Check resource usage — CPU throttling causes latency spikes
kubectl top pods -n observability

# 5. Verify HPA is responding
kubectl describe hpa workload-simulator -n observability

# 6. Check Kafka lag — backpressure can cause latency
kubectl exec -it kafka-0 -n kafka -- \
  kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --group stream-processor-group
```

## Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| CPU throttling | Increase resource limits or scale replicas |
| High `LATENCY_SPIKE_PROBABILITY` | Set env var to `0.01` and rollout |
| Kafka producer backpressure | Check Kafka broker health; increase partitions |
| Pod OOM / restart loop | Check memory; `kubectl rollout restart deployment/workload-simulator -n observability` |

## Escalation

- Unresolved after 30 minutes: page on-call engineer
- Simultaneous with `ErrorBudgetBurnRateFast`: immediate escalation

## Related Dashboards

- [Golden Signals](http://localhost:3000/d/golden-signals)
- [SLO Dashboard](http://localhost:3000/d/slo-dashboard)
- [Kubernetes Platform](http://localhost:3000/d/kubernetes-platform)
