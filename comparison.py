"""
Performance comparison and analysis.
Compares baseline vs optimized test results and generates reports.
"""

import csv
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Tuple


def load_csv_results(filepath: str) -> List[Dict]:
    """Load latency results from CSV file"""
    if not os.path.exists(filepath):
        return []
    
    results = []
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            results.append({
                "request_id": int(row["request_id"]),
                "timestamp_ms": int(row["timestamp_ms"]),
                "latency_ms": float(row["latency_ms"]),
                "status_code": int(row["status_code"])
            })
    return results


def percentile(values: List[float], p: float) -> Optional[float]:
    """Calculate percentile"""
    if not values:
        return None
    values = sorted(values)
    index = int(len(values) * p)
    return values[min(index, len(values) - 1)]


def analyze_results(results: List[Dict]) -> Dict:
    """Analyze latency results and compute statistics"""
    if not results:
        return {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "p50": None,
            "p95": None,
            "p99": None,
            "min": None,
            "max": None,
            "mean": None,
            "sla_met": False
        }
    
    successful_latencies = [
        r["latency_ms"]
        for r in results
        if r["status_code"] == 200
    ]
    
    failed_count = len(results) - len(successful_latencies)
    
    analysis = {
        "total_requests": len(results),
        "successful_requests": len(successful_latencies),
        "failed_requests": failed_count,
        "p50": percentile(successful_latencies, 0.50),
        "p95": percentile(successful_latencies, 0.95),
        "p99": percentile(successful_latencies, 0.99),
        "min": min(successful_latencies) if successful_latencies else None,
        "max": max(successful_latencies) if successful_latencies else None,
        "mean": sum(successful_latencies) / len(successful_latencies) if successful_latencies else None,
    }
    
    # SLA: P95 <= 800ms
    analysis["sla_met"] = analysis["p95"] is not None and analysis["p95"] <= 800
    
    return analysis


def generate_comparison_report(
    baseline_path: str,
    optimized_path: str,
    output_path: str = "comparison_report.json"
) -> Tuple[Dict, bool]:
    """
    Generate comprehensive comparison report.
    Returns: (report_dict, sla_met_flag)
    """
    
    print("\nLoading baseline results...")
    baseline_results = load_csv_results(baseline_path)
    baseline_analysis = analyze_results(baseline_results)
    
    print("Loading optimized results...")
    optimized_results = load_csv_results(optimized_path)
    optimized_analysis = analyze_results(optimized_results)
    
    # Calculate improvements
    p95_baseline = baseline_analysis["p95"]
    p95_optimized = optimized_analysis["p95"]
    
    if p95_baseline and p95_optimized:
        p95_improvement_ms = p95_baseline - p95_optimized
        p95_improvement_pct = (p95_improvement_ms / p95_baseline) * 100
    else:
        p95_improvement_ms = None
        p95_improvement_pct = None
    
    report = {
        "sla_threshold_ms": 800,
        "baseline": baseline_analysis,
        "optimized": optimized_analysis,
        "improvements": {
            "p50_delta_ms": optimized_analysis["p50"] - baseline_analysis["p50"] if baseline_analysis["p50"] and optimized_analysis["p50"] else None,
            "p95_delta_ms": p95_improvement_ms,
            "p95_improvement_pct": p95_improvement_pct,
            "p99_delta_ms": optimized_analysis["p99"] - baseline_analysis["p99"] if baseline_analysis["p99"] and optimized_analysis["p99"] else None,
        }
    }
    
    sla_met = optimized_analysis["sla_met"]
    
    # Write report to JSON
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    return report, sla_met


