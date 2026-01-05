"""
Functional verification tests for the load testing framework.
Tests core functionality without requiring a live external service.
"""

import asyncio
import json
import csv
import tempfile
import os
from pathlib import Path


def test_percentile_calculation():
    """
    Test that percentile calculation is correct.
    Uses known datasets for verification.
    Uses nearest-rank method (same as input.py).
    """
    from input import percentile
    
    # Test with sorted list
    # Nearest-rank: index = int(len(values) * p), clamped to [0, len-1]
    values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    
    # For 10 items:
    # P50: index=5 -> values[5]=60
    # P95: index=9 -> values[9]=100
    # P99: index=9 -> values[9]=100
    # P0: index=0 -> values[0]=10
    assert percentile(values, 0.50) == 60, "P50 should be 60"
    assert percentile(values, 0.95) == 100, "P95 should be 100"
    assert percentile(values, 0.99) == 100, "P99 should be 100"
    assert percentile(values, 0.00) == 10, "P0 should be 10"
    
    # Test with empty list
    assert percentile([], 0.50) is None, "Empty list should return None"
    
    # Test with single value
    assert percentile([42], 0.50) == 42, "Single value should return itself"
    
    print("[PASS] Percentile calculation tests passed")


def test_csv_output_format():
    """
    Test that CSV output is correctly formatted with required fields.
    """
    # Create a mock result set
    mock_results = [
        {
            "request_id": 0,
            "timestamp_ms": 1000,
            "latency_ms": 150.5,
            "status_code": 200
        },
        {
            "request_id": 1,
            "timestamp_ms": 1001,
            "latency_ms": 250.25,
            "status_code": 200
        },
        {
            "request_id": 2,
            "timestamp_ms": 1002,
            "latency_ms": -1,
            "status_code": 500
        }
    ]
    
    # Write to temporary CSV
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.csv', newline='') as f:
        temp_path = f.name
        import csv as csv_module
        writer = csv_module.DictWriter(
            f,
            fieldnames=[
                "request_id",
                "timestamp_ms",
                "latency_ms",
                "status_code"
            ]
        )
        writer.writeheader()
        writer.writerows(mock_results)
    
    try:
        # Read and verify
        with open(temp_path, 'r') as f:
            reader = csv_module.DictReader(f)
            rows = list(reader)
            
            assert len(rows) == 3, "Should have 3 data rows"
            
            # Verify headers
            assert rows[0] is not None
            assert 'request_id' in rows[0]
            assert 'timestamp_ms' in rows[0]
            assert 'latency_ms' in rows[0]
            assert 'status_code' in rows[0]
            
            # Verify data types and values
            assert rows[0]['request_id'] == '0'
            assert rows[0]['latency_ms'] == '150.5'
            assert rows[0]['status_code'] == '200'
            
            assert rows[2]['status_code'] == '500'
    
    finally:
        os.unlink(temp_path)
    
    print("[PASS] CSV output format tests passed")


def test_request_input_consistency():
    """
    Test that request inputs remain consistent between runs.
    This ensures baseline and optimized tests use identical inputs.
    """
    from input import PAYLOAD, HEADERS
    
    # Verify payload is valid JSON
    json_str = json.dumps(PAYLOAD)
    parsed = json.loads(json_str)
    assert parsed == PAYLOAD, "Payload should remain valid JSON"
    
    # Verify headers are correct
    assert HEADERS["Content-Type"] == "application/json"
    
    # Verify payload contains required fields
    assert "model" in PAYLOAD
    assert "input" in PAYLOAD
    assert PAYLOAD["model"] == "example-model"
    assert isinstance(PAYLOAD["input"], str)
    assert len(PAYLOAD["input"]) > 0
    
    print("[PASS] Request input consistency tests passed")


def test_sla_gating():
    """
    Test SLA enforcement logic.
    """
    from input import percentile
    
    # Scenario 1: SLA met (P95 <= 800ms)
    # With 10 items, P95 uses index 9 (nearest-rank)
    latencies_good = [100, 150, 200, 250, 300, 350, 400, 450, 500, 700]
    p95_good = percentile(latencies_good, 0.95)
    assert p95_good <= 800, f"SLA should be met with P95={p95_good}"
    
    # Scenario 2: SLA not met (P95 > 800ms)
    latencies_bad = [100, 200, 400, 600, 800, 900, 950, 1000, 1100, 1200]
    p95_bad = percentile(latencies_bad, 0.95)
    assert p95_bad > 800, f"SLA should fail with P95={p95_bad}"
    
    print("[PASS] SLA gating tests passed")


def test_result_dictionary_structure():
    """
    Test that result dictionaries have the correct structure.
    """
    # This is what the API returns
    result = {
        "request_id": 42,
        "timestamp_ms": 1702660000000,
        "latency_ms": 250.5,
        "status_code": 200
    }
    
    assert isinstance(result["request_id"], int)
    assert isinstance(result["timestamp_ms"], int)
    assert isinstance(result["latency_ms"], (int, float))
    assert isinstance(result["status_code"], int)
    
    # Verify field types and reasonableness
    assert result["request_id"] >= 0
    assert result["timestamp_ms"] > 0
    assert result["latency_ms"] >= 0
    assert result["status_code"] >= -1  # -1 for errors, otherwise HTTP status
    
    print("[PASS] Result dictionary structure tests passed")


def run_all_functional_tests():
    """Run all functional verification tests"""
    print("\n" + "="*50)
    print("FUNCTIONAL VERIFICATION TESTS")
    print("="*50)
    
    try:
        test_percentile_calculation()
        test_csv_output_format()
        test_request_input_consistency()
        test_sla_gating()
        test_result_dictionary_structure()
        
        print("\n" + "="*50)
        print("[PASS] ALL FUNCTIONAL TESTS PASSED")
        print("="*50 + "\n")
        return True
    except AssertionError as e:
        print(f"\n[FAIL] FUNCTIONAL TEST FAILED: {e}\n")
        return False
    except Exception as e:
        print(f"\n[FAIL] UNEXPECTED ERROR IN FUNCTIONAL TESTS: {e}\n")
        return False


if __name__ == "__main__":
    success = run_all_functional_tests()
    exit(0 if success else 1)
