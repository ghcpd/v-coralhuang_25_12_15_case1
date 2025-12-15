import asyncio
import time
import csv
import aiohttp

API_URL = "http://localhost:8000/api"

BATCH_SIZE = 10
CONCURRENCY = 20  # concurrency for batches
TOTAL_REQUESTS = 400
TIMEOUT_SECONDS = 30.0

OUTPUT_CSV = "latency_optimized.csv"

HEADERS = {
    "Content-Type": "application/json"
}

PAYLOAD_BASE = {
    "model": "example-model",
    "input": "Generate a short explanation text for performance testing purposes."
}


async def call_api_batch(client, semaphore, batch_id, batch_size):
    async with semaphore:
        payload = {
            "model": "example-model",
            "inputs": [PAYLOAD_BASE["input"]] * batch_size
        }
        start_time = time.perf_counter()
        status_code = None
        try:
            async with client.post(
                API_URL,
                headers=HEADERS,
                json=payload
            ) as response:
                status_code = response.status
                data = await response.json()
        except Exception:
            status_code = -1
            data = None
        end_time = time.perf_counter()

        latency_ms = round((end_time - start_time) * 1000, 2)

        results = []
        for i in range(batch_size):
            request_id = batch_id * BATCH_SIZE + i
            results.append({
                "request_id": request_id,
                "timestamp_ms": int(time.time() * 1000),
                "latency_ms": latency_ms,
                "status_code": status_code
            })
        return results


async def run_load_test():
    semaphore = asyncio.Semaphore(CONCURRENCY)
    connector = aiohttp.TCPConnector(limit=0)  # Allow unlimited connections for better performance
    timeout = aiohttp.ClientTimeout(total=TIMEOUT_SECONDS)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as client:
        num_batches = (TOTAL_REQUESTS + BATCH_SIZE - 1) // BATCH_SIZE
        tasks = [
            call_api_batch(client, semaphore, i, min(BATCH_SIZE, TOTAL_REQUESTS - i * BATCH_SIZE))
            for i in range(num_batches)
        ]
        batch_results = await asyncio.gather(*tasks)
        results = [item for sublist in batch_results for item in sublist]
        return results


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

    print("=== Optimized Latency Summary ===")
    print(f"P50: {percentile(successful_latencies, 0.50)} ms")
    print(f"P95: {percentile(successful_latencies, 0.95)} ms")
    print(f"P99: {percentile(successful_latencies, 0.99)} ms")
    print(f"Total requests: {len(results)}")
    print(f"Successful requests: {len(successful_latencies)}")


if __name__ == "__main__":
    main()