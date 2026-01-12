import time
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = "localhost"
PORT = 8000

class BaselineHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/api":
            self.send_response(404)
            self.end_headers()
            return
        # Simulate heavy synchronous processing
        time.sleep(0.3)  # 300ms
        # Read body to ensure request is handled properly
        length = int(self.headers.get('Content-Length', 0))
        _ = self.rfile.read(length)
        # Respond quickly after simulated work
        response = {"ok": True, "message": "baseline"}
        body = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        # Suppress logging for tests
        pass


def run_server():
    server = HTTPServer((HOST, PORT), BaselineHandler)
    print(f"Baseline server listening on http://{HOST}:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
