import csv
import json
from statistics import median

def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    index = int(len(values) * p)
    return values[min(index, len(values) - 1)]


def read_latency_csv(path):
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    latencies = [float(r["latency_ms"]) for r in rows]
    statuses = [int(r["status_code"]) for r in rows]
    return {"rows": rows, "latencies": latencies, "statuses": statuses}


def write_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, indent=2)