def print_comparison_report(report: Dict, sla_met: bool):
    """Print formatted comparison report"""
    print("\n" + "="*70)
    print("PERFORMANCE COMPARISON REPORT")
    print("="*70)
    
    baseline = report["baseline"]
    optimized = report["optimized"]
    improvements = report["improvements"]
    
    checkmark = "[PASS]"
    xmark = "[FAIL]"
    
    print("\nBASELINE (Before Optimization)")
    print("-" * 70)
    print(f"  Total Requests:       {baseline['total_requests']}")
    print(f"  Successful Requests:  {baseline['successful_requests']}")
    print(f"  Failed Requests:      {baseline['failed_requests']}")
    print(f"  P50 Latency:          {baseline['p50']:.2f} ms" if baseline['p50'] else f"  P50 Latency:          N/A")
    print(f"  P95 Latency:          {baseline['p95']:.2f} ms" if baseline['p95'] else f"  P95 Latency:          N/A")
    print(f"  P99 Latency:          {baseline['p99']:.2f} ms" if baseline['p99'] else f"  P99 Latency:          N/A")
    print(f"  Min Latency:          {baseline['min']:.2f} ms" if baseline['min'] else f"  Min Latency:          N/A")
    print(f"  Max Latency:          {baseline['max']:.2f} ms" if baseline['max'] else f"  Max Latency:          N/A")
    print(f"  Mean Latency:         {baseline['mean']:.2f} ms" if baseline['mean'] else f"  Mean Latency:         N/A")
    print(f"  SLA Met (P95<=800ms): {checkmark if baseline['sla_met'] else xmark}")
    
    print("\nOPTIMIZED (After Optimization)")
    print("-" * 70)
    print(f"  Total Requests:       {optimized['total_requests']}")
    print(f"  Successful Requests:  {optimized['successful_requests']}")
    print(f"  Failed Requests:      {optimized['failed_requests']}")
    print(f"  P50 Latency:          {optimized['p50']:.2f} ms" if optimized['p50'] else f"  P50 Latency:          N/A")
    print(f"  P95 Latency:          {optimized['p95']:.2f} ms" if optimized['p95'] else f"  P95 Latency:          N/A")
    print(f"  P99 Latency:          {optimized['p99']:.2f} ms" if optimized['p99'] else f"  P99 Latency:          N/A")
    print(f"  Min Latency:          {optimized['min']:.2f} ms" if optimized['min'] else f"  Min Latency:          N/A")
    print(f"  Max Latency:          {optimized['max']:.2f} ms" if optimized['max'] else f"  Max Latency:          N/A")
    print(f"  Mean Latency:         {optimized['mean']:.2f} ms" if optimized['mean'] else f"  Mean Latency:         N/A")
    print(f"  SLA Met (P95<=800ms): {checkmark if optimized['sla_met'] else xmark}")
    
    print("\nPERFORMANCE IMPROVEMENTS")
    print("-" * 70)
    if improvements["p95_delta_ms"] is not None:
        print(f"  P95 Improvement:      {improvements['p95_delta_ms']:.2f} ms ({improvements['p95_improvement_pct']:.1f}%)")
    if improvements["p50_delta_ms"] is not None:
        delta = improvements["p50_delta_ms"]
        sign = "DOWN" if delta < 0 else "UP"
        print(f"  P50 Delta:            {sign} {abs(delta):.2f} ms")
    if improvements["p99_delta_ms"] is not None:
        delta = improvements["p99_delta_ms"]
        sign = "DOWN" if delta < 0 else "UP"
        print(f"  P99 Delta:            {sign} {abs(delta):.2f} ms")
    
    print("\nSLA STATUS")
    print("-" * 70)
    print(f"  SLA Threshold:        P95 <= {report['sla_threshold_ms']} ms")
    if sla_met:
        print(f"  Result:               [PASS] SLA MET - P95 optimized to {optimized['p95']:.2f} ms")
    else:
        print(f"  Result:               [FAIL] SLA NOT MET - P95 is {optimized['p95']:.2f} ms (need <= {report['sla_threshold_ms']} ms)")
    
    print("="*70 + "\n")
    
    return sla_met


if __name__ == "__main__":
    import sys
    
    baseline_csv = "latency_baseline.csv"
    optimized_csv = "latency_optimized.csv"
    report_json = "comparison_report.json"
    
    if os.path.exists(baseline_csv) and os.path.exists(optimized_csv):
        report, sla_met = generate_comparison_report(baseline_csv, optimized_csv, report_json)
        print_comparison_report(report, sla_met)
        sys.exit(0 if sla_met else 1)
    else:
        print(f"Error: Missing test result files")
        print(f"  Expected: {baseline_csv}")
        print(f"  Expected: {optimized_csv}")
        sys.exit(1)
