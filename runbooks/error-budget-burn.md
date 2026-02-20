# Runbook: ErrorBudgetBurnRateFast / ErrorBudgetBurnRateSlow

**Alerts:** `ErrorBudgetBurnRateFast` (critical) / `ErrorBudgetBurnRateSlow` (warning)
**SLO Impact:** Direct — measures rate of error budget depletion

---

## What It Means

These alerts implement the **multiburn, multiwindow** SLO alerting pattern from the Google SRE Workbook:

| Alert | Burn Rate | Time Window | Budget Exhausted In |
|-------|-----------|-------------|---------------------|
| `ErrorBudgetBurnRateFast` | 14x | 1 hour | < 1 hour |
| `ErrorBudgetBurnRateSlow` | 3x | 6 hours | ~5 days |

For a **99.9% SLO** (0.1% error budget = 43.2 min/month):
- 14x burn rate = 14 × 0.1% = 1.4% error rate
- 3x burn rate = 3 × 0.1% = 0.3% error rate

## Triage Steps

```bash
# 1. Check error budget remaining
# Grafana: SLO Dashboard > Error Budget Remaining gauge

# 2. Check current burn rate
# Grafana: SLO Dashboard > Error Budget Burn Rate (1h vs 6h)

# 3. Identify root cause service
# Grafana: Golden Signals > Error Rate % (filter by service)

# 4. Correlate with recent deployments
kubectl rollout history deployment/workload-simulator -n observability
kubectl rollout history deployment/stream-processor -n observability

# 5. Check if it's a known load test
kubectl get pods -n observability -l app=workload-simulator -o wide
```

## Resolution

**Fast burn (< 1 hour to exhaustion):**
1. Identify and fix the root cause immediately
2. Consider a rollback if a recent deploy is the cause: `kubectl rollout undo deployment/workload-simulator -n observability`
3. Notify stakeholders of potential SLO breach

**Slow burn (days to exhaustion):**
1. Treat as warning; schedule a fix within 24 hours
2. Monitor trend — if burn rate increases, escalate

## Escalation

- `ErrorBudgetBurnRateFast`: Immediate page to on-call
- `ErrorBudgetBurnRateSlow`: Alert team lead; schedule postmortem if SLO is close to breach

## Related Dashboards

- [SLO Dashboard](http://localhost:3000/d/slo-dashboard)
- [Golden Signals](http://localhost:3000/d/golden-signals)
