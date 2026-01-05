"""
Mock server manager - starts and stops the mock server for testing.
"""

import subprocess
import time
import requests
import sys
from pathlib import Path


def wait_for_server(url: str, timeout: int = 10, interval: float = 0.5) -> bool:
    """Wait for server to be ready"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.post(url, timeout=1)
            if response.status_code in [200, 400, 404, 500]:  # Server responded
                return True
        except:
            pass
        time.sleep(interval)
    return False


def configure_server(optimized: bool = False):
    """Configure mock server behavior"""
    try:
        response = requests.post(
            "http://localhost:8000/config",
            json={"optimized": optimized},
            timeout=5
        )
        return response.status_code == 200
    except:
        return False


def reset_server():
    """Reset server state"""
    try:
        response = requests.post(
            "http://localhost:8000/reset",
            timeout=5
        )
        return response.status_code == 200
    except:
        return False


def start_mock_server() -> subprocess.Popen:
    """Start the mock server in a subprocess"""
    script_dir = Path(__file__).parent
    mock_server_path = script_dir / "mock_server.py"
    
    print("Starting mock server...")
    proc = subprocess.Popen(
        [sys.executable, str(mock_server_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to be ready
    if wait_for_server("http://localhost:8000/api", timeout=15):
        print("[PASS] Mock server started and ready")
        return proc
    else:
        print("[FAIL] Failed to start mock server")
        proc.terminate()
        raise RuntimeError("Mock server failed to start")


def stop_mock_server(proc: subprocess.Popen):
    """Stop the mock server"""
    if proc:
        print("Stopping mock server...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[PASS] Mock server stopped")


if __name__ == "__main__":
    # Test script
    proc = start_mock_server()
    try:
        print("Server running. Press Ctrl+C to stop.")
        time.sleep(10)
    except KeyboardInterrupt:
        pass
    finally:
        stop_mock_server(proc)
