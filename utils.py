"""
Utility helpers for reading CSV results and computing latency metrics.
"""
import csv
from typing import List, Dict, Any, Optional


def read_results_csv(path: str) -> List[Dict[str, Any]]:
    rows = []
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            # normalize types
            try:
                latency = float(r.get("latency_ms", "0"))
            except Exception:
                latency = None
            try:
                status = int(r.get("status_code", "-1"))
            except Exception:
                status = -1

            rows.append({
                "request_id": r.get("request_id"),
                "timestamp_ms": int(r.get("timestamp_ms", "0")),
                "latency_ms": latency,
                "status_code": status,
            })
    return rows


def percentile(values: List[float], p: float) -> Optional[float]:
    if not values:
        return None
    values = sorted(values)
    index = int(len(values) * p)
    return values[min(index, len(values) - 1)]


def compute_metrics(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total = len(rows)
    successful = [r["latency_ms"] for r in rows if r["status_code"] == 200 and r["latency_ms"] is not None]
    metrics = {
        "total_requests": total,
        "successful_requests": len(successful),
        "p50": percentile(successful, 0.50),
        "p95": percentile(successful, 0.95),
        "p99": percentile(successful, 0.99),
    }
    return metrics
