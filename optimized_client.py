#!/usr/bin/env python3
"""
Optimized load test client.

This script preserves the request semantics from `input.py` by importing
the constants defined there (API_URL, CONCURRENCY, TOTAL_REQUESTS, TIMEOUT_SECONDS,
HEADERS, PAYLOAD). It implements an optimization to reduce end-to-end latency by
increasing the HTTP connection pool limits used by httpx so that the client
does not artificially queue requests behind a small pool.

The CSV format is the same as `input.py` but the output file is `latency_optimized.csv`.
"""
import asyncio
import time
import csv
import sys

import httpx

# Import constants from input.py to ensure identical request semantics
try:
    import input as baseline
except Exception:
    print("Could not import input.py - ensure run_tests is executed from repository root.")
    raise


API_URL = getattr(baseline, "API_URL")
CONCURRENCY = getattr(baseline, "CONCURRENCY")
TOTAL_REQUESTS = getattr(baseline, "TOTAL_REQUESTS")
TIMEOUT_SECONDS = getattr(baseline, "TIMEOUT_SECONDS")
HEADERS = getattr(baseline, "HEADERS")
PAYLOAD = getattr(baseline, "PAYLOAD")

OUTPUT_CSV = "latency_optimized.csv"


async def call_api(client, semaphore, request_id):
    async with semaphore:
        start_time = time.perf_counter()
        status_code = None
        try:
            response = await client.post(
                API_URL,
                headers=HEADERS,
                json=PAYLOAD
            )
            status_code = response.status_code
        except Exception:
            status_code = -1
        end_time = time.perf_counter()

        return {
            "request_id": request_id,
            "timestamp_ms": int(time.time() * 1000),
            "latency_ms": round((end_time - start_time) * 1000, 2),
            "status_code": status_code,
        }


async def run_load_test():
    semaphore = asyncio.Semaphore(CONCURRENCY)

    # Optimization: increase connection pool limits so we don't bottleneck on
    # a small default pool. Set max_connections to match CONCURRENCY to avoid
    # excessive new-connection overhead while still preventing client-side
    # queuing.
    limits = httpx.Limits(max_connections=max(1, CONCURRENCY), max_keepalive_connections=CONCURRENCY)

    # We also enable HTTP/1.1 keep-alive by default (httpx enables it). No
    # protocol changes are made to keep semantics identical.
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS, limits=limits) as client:
        tasks = [
            call_api(client, semaphore, i)
            for i in range(TOTAL_REQUESTS)
        ]
        return await asyncio.gather(*tasks)


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    index = int(len(values) * p)
    return values[min(index, len(values) - 1)]


def main():
    results = asyncio.run(run_load_test())

    with open(OUTPUT_CSV, "w", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "request_id",
                "timestamp_ms",
                "latency_ms",
                "status_code",
            ],
        )
        writer.writeheader()
        writer.writerows(results)

    successful_latencies = [
        r["latency_ms"]
        for r in results
        if r["status_code"] == 200
    ]

    print("=== Optimized Latency Summary ===")
    print(f"P50: {percentile(successful_latencies, 0.50)} ms")
    print(f"P95: {percentile(successful_latencies, 0.95)} ms")
    print(f"P99: {percentile(successful_latencies, 0.99)} ms")
    print(f"Total requests: {len(results)}")
    print(f"Successful requests: {len(successful_latencies)}")


if __name__ == "__main__":
    main()
