"""
Mock HTTP server for functional testing without external dependencies.
Simulates a realistic inference API with configurable latency.
"""

import asyncio
import json
import random
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn


# Configuration for realistic latency simulation
BASE_LATENCY_MS = 250  # Base processing time
JITTER_MS = 50  # Random jitter ±
PERCENTILE_95_LATENCY = 800  # Target P95 before optimization
PERCENTILE_95_LATENCY_OPTIMIZED = 350  # Target P95 after optimization


class MockServerConfig:
    """Configuration for mock server behavior"""
    def __init__(self, optimized: bool = False):
        self.optimized = optimized
        self.request_count = 0

    def get_simulated_latency(self) -> float:
        """Simulate realistic latency distribution"""
        # Generate latency with occasional peaks (realistic distribution)
        if random.random() < 0.08:  # 8% of requests are slow
            # Slow requests - cause P95 to be high in baseline
            if self.optimized:
                latency_ms = random.uniform(300, 500)
            else:
                latency_ms = random.uniform(950, 1300)  # Increased for baseline
        else:
            # Normal requests
            if self.optimized:
                latency_ms = random.gauss(200, 30)
            else:
                latency_ms = random.gauss(450, 90)  # Increased baseline latency
        
        # Ensure non-negative
        return max(latency_ms, 10)


_server_config = MockServerConfig(optimized=False)


async def api_handler(request):
    """
    Mock API endpoint handler.
    Simulates latency and returns successful response.
    """
    global _server_config
    
    # Simulate processing latency
    latency = _server_config.get_simulated_latency()
    await asyncio.sleep(latency / 1000.0)  # Convert ms to seconds
    
    _server_config.request_count += 1
    
    return JSONResponse({
        "status": "success",
        "model": "example-model",
        "output": "Generated explanation text for performance testing.",
        "request_count": _server_config.request_count
    })


async def config_handler(request):
    """Endpoint to configure server behavior"""
    global _server_config
    
    data = await request.json()
    optimized = data.get("optimized", False)
    _server_config = MockServerConfig(optimized=optimized)
    
    return JSONResponse({
        "status": "configured",
        "optimized": optimized
    })


async def reset_handler(request):
    """Reset server state"""
    global _server_config
    optimized = _server_config.optimized
    _server_config = MockServerConfig(optimized=optimized)
    
    return JSONResponse({
        "status": "reset",
        "request_count": 0
    })


# Create Starlette app
routes = [
    Route("/api", api_handler, methods=["POST"]),
    Route("/config", config_handler, methods=["POST"]),
    Route("/reset", reset_handler, methods=["POST"]),
]

app = Starlette(routes=routes)


def run_server(port: int = 8000):
    """Run the mock server"""
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")


if __name__ == "__main__":
    run_server()
