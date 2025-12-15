import argparse
import asyncio
import json
import random
import time
import os
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

app = FastAPI()

# Configuration may be provided via environment variables so that uvicorn's import of
# this module when launching the app picks up the right settings.
MODE = os.environ.get("SERVER_MODE", "baseline")
SEED = int(os.environ.get("SERVER_SEED", "123"))
LOG_FILE = os.environ.get("SERVER_LOG_FILE", "logs/requests.jsonl")

# Ensure deterministic randomness at import time
random.seed(SEED)

@app.post("/api")
async def api(request: Request):
    body = await request.json()

    # Configure per-mode latency distributions so baseline is slower than optimized
    if MODE == "baseline":
        # baseline has higher median and a small heavy tail
        if random.random() < 0.05:
            latency_ms = random.uniform(900, 1400)
        else:
            latency_ms = random.uniform(600, 1000)
        # baseline simulates some extra CPU overhead (blocking sleep)
        time.sleep(latency_ms / 1000.0)
    else:
        # optimized has lower median and fewer tail events
        if random.random() < 0.02:
            latency_ms = random.uniform(300, 600)
        else:
            latency_ms = random.uniform(80, 220)
        await asyncio.sleep(latency_ms / 1000.0)

    entry = {
        "timestamp_ms": int(time.time() * 1000),
        "latency_ms": round(latency_ms, 2),
        "body": body,
    }

    # Append to log file
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")

    return JSONResponse({"result": "ok"})


@app.get("/health")
async def health():
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "optimized"], required=True)
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--seed", type=int, default=123)
    parser.add_argument("--log-file", type=str, default="logs/requests.jsonl")
    args = parser.parse_args()

    # When uvicorn imports this module (server_stub:app) it will pick up configuration
    # from environment variables. Set them here before launching.
    os.environ["SERVER_MODE"] = args.mode
    os.environ["SERVER_SEED"] = str(args.seed)
    os.environ["SERVER_LOG_FILE"] = args.log_file

    # Clear or create log file
    with open(args.log_file, "w", encoding="utf-8") as f:
        f.write("")

    uvicorn.run("server_stub:app", host="127.0.0.1", port=args.port, log_level="info")
