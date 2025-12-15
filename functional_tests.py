import os
import subprocess
import time
import csv
import sys

# Set delay to 0 for instant response
os.environ["DELAY_MS"] = "0"

# Start stub server
stub_process = subprocess.Popen([sys.executable, "stub_server.py"])
time.sleep(2)  # Wait for server to start

try:
    # Run small baseline
    result = subprocess.run([sys.executable, "small_baseline.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Functional test failed: small_baseline.py failed")
        sys.exit(1)
    print(result.stdout)

    # Check baseline small csv
    with open("latency_baseline_small.csv", "r") as f:
        reader = csv.DictReader(f)
        results = list(reader)
    if len(results) != 10:
        print("Functional test failed: baseline small should have 10 results")
        sys.exit(1)
    for r in results:
        if r["status_code"] != "200":
            print("Functional test failed: all requests should be successful")
            sys.exit(1)
        if float(r["latency_ms"]) > 1000:  # Allow some processing time
            print("Functional test failed: latency too high")
            sys.exit(1)
    print("Baseline small test passed")

    # Run small optimized
    result = subprocess.run([sys.executable, "small_optimized.py"], capture_output=True, text=True)
    if result.returncode != 0:
        print("Functional test failed: small_optimized.py failed")
        sys.exit(1)
    print(result.stdout)

    # Check optimized small csv
    with open("latency_optimized_small.csv", "r") as f:
        reader = csv.DictReader(f)
        results = list(reader)
    if len(results) != 10:
        print("Functional test failed: optimized small should have 10 results")
        sys.exit(1)
    for r in results:
        if r["status_code"] != "200":
            print("Functional test failed: all requests should be successful")
            sys.exit(1)
        if float(r["latency_ms"]) > 1000:
            print("Functional test failed: latency too high")
            sys.exit(1)
    print("Optimized small test passed")

    # Test percentile function
    def percentile(values, p):
        if not values:
            return None
        values = sorted(values)
        index = int(len(values) * p)
        return values[min(index, len(values) - 1)]

    test_values = [1, 2, 3, 4, 5]
    assert percentile(test_values, 0.5) == 3
    assert percentile(test_values, 0.95) == 5
    assert percentile(test_values, 0.99) == 5
    print("Percentile function test passed")

    # Test SLA gating: assume P95 <=800 passes
    successful_latencies = [float(r["latency_ms"]) for r in results if r["status_code"] == "200"]
    p95 = percentile(successful_latencies, 0.95)
    if p95 > 800:
        print("Functional test failed: SLA not met")
        sys.exit(1)
    print("SLA gating test passed")

    print("All functional tests passed")

finally:
    stub_process.terminate()
    stub_process.wait()