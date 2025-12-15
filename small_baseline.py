import asyncio
import time
import csv
import httpx

API_URL = "http://localhost:8000/api"  # placeholder inference endpoint


CONCURRENCY = 2
TOTAL_REQUESTS = 10
TIMEOUT_SECONDS = 30.0

OUTPUT_CSV = "latency_baseline_small.csv"

HEADERS = {
    "Content-Type": "application/json"
}

PAYLOAD = {
    "model": "example-model",
    "input": "Generate a short explanation text for performance testing purposes."
}


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
            "status_code": status_code
        }


async def run_load_test():
    semaphore = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as client:
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
                "status_code"
            ]
        )
        writer.writeheader()
        writer.writerows(results)

    successful_latencies = [
        r["latency_ms"]
        for r in results
        if r["status_code"] == 200
    ]

    print("=== Baseline Small Latency Summary ===")
    print(f"P50: {percentile(successful_latencies, 0.50)} ms")
    print(f"P95: {percentile(successful_latencies, 0.95)} ms")
    print(f"P99: {percentile(successful_latencies, 0.99)} ms")
    print(f"Total requests: {len(results)}")
    print(f"Successful requests: {len(successful_latencies)}")


if __name__ == "__main__":
    main()