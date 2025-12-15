import subprocess
import sys
import time
import os
import csv
import json
import shutil
import threading
from contextlib import contextmanager
import asyncio
from statistics import mean

# Import the input module to access helpers for tests
import input

# Paths
BASELINE_SERVER = os.path.join(os.path.dirname(__file__), "server_baseline.py")
OPTIMIZED_SERVER = os.path.join(os.path.dirname(__file__), "server_optimized.py")

# Output filenames
BASELINE_CSV = "latency_baseline.csv"
OPTIMIZED_CSV = "latency_optimized.csv"
COMPARISON_JSON = "comparison.json"

# SLA threshold for P95 in ms
SLA_P95_MS = 800

@contextmanager
def run_server(server_path):
    """Start a server subprocess and ensure it is terminated.
    Waits until server responds to a health-check POST.
    """
    # Use the same interpreter as current python
    proc = subprocess.Popen([sys.executable, server_path], cwd=os.path.dirname(server_path),
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        # Wait for server to start listening
        timeout = 10
        start = time.time()
        while True:
            if proc.poll() is not None:
                # server exited prematurely; show output and raise
                out = proc.stdout.read()
                raise RuntimeError(f"Server process exited early: {out}")
            try:
                # Try simple health-check via HTTP POST
                import httpx
                with httpx.Client(timeout=2) as client:
                    r = client.post("http://localhost:8000/api", json={})
                    if r.status_code == 200:
                        break
            except Exception:
                pass
            if time.time() - start > timeout:
                proc.terminate()
                out = proc.stdout.read()
                raise TimeoutError(f"Server failed to start within {timeout}s: {out}")
            time.sleep(0.1)
        yield proc
    finally:
        # Terminate the server
        if proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        # Drain output
        proc.stdout.close()


def run_input_main():
    """Run input.py as a subprocess to ensure outputs and side effects are identical to baseline behavior."""
    proc = subprocess.run([sys.executable, "input.py"], cwd=os.path.dirname(__file__))
    if proc.returncode != 0:
        raise RuntimeError("input.py failed with return code %s" % proc.returncode)


def parse_csv(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        return [row for row in reader]


def compute_metrics(records):
    # records: list of dicts with latency_ms and status_code
    latencies = [float(r["latency_ms"]) for r in records if int(r.get("status_code", 0)) == 200]
    total = len(records)
    success = len(latencies)
    func = input.percentile
    return {
        "p50": func(latencies, 0.50),
        "p95": func(latencies, 0.95),
        "p99": func(latencies, 0.99),
        "total_requests": total,
        "successful_requests": success,
    }


def run_performance_test(server_path, output_csv):
    # Starts the server, runs input.py to produce CSV, renames CSV to output_csv
    with run_server(server_path) as proc:
        # Run the load test
        start = time.time()
        run_input_main()
        duration = time.time() - start
        # Move produced CSV
        default_csv = os.path.join(os.path.dirname(__file__), "latency_baseline.csv")
        if not os.path.exists(default_csv):
            raise FileNotFoundError("Expected output CSV not found: %s" % default_csv)
        shutil.move(default_csv, output_csv)
        return duration


def functional_tests():
    # tests for percentile and request structure
    # Test percentile correctness
    assert input.percentile([], 0.5) is None
    assert input.percentile([1, 2, 3, 4, 5], 0.5) == 3
    assert input.percentile([1, 2, 3, 4, 5], 0.95) == 5

    # Test run_load_test returns expected fields and consistent inputs
    # Monkeypatch httpx.AsyncClient.post to record payloads
    import httpx
    recorded = []
    class FakeResponse:
        def __init__(self):
            self.status_code = 200
    async def fake_post(self, url, headers=None, json=None):
        recorded.append(json)
        return FakeResponse()

    original_post = httpx.AsyncClient.post
    httpx.AsyncClient.post = fake_post
    try:
        results = asyncio.run(input.run_load_test())
    finally:
        httpx.AsyncClient.post = original_post

    assert len(results) == input.TOTAL_REQUESTS
    # Payload consistent across all requests
    assert all(req == input.PAYLOAD for req in recorded)
    # Each result must contain required keys
    for r in results:
        assert set(r.keys()) >= {"request_id", "timestamp_ms", "latency_ms", "status_code"}

    # Ensure main creates CSV with expected fields
    run_input_main()
    assert os.path.exists("latency_baseline.csv")
    rows = parse_csv("latency_baseline.csv")
    assert len(rows) == input.TOTAL_REQUESTS
    for r in rows:
        for k in ("request_id", "timestamp_ms", "latency_ms", "status_code"):
            assert k in r

    # Clean up
    if os.path.exists("latency_baseline.csv"):
        os.remove("latency_baseline.csv")


def main():
    print("Running functional verification tests...")
    functional_tests()
    print("Functional tests passed")

    # Run baseline performance
    print("Running baseline performance test...")
    baseline_time = run_performance_test(BASELINE_SERVER, BASELINE_CSV)
    baseline_records = parse_csv(BASELINE_CSV)
    baseline_metrics = compute_metrics(baseline_records)

    print(f"Baseline duration: {baseline_time:.1f}s")

    # Run optimized performance
    print("Running optimized performance test...")
    optimized_time = run_performance_test(OPTIMIZED_SERVER, OPTIMIZED_CSV)
    optimized_records = parse_csv(OPTIMIZED_CSV)
    optimized_metrics = compute_metrics(optimized_records)

    print(f"Optimized duration: {optimized_time:.1f}s")

    # Produce comparison JSON
    comparison = {
        "baseline": baseline_metrics,
        "optimized": optimized_metrics,
    }
    # Determine SLA success
    comparison["sla_met"] = optimized_metrics.get("p95") is not None and optimized_metrics["p95"] <= SLA_P95_MS
    with open(COMPARISON_JSON, "w") as f:
        json.dump(comparison, f, indent=2)

    # Print human-friendly summary
    print("\n===== Summary =====")
    print("Baseline P50/P95/P99:")
    print(f"  P50: {baseline_metrics['p50']} ms")
    print(f"  P95: {baseline_metrics['p95']} ms")
    print(f"  P99: {baseline_metrics['p99']} ms")
    print("Optimized P50/P95/P99:")
    print(f"  P50: {optimized_metrics['p50']} ms")
    print(f"  P95: {optimized_metrics['p95']} ms")
    print(f"  P99: {optimized_metrics['p99']} ms")

    if comparison["sla_met"]:
        print("✅ SLA met (P95 <= 800 ms)")
    else:
        print("❌ SLA NOT met (P95 > 800 ms)")

    # Exit code reflects SLA
    sys.exit(0 if comparison["sla_met"] else 1)


if __name__ == "__main__":
    main()
