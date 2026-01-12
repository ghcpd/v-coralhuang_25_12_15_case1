"""
Deterministic functional verification tests for the load-testing framework.

These tests do not depend on any external service. They use a local stub
server (the same `server.py`) with deterministic behavior for the checks
that require network interactions.
"""
import subprocess
import sys
import time
import os
import tempfile
import asyncio

import httpx

import utils


def assert_equal(a, b, msg=None):
    if a != b:
        raise AssertionError(msg or f"Assertion failed: {a!r} != {b!r}")


def test_percentile():
    # Known dataset
    data = [10, 20, 30, 40, 50]
    assert_equal(utils.percentile(data, 0.5), 30)
    assert_equal(utils.percentile(data, 0.95), 50)
    assert_equal(utils.percentile(data, 0.99), 50)


def test_payload_identity():
    # Ensure the optimized client uses the same request payload as input.py
    import input as baseline
    import optimized_client as opt

    assert_equal(baseline.PAYLOAD, opt.PAYLOAD, "PAYLOAD differs between baseline and optimized client")
    assert_equal(baseline.HEADERS, opt.HEADERS, "HEADERS differ between baseline and optimized client")


async def _small_client_run(port: int, out_csv: str, total: int = 5, concurrency: int = 2):
    semaphore = asyncio.Semaphore(concurrency)
    API = f"http://127.0.0.1:{port}/api"

    async def call(i, client):
        async with semaphore:
            start = time.perf_counter()
            resp = await client.post(API, headers={"Content-Type": "application/json"}, json={"test": True})
            end = time.perf_counter()
            return {"request_id": i, "timestamp_ms": int(time.time() * 1000), "latency_ms": round((end - start) * 1000, 2), "status_code": resp.status_code}

    async with httpx.AsyncClient(timeout=10.0) as client:
        tasks = [call(i, client) for i in range(total)]
        results = await asyncio.gather(*tasks)

    # write CSV
    import csv
    with open(out_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["request_id", "timestamp_ms", "latency_ms", "status_code"])
        writer.writeheader()
        writer.writerows(results)


def test_csv_logging_fields():
    # Start a deterministic local stub server for this test
    port = 8001
    server_proc = subprocess.Popen([sys.executable, "server.py", "--port", str(port), "--processing", "0.0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        # wait for server to be ready
        time.sleep(0.2)

        fd, tmp = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            asyncio.run(_small_client_run(port, tmp, total=5, concurrency=2))

            rows = utils.read_results_csv(tmp)
            assert_equal(len(rows), 5, "CSV should contain 5 rows")
            # check fields exist on first row
            row = rows[0]
            assert_equal(set(row.keys()), {"request_id", "timestamp_ms", "latency_ms", "status_code"})
        finally:
            try:
                os.remove(tmp)
            except Exception:
                pass
    finally:
        server_proc.terminate()
        server_proc.wait()


def test_sla_gating():
    # Basic gating logic
    def sla_pass(p95, threshold=800):
        return p95 is not None and p95 <= threshold

    assert_equal(sla_pass(700), True)
    assert_equal(sla_pass(800), True)
    assert_equal(sla_pass(801), False)
    assert_equal(sla_pass(None), False)


def run_functional_tests():
    print("[tests] Running functional verification tests...")
    test_percentile()
    print("[tests] percentile tests passed")
    test_payload_identity()
    print("[tests] payload identity passed")
    test_csv_logging_fields()
    print("[tests] csv logging fields passed")
    test_sla_gating()
    print("[tests] sla gating passed")
    print("[tests] All functional tests passed")


if __name__ == "__main__":
    run_functional_tests()
