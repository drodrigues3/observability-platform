"""
Load test script: Spikes traffic through the workload simulator
by patching environment variables via kubectl.

Usage:
    python scripts/load_test.py --target-rps 100 --duration 120

Watch the Grafana Golden Signals dashboard for HPA scaling events.
"""
import argparse
import json
import subprocess
import time
import sys


def kubectl_patch_env(namespace: str, deployment: str, env_var: str, value: str) -> bool:
    """Patch a single environment variable in a Deployment."""
    patch = json.dumps({
        "spec": {
            "template": {
                "spec": {
                    "containers": [{
                        "name": deployment,
                        "env": [{"name": env_var, "value": value}],
                    }]
                }
            }
        }
    })
    result = subprocess.run(
        ["kubectl", "patch", "deployment", deployment,
         "-n", namespace, "--patch", patch],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"  ERROR patching {deployment}: {result.stderr.strip()}")
        return False
    print(f"  Patched {deployment}: {env_var}={value}")
    return True


def get_hpa_status(namespace: str) -> str:
    result = subprocess.run(
        ["kubectl", "get", "hpa", "-n", namespace, "--no-headers"],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "(unavailable)"


def main() -> None:
    parser = argparse.ArgumentParser(description="Load test the observability platform")
    parser.add_argument("--namespace", default="observability")
    parser.add_argument("--deployment", default="workload-simulator")
    parser.add_argument("--target-rps", type=int, default=100, help="Events per second during load test")
    parser.add_argument("--error-rate", type=float, default=0.1, help="Error rate during load (0-1)")
    parser.add_argument("--duration", type=int, default=120, help="Duration in seconds")
    parser.add_argument("--baseline-rps", type=int, default=10, help="RPS after test ends")
    args = parser.parse_args()

    print(f"""
=== Load Test: Real-Time Observability Platform ===
Target:    {args.target_rps} events/sec for {args.duration}s
Error rate: {args.error_rate:.0%} (triggers HighErrorRate alert)
Namespace: {args.namespace}
Deployment: {args.deployment}

Watch in Grafana:
  - Golden Signals: Error Rate % and Request Rate (RPS)
  - Kubernetes Platform: HPA Current vs Desired Replicas
  - SLO Dashboard: Error Budget Burn Rate
""")

    # --- Ramp up ---
    print("=== RAMPING UP ===")
    kubectl_patch_env(args.namespace, args.deployment, "EVENTS_PER_SECOND", str(args.target_rps))
    kubectl_patch_env(args.namespace, args.deployment, "ERROR_RATE", str(args.error_rate))
    print(f"\nLoad running for {args.duration}s...\n")

    check_interval = 30
    for elapsed in range(check_interval, args.duration + check_interval, check_interval):
        time.sleep(min(check_interval, max(0, args.duration - (elapsed - check_interval))))
        print(f"[{elapsed}s] HPA status:")
        print(f"  {get_hpa_status(args.namespace)}")
        if elapsed >= args.duration:
            break

    # --- Ramp down ---
    print("\n=== RAMPING DOWN ===")
    kubectl_patch_env(args.namespace, args.deployment, "EVENTS_PER_SECOND", str(args.baseline_rps))
    kubectl_patch_env(args.namespace, args.deployment, "ERROR_RATE", "0.02")

    print("""
Load test complete!
- Wait ~5 minutes for HPA to scale down (stabilization window)
- Check SLO Dashboard to see error budget impact
- Save Grafana screenshots for portfolio documentation
""")


if __name__ == "__main__":
    main()
