import os
import subprocess
import time
import json
import csv
import urllib.request
import shutil

ROOT = os.path.dirname(os.path.dirname(__file__))
INPUT_PY = os.path.join(ROOT, "input.py")
SERVER_PY = os.path.join(ROOT, "server_stub.py")
TEST_LOGS = os.path.join(ROOT, "tests", "logs")
TEST_RESULTS = os.path.join(ROOT, "tests", "results")

os.makedirs(TEST_LOGS, exist_ok=True)
os.makedirs(TEST_RESULTS, exist_ok=True)

TOTAL_REQUESTS = 400


def wait_for_health(port=8000, timeout=10.0):
    deadline = time.time() + timeout
    url = f"http://127.0.0.1:{port}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                if r.status == 200:
                    return True
        except Exception:
            time.sleep(0.1)
    return False


def start_server(mode, port=8000, seed=123, log_file=None):
    if log_file is None:
        log_file = os.path.join(TEST_LOGS, f"requests_{mode}.jsonl")
    cmd = ["python", SERVER_PY, "--mode", mode, "--port", str(port), "--seed", str(seed), "--log-file", log_file]
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    ok = wait_for_health(port=port, timeout=10.0)
    if not ok:
        proc.terminate()
        raise RuntimeError("Server failed to start")
    return proc, log_file


def stop_server(proc):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()


def read_latencies_from_csv(path):
    latencies = []
    total = 0
    successes = 0
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total += 1
            try:
                lat = float(r["latency_ms"])
            except Exception:
                lat = None
            if r["status_code"] == '200' or r["status_code"] == 200:
                successes += 1
                if lat is not None:
                    latencies.append(lat)
    return latencies, total, successes


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    index = int(len(values) * p)
    return values[min(index, len(values) - 1)]


def read_bodies(log_path):
    bodies = []
    with open(log_path, encoding="utf-8") as f:
        for line in f:
            try:
                j = json.loads(line)
                bodies.append(j.get("body"))
            except Exception:
                pass
    return bodies


def run_client_and_collect(mode, log_file):
    # run input.py which writes latency_baseline.csv
    r = subprocess.run(["python", INPUT_PY], cwd=ROOT)
    if r.returncode != 0:
        raise RuntimeError("input.py failed")
    src = os.path.join(ROOT, "latency_baseline.csv")
    if not os.path.exists(src):
        raise RuntimeError("CSV not produced")
    dest = os.path.join(TEST_RESULTS, f"{mode}_latency.csv")
    shutil.move(src, dest)
    # copy log produced by server
    shutil.copy(log_file, os.path.join(TEST_RESULTS, os.path.basename(log_file)))
    return dest, os.path.join(TEST_RESULTS, os.path.basename(log_file))


def test_percentile_basic():
    data = [1, 2, 3, 4, 5]
    assert percentile(data, 0.5) == 3
    assert percentile(data, 0.95) == 5


import asyncio
import httpx


def small_client_run(concurrency=10, total=40, timeout=10.0):
    # Lightweight client reusing input.py semantics but much smaller for unit tests
    semaphore = asyncio.Semaphore(concurrency)
    payload = {"model": "example-model", "input": "Generate a short explanation text for performance testing purposes."}

    async def call_api(client, sem, request_id):
        async with sem:
            start = time.perf_counter()
            status = None
            try:
                r = await client.post("http://127.0.0.1:8000/api", json=payload, timeout=timeout)
                status = r.status_code
            except Exception:
                status = -1
            end = time.perf_counter()
            return {"request_id": request_id, "latency_ms": round((end - start) * 1000, 2), "status_code": status}

    async def run_all():
        async with httpx.AsyncClient() as client:
            tasks = [call_api(client, semaphore, i) for i in range(total)]
            return await asyncio.gather(*tasks)

    return asyncio.run(run_all())


def test_small_end_to_end_baseline_and_optimized():
    # Baseline small run
    baseline_proc, baseline_log = start_server("baseline", log_file=os.path.join(TEST_LOGS, "requests_baseline_small.jsonl"))
    try:
        results = small_client_run(concurrency=5, total=40, timeout=15.0)
    finally:
        stop_server(baseline_proc)

    # persist results to CSV for checking
    baseline_csv = os.path.join(TEST_RESULTS, "baseline_small_latency.csv")
    with open(baseline_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["request_id", "latency_ms", "status_code"])
        writer.writeheader()
        writer.writerows(results)

    # Optimized small run
    opt_proc, opt_log = start_server("optimized", log_file=os.path.join(TEST_LOGS, "requests_optimized_small.jsonl"))
    try:
        results_opt = small_client_run(concurrency=5, total=40, timeout=15.0)
    finally:
        stop_server(opt_proc)

    opt_csv = os.path.join(TEST_RESULTS, "optimized_small_latency.csv")
    with open(opt_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["request_id", "latency_ms", "status_code"])
        writer.writeheader()
        writer.writerows(results_opt)

    # Compute percentiles
    b_lats = [r["latency_ms"] for r in results if r["status_code"] == 200]
    a_lats = [r["latency_ms"] for r in results_opt if r["status_code"] == 200]

    assert len(b_lats) > 0
    assert len(a_lats) > 0

    b_p95 = percentile(b_lats, 0.95)
    a_p95 = percentile(a_lats, 0.95)

    assert a_p95 <= 800
    assert a_p95 < b_p95


def test_integration_run_input_py_slow():
    # Integration test that runs the full input.py; mark as slow and optional via env var
    if os.environ.get("RUN_SLOW_INTEGRATION", "false").lower() != "true":
        # skip
        return
    # Baseline full run
    baseline_proc, baseline_log = start_server("baseline", log_file=os.path.join(TEST_LOGS, "requests_baseline.jsonl"))
    try:
        subprocess.run(["python", INPUT_PY], cwd=ROOT, check=True)
    finally:
        stop_server(baseline_proc)

    # Optimized full run
    opt_proc, opt_log = start_server("optimized", log_file=os.path.join(TEST_LOGS, "requests_optimized.jsonl"))
    try:
        subprocess.run(["python", INPUT_PY], cwd=ROOT, check=True)
    finally:
        stop_server(opt_proc)

    # If we reach here, the integration test ran.

