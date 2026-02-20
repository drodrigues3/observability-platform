"""
End-to-end smoke test for the observability pipeline.
Validates that all components are healthy and data is flowing end-to-end.

Usage:
    # Port-forward required services first, then:
    python tests/smoke_test.py
"""
import sys
import subprocess
import urllib.request
import urllib.error
from typing import Optional


def kubectl(*args: str) -> tuple[int, str, str]:
    result = subprocess.run(
        ["kubectl", *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def check_pods_running(namespace: str, label: str) -> bool:
    rc, stdout, stderr = kubectl(
        "get", "pods", "-n", namespace, "-l", label,
        "-o", "jsonpath={.items[*].status.phase}"
    )
    if rc != 0:
        print(f"  FAIL: kubectl error: {stderr.strip()}")
        return False
    phases = stdout.split()
    if not phases:
        print(f"  FAIL: No pods found for label={label} in ns={namespace}")
        return False
    all_running = all(p == "Running" for p in phases)
    if not all_running:
        print(f"  FAIL: Not all pods running: {phases}")
        return False
    print(f"  OK: {len(phases)} pod(s) Running")
    return True


def check_endpoint(url: str, expected_status: int = 200) -> bool:
    try:
        req = urllib.request.urlopen(url, timeout=10)
        if req.status == expected_status:
            print(f"  OK: {url} -> {req.status}")
            return True
        print(f"  FAIL: {url} -> {req.status} (expected {expected_status})")
        return False
    except urllib.error.URLError as e:
        print(f"  FAIL: {url} unreachable: {e}")
        return False


def check_metrics_content(url: str, expected_metric: str) -> bool:
    """Verify that a specific metric name appears in /metrics output."""
    try:
        req = urllib.request.urlopen(url, timeout=10)
        content = req.read().decode("utf-8")
        if expected_metric in content:
            print(f"  OK: metric '{expected_metric}' found in /metrics")
            return True
        print(f"  FAIL: metric '{expected_metric}' NOT found in /metrics")
        return False
    except urllib.error.URLError as e:
        print(f"  FAIL: {url} unreachable: {e}")
        return False


def run_smoke_tests() -> None:
    results: list[bool] = []

    print("\n=== Smoke Test: Real-Time Observability Platform ===\n")

    print("1. Checking workload-simulator pods...")
    results.append(check_pods_running("observability", "app=workload-simulator"))

    print("2. Checking stream-processor pods...")
    results.append(check_pods_running("observability", "app=stream-processor"))

    print("3. Checking metrics-bridge pods...")
    results.append(check_pods_running("observability", "app=metrics-bridge"))

    print("4. Checking Prometheus pods...")
    results.append(check_pods_running("monitoring", "app.kubernetes.io/name=prometheus"))

    print("5. Checking Grafana pods...")
    results.append(check_pods_running("monitoring", "app.kubernetes.io/name=grafana"))

    print("6. Checking metrics-bridge /healthz (port-forward required)...")
    results.append(check_endpoint("http://localhost:8080/healthz"))

    print("7. Checking metrics-bridge /readyz...")
    results.append(check_endpoint("http://localhost:8080/readyz"))

    print("8. Checking /metrics endpoint has workload data...")
    results.append(check_metrics_content("http://localhost:8080/metrics", "workload_requests_total"))

    print("9. Checking Prometheus health...")
    results.append(check_endpoint("http://localhost:9090/-/healthy"))

    print("10. Checking Grafana health...")
    results.append(check_endpoint("http://localhost:3000/api/health"))

    passed = sum(results)
    total = len(results)
    print(f"\n=== Results: {passed}/{total} checks passed ===")

    if passed < total:
        print("FAILED — some checks did not pass. See output above for details.")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED — pipeline is healthy end-to-end!")
        sys.exit(0)


if __name__ == "__main__":
    run_smoke_tests()
