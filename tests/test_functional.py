import os
import subprocess
import time
import json
import shutil
import tempfile
import pytest
from tools import percentile, read_latency_csv

BASE_PORT = 8001  # use a different port for fast functional tests


def start_server(mode, port=BASE_PORT, artifacts=None):
    cmd = ["python", "server_stub.py", "--mode", mode, "--port", str(port)]
    if artifacts:
        cmd += ["--artifacts", artifacts]
    proc = subprocess.Popen(cmd)
    # wait briefly for server to start
    time.sleep(0.5)
    return proc


def run_simple_load_test(port, num_requests=20, concurrency=5, output_csv="test_out.csv"):
    # use requests + ThreadPoolExecutor for a small deterministic synchronous load run
    import requests
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed

    API_URL = f"http://127.0.0.1:{port}/api"
    HEADERS = {"Content-Type": "application/json"}
    PAYLOAD = {"model": "example-model", "input": "test"}

    def call_api(request_id):
        start = time.perf_counter()
        try:
            r = requests.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=30.0)
            status = r.status_code
        except Exception:
            status = -1
        end = time.perf_counter()
        return {"request_id": request_id, "timestamp_ms": int(time.time() * 1000), "latency_ms": round((end - start) * 1000, 2), "status_code": status}

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(call_api, i) for i in range(num_requests)]
        for f in as_completed(futures):
            results.append(f.result())

    # write csv
    import csv
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["request_id", "timestamp_ms", "latency_ms", "status_code"])
        writer.writeheader()
        writer.writerows(results)
    return output_csv


def test_percentile_basic():
    data = [1, 2, 3, 4, 5]
    assert percentile(data, 0.5) == 3
    assert percentile(data, 0.0) == 1
    assert percentile(data, 0.99) == 5


def test_csv_and_payloads(tmp_path):
    artifacts = tmp_path / "art.json"
    proc = start_server("baseline", port=BASE_PORT, artifacts=str(artifacts))
    try:
        out = run_simple_load_test(port=BASE_PORT, num_requests=20, concurrency=5, output_csv=str(tmp_path / "out.csv"))
        data = read_latency_csv(out)
        assert len(data["rows"]) == 20
        assert all(k in data["rows"][0] for k in ["request_id", "timestamp_ms", "latency_ms", "status_code"]) 
    finally:
        proc.terminate()
        proc.wait()

    # the server should have dumped artifacts file
    assert artifacts.exists()
    with open(artifacts) as f:
        j = json.load(f)
        assert "payloads" in j and len(j["payloads"]) == 20


def test_inputs_identical_between_runs(tmp_path):
    # run two small runs and check payloads recorded are identical
    a1 = tmp_path / "a1.json"
    proc1 = start_server("baseline", port=BASE_PORT, artifacts=str(a1))
    try:
        run_simple_load_test(port=BASE_PORT, num_requests=10, concurrency=3, output_csv=str(tmp_path / "r1.csv"))
    finally:
        proc1.terminate()
        proc1.wait()

    a2 = tmp_path / "a2.json"
    proc2 = start_server("optimized", port=BASE_PORT, artifacts=str(a2))
    try:
        run_simple_load_test(port=BASE_PORT, num_requests=10, concurrency=3, output_csv=str(tmp_path / "r2.csv"))
    finally:
        proc2.terminate()
        proc2.wait()

    with open(a1) as f:
        p1 = json.load(f)["payloads"]
    with open(a2) as f:
        p2 = json.load(f)["payloads"]

    assert p1 == p2


def test_sla_gating_logic(tmp_path):
    # create a synthetic latency list and ensure SLA gating works
    lats_fail = [100, 120, 800, 900, 1200]
    p95_fail = percentile(lats_fail, 0.95)
    assert p95_fail >= 800

    lats_pass = [50, 60, 70, 80, 90, 400]
    p95_pass = percentile(lats_pass, 0.95)
    assert p95_pass < 800
