import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
import threading
import socketserver


class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    # shared state assigned on server instance
    def do_POST(self):
        if self.path != "/api":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        try:
            data = json.loads(body.decode())
        except Exception:
            data = None

        ts = time.time()
        # record payload
        self.server._payloads.append(data)
        self.server._request_times.append(ts)

        # If artifacts path is set, persist after each request (helps deterministic tests)
        if getattr(self.server, "_artifacts", None):
            try:
                with open(self.server._artifacts, "w") as f:
                    json.dump({"payloads": self.server._payloads, "request_times": self.server._request_times}, f)
            except Exception:
                pass

        # simulate processing with concurrency limit
        sem = self.server._sem
        processing_ms = self.server._processing_ms
        mode = self.server._mode

        with sem:
            time.sleep(processing_ms / 1000.0)
            resp = {"ok": True, "mode": mode}
            resp_bytes = json.dumps(resp).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(resp_bytes)))
            self.end_headers()
            self.wfile.write(resp_bytes)

    def log_message(self, format, *args):
        # suppress default logging
        return


def save_artifacts(path, payloads, request_times):
    with open(path, "w") as f:
        json.dump({"payloads": payloads, "request_times": request_times}, f)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["baseline", "optimized"], default="baseline")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--artifacts", default=None, help="path to dump payloads and times on shutdown")
    args = parser.parse_args()

    if args.mode == "baseline":
        processing_ms = 350
        max_concurrent = 4
    else:
        # more aggressive optimization: simulate faster inference and large parallelism
        processing_ms = 10
        max_concurrent = 1000

    server = ThreadedHTTPServer(("127.0.0.1", args.port), Handler)
    server._payloads = []
    server._request_times = []
    server._mode = args.mode
    server._processing_ms = processing_ms
    server._sem = threading.BoundedSemaphore(max_concurrent)
    server._artifacts = args.artifacts

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        if args.artifacts:
            save_artifacts(args.artifacts, server._payloads, server._request_times)


if __name__ == "__main__":
    main()
