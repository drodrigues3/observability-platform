# Runbook: HighErrorRate

**Alert:** `HighErrorRate`
**Severity:** Critical
**SLO Impact:** Availability SLO — rapid error budget consumption

---

## What It Means

The error rate for one or more services has exceeded **5%** for the past **3 minutes**. This is a critical availability issue affecting a significant portion of requests.

## Impact

- ~5%+ of users receiving errors (5xx/4xx responses)
- Rapid consumption of monthly error budget (43.2 min at 99.9% SLO)
- At 100% error rate: budget exhausted in ~26 minutes

## Triage Steps

```bash
# 1. Check which service is affected (from alert labels)
kubectl get pods -n observability

# 2. See error breakdown by status code
# Grafana: Golden Signals > Errors by Status Code

# 3. Check stream-processor alert events
kubectl logs -l app=stream-processor -n observability --tail=200 | grep "HighErrorRate"

# 4. Check current ERROR_RATE env var
kubectl exec -it deployment/workload-simulator -n observability -- \
  printenv | grep ERROR_RATE

# 5. Check for OOMKilled containers
kubectl get events -n observability --field-selector reason=OOMKilling

# 6. Verify Kafka connectivity
kubectl exec -it kafka-0 -n kafka -- \
  kafka-topics.sh --list --bootstrap-server localhost:9092
```

## Common Causes & Fixes

| Cause | Fix |
|-------|-----|
| `ERROR_RATE` set too high | Update env var: `kubectl set env deployment/workload-simulator ERROR_RATE=0.02 -n observability` |
| Kafka DLQ growing | Check producer logs; restart if max retries exceeded |
| Pod crash loop | `kubectl rollout restart deployment/workload-simulator -n observability` |
| Load test in progress | Verify with scripts/load_test.py — may be intentional |

## Escalation

- Error rate > 50%: immediate escalation (full outage scenario)
- Simultaneous with `ErrorBudgetBurnRateFast`: page on-call immediately

## Related Dashboards

- [Golden Signals](http://localhost:3000/d/golden-signals)
- [SLO Dashboard](http://localhost:3000/d/slo-dashboard)
