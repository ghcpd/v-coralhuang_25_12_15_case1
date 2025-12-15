import argparse
import csv
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from requests.adapters import HTTPAdapter

API_URL = "http://127.0.0.1:8000/api"
CONCURRENCY = 20
TOTAL_REQUESTS = 400
TIMEOUT_SECONDS = 30.0
OUTPUT_CSV = "latency_baseline.csv"
HEADERS = {"Content-Type": "application/json"}
PAYLOAD = {"model": "example-model", "input": "Generate a short explanation text for performance testing purposes."}


def call_api(session, i):
    start = time.perf_counter()
    try:
        r = session.post(API_URL, headers=HEADERS, json=PAYLOAD, timeout=TIMEOUT_SECONDS)
        status = r.status_code
    except Exception:
        status = -1
    end = time.perf_counter()
    return {
        "request_id": i,
        "timestamp_ms": int(time.time() * 1000),
        "latency_ms": round((end - start) * 1000, 2),
        "status_code": status
    }


def run(output_csv=OUTPUT_CSV, total=TOTAL_REQUESTS, concurrency=CONCURRENCY):
    # Use a single Session with a tuned HTTPAdapter for connection pooling
    # create a session per worker to maximize connection reuse per thread
    sessions = []
    for _ in range(concurrency):
        s = requests.Session()
        adapter = HTTPAdapter(pool_connections=concurrency * 2, pool_maxsize=concurrency * 2)
        s.mount("http://", adapter)
        sessions.append(s)

    results = []
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(call_api, sessions[i % concurrency], i) for i in range(total)]
        for f in as_completed(futures):
            results.append(f.result())

    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["request_id", "timestamp_ms", "latency_ms", "status_code"])
        writer.writeheader()
        writer.writerows(results)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=OUTPUT_CSV)
    parser.add_argument("--total", type=int, default=TOTAL_REQUESTS)
    parser.add_argument("--concurrency", type=int, default=CONCURRENCY)
    args = parser.parse_args()
    run(output_csv=args.output, total=args.total, concurrency=args.concurrency)
