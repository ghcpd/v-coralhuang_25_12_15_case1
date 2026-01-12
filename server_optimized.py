import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

HOST = "localhost"
PORT = 8000

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

class OptimizedHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api":
            self.send_response(404)
            self.end_headers()
            return
        # Simulate same processing time but allow concurrent handling
        time.sleep(0.3)  # 300ms
        length = int(self.headers.get('Content-Length', 0))
        _ = self.rfile.read(length)
        response = {"ok": True, "message": "optimized"}
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def run_server():
    server = ThreadedHTTPServer((HOST, PORT), OptimizedHandler)
    print(f"Optimized server listening on http://{HOST}:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
