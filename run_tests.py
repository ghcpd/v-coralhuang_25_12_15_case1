import os
import subprocess
import time
import csv
import json
import sys

def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    index = int(len(values) * p)
    return values[min(index, len(values) - 1)]

# Run functional tests
print("Running functional verification tests...")
result = subprocess.run([sys.executable, "functional_tests.py"])
if result.returncode != 0:
    print("Functional tests failed")
    sys.exit(1)
print("Functional tests passed\n")

# Run performance tests
print("Running performance tests...")
os.environ["DELAY_MS"] = "1000"

# Start stub server
stub_process = subprocess.Popen([sys.executable, "stub_server.py"])
time.sleep(2)  # Wait for server

try:
    # Run baseline
    print("Running baseline load test...")
    result = subprocess.run([sys.executable, "input.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Baseline test failed")
        sys.exit(1)
    print(result.stdout)

    # Run optimized
    print("Running optimized load test...")
    result = subprocess.run([sys.executable, "optimized_load_test.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Optimized test failed")
        sys.exit(1)
    print(result.stdout)

    # Read results
    def read_csv(filename):
        with open(filename, "r") as f:
            reader = csv.DictReader(f)
            results = list(reader)
        successful_latencies = [float(r["latency_ms"]) for r in results if r["status_code"] == "200"]
        return {
            "total_requests": len(results),
            "successful_requests": len(successful_latencies),
            "p50": percentile(successful_latencies, 0.50),
            "p95": percentile(successful_latencies, 0.95),
            "p99": percentile(successful_latencies, 0.99)
        }

    baseline = read_csv("latency_baseline.csv")
    optimized = read_csv("latency_optimized.csv")

    comparison = {
        "baseline": baseline,
        "optimized": optimized,
        "improvement": {
            "p50": baseline["p50"] - optimized["p50"],
            "p95": baseline["p95"] - optimized["p95"],
            "p99": baseline["p99"] - optimized["p99"]
        }
    }

    with open("comparison.json", "w") as f:
        json.dump(comparison, f, indent=2)

    print("\n=== Before vs After Comparison ===")
    print(f"Baseline P95: {baseline['p95']} ms")
    print(f"Optimized P95: {optimized['p95']} ms")
    print(f"Improvement: {comparison['improvement']['p95']} ms")
    print(f"Total requests: {baseline['total_requests']} (baseline), {optimized['total_requests']} (optimized)")
    print(f"Successful requests: {baseline['successful_requests']} (baseline), {optimized['successful_requests']} (optimized)")

    # Check SLA
    sla_met = optimized["p95"] <= 800
    print(f"SLA (P95 <= 800 ms) met: {sla_met}")

    if not sla_met:
        print("SLA not met after optimization")
        sys.exit(1)

    print("All tests passed, SLA met")

finally:
    stub_process.terminate()
    stub_process.wait()