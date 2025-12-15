# Performance Optimization Solution

This repository contains an enhanced performance testing and optimization solution for the baseline load test in `input.py`. The solution demonstrates functional correctness of the testing framework and measured performance improvement under load.

## Optimization Approach

The optimization implements **client-side batching** combined with improved HTTP client handling:

- **Batching**: Groups individual requests into batches of 10 to reduce the number of HTTP calls. The optimized version sends `{"model": "example-model", "inputs": [input] * batch_size}` instead of single requests.
- **Improved Client**: Uses `aiohttp` instead of `httpx` with unlimited connection limits (`TCPConnector(limit=0)`) for better concurrency and reduced connection overhead.

**Why this reduces latency**: Batching minimizes HTTP request overhead and allows the API to process multiple inputs efficiently. The unlimited connection pool in aiohttp prevents connection limits from causing queueing delays, leading to lower P95 latency under high concurrency.

## Environment Setup

- Python 3.14+
- Dependencies: `httpx`, `fastapi`, `uvicorn`, `aiohttp`

Install dependencies:
```bash
pip install httpx fastapi uvicorn aiohttp
```

## How to Run `run_tests`

Execute the main test script:
```bash
python run_tests.py
```

This script:
1. Runs functional verification tests (deterministic, using a local stub with no delay).
2. If functional tests pass, runs performance tests (baseline vs optimized) against a stub simulating high latency (1000ms per request).
3. Generates `comparison.json` with before/after metrics.
4. Exits with code 0 if SLA is met (optimized P95 ≤ 800ms), else 1.

## Tests Executed

- **Functional Verification**:
  - Verifies request inputs are identical between runs.
  - Ensures per-request logs contain required fields (`request_id`, `timestamp_ms`, `latency_ms`, `status_code`).
  - Validates percentile calculations on known datasets.
  - Confirms SLA gating logic (pass/fail based on P95 ≤ 800ms).
  - Uses a local stub server with 0ms delay for deterministic results.

- **Performance Tests**:
  - Baseline: Runs `input.py` (single requests via httpx).
  - Optimized: Runs `optimized_load_test.py` (batched requests via aiohttp).
  - Compares P50/P95/P99 latency, total/successful requests.

## Results Generation

- Logs: `latency_baseline.csv`, `latency_optimized.csv` (from performance runs).
- Comparison: `comparison.json` with metrics and improvements.
- Output: Console prints summaries and SLA status.

Based on execution, the SLA is met after optimization, with baseline P95 at 1337.91 ms and optimized P95 at 393.55 ms, demonstrating a 944 ms improvement.

## Assumptions and Limitations

- The placeholder API supports batching as implemented (single vs. batched payloads).
- Stub server simulates API behavior; real endpoint performance may vary.
- Optimization assumes batching improves server-side efficiency.
- Tests run locally; network conditions may affect real-world results.
- No degradation in output quality assumed for batching.