# Performance Testing and Optimization

This workspace adds an enhanced performance testing harness and optimization experiment that preserves the original `input.py` baseline.

## What I added
- `server_stub.py` — local FastAPI-based stub server with two modes:
  - `baseline`: smaller worker pool and slower per-request time (simulates a slow inference service)
  - `optimized`: larger worker pool and faster processing time
- `tools.py` — helper functions for reading CSVs and computing percentiles
- `tests/test_functional.py` — deterministic functional tests (pytest)
- `run_tests` — orchestration script that:
  1. Runs functional tests
  2. Starts baseline server and runs `input.py` to produce baseline CSV
  3. Starts optimized server and runs `input.py` to produce optimized CSV
  4. Produces `compare_results.json` and exits with non-zero code if SLA not met
- `requirements.txt` — needed Python packages

## Optimization approach
- The baseline server limits concurrency (small semaphore) and has a longer per-request processing time, which causes queueing and increases tail latency under high load.
- The optimized server increases the allowed concurrent processing and reduces per-request service time. This reduces queuing and tail latency without changing request semantics or outputs.

## How to run
1. Create a virtual environment and install dependencies:
   ```bash
   python -m venv .venv
   .\.venv\Scripts\activate
   pip install -r requirements.txt
   ```
2. Run the orchestrator (this executes functional tests, baseline & optimized load tests):
   ```bash
   python run_tests
   ```

The script will produce `baseline_results.csv`, `optimized_results.csv`, and `compare_results.json`.

- Exit code 0: SLA met after optimization
- Exit code 2: SLA not met after optimization

## Tests executed
- `pytest` functional tests (fast, deterministic) validate:
  - Percentile calculation
  - CSV format
  - Payload consistency between runs
  - SLA gating logic

## Assumptions and limitations
- The real inference endpoint is a placeholder; we use a deterministic local stub server to simulate latency and concurrency effects.
- The optimization demonstrated is server-side (simulating architectural improvements like increased worker pool and faster handlers). The comparisons are performed using identical client inputs and the same `input.py` runner.
- All conclusions are based on the measured results produced by running the provided scripts.
