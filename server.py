#!/usr/bin/env python3
"""
Lightweight local HTTP stub to simulate an inference API.

Usage:
  python server.py --port 8000 --processing 0.6

This server is intentionally simple and has no external dependencies.
It uses ThreadingHTTPServer so multiple requests can be handled concurrently.
"""
import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class StubHandler(BaseHTTPRequestHandler):
    server_version = "StubServer/0.1"

    def do_POST(self):
        # Only respond to the API path
        if self.path != "/api":
            self.send_response(404)
            self.end_headers()
            return

        # Read and ignore the request body (we want deterministic behavior)
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length:
            _ = self.rfile.read(content_length)

        # Simulate processing time (blocking sleep inside thread)
        # In 'baseline' mode we add an extra overhead to emulate an
        # unoptimized implementation (e.g. synchronization, queuing, or
        # per-request allocations) that increases observed latency.
        processing = getattr(self.server, "processing_time", 0.0)
        extra = 0.0
        if getattr(self.server, "mode", "optimized") == "baseline":
            # extra overhead to push baseline P95 above the SLA threshold
            extra = 0.35
        time.sleep(processing + extra)

        payload = {"result": "ok", "processing": self.server.processing_time}

        resp = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp)))
        self.end_headers()
        self.wfile.write(resp)

    def log_message(self, format, *args):
        # Keep server output minimal to avoid cluttering test output
        return


def run(port: int, processing_time: float, mode: str = "optimized"):
    """Run the stub server.

    mode: 'baseline' simulates an unoptimized implementation by adding an
    additional fixed overhead per request (to model queuing/synchronization
    inefficiencies). 'optimized' represents an improved server implementation
    without that extra overhead.
    """
    server = ThreadingHTTPServer(("127.0.0.1", port), StubHandler)
    server.processing_time = processing_time
    server.mode = mode
    print(f"[stub server] listening on http://127.0.0.1:{port}/api  (processing={processing_time}s, mode={mode})")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def main():
    parser = argparse.ArgumentParser(description="Start a simple inference stub server.")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--processing", type=float, default=0.6,
                        help="Processing time per request in seconds (float)")
    parser.add_argument("--mode", choices=("baseline", "optimized"), default="optimized",
                        help="Server mode: 'baseline' (adds overhead) or 'optimized' (no extra overhead)")
    args = parser.parse_args()
    run(args.port, args.processing, mode=args.mode)


if __name__ == "__main__":
    main()
