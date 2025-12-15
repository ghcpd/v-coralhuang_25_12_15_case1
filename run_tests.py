#!/usr/bin/env python3
"""
Main test runner - orchestrates all tests and generates final results.
Executes:
1. Functional verification tests (deterministic, no external service)
2. Baseline performance test (using mock server)
3. Optimized performance test (using mock server)
4. Comparison and SLA validation

Exit code: 0 if SLA met, 1 if not met or errors occur
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from server_manager import start_mock_server, stop_mock_server, configure_server, reset_server
from functional_tests import run_all_functional_tests


def run_baseline_test():
    """Run baseline performance test"""
    print("\n" + "="*70)
    print("BASELINE PERFORMANCE TEST (Before Optimization)")
    print("="*70)
    
    try:
        # Reset server for baseline (unoptimized)
        reset_server()
        configure_server(optimized=False)
        
        # Run input.py
        result = subprocess.run(
            [sys.executable, "input.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print("[FAIL] Baseline test failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
        
        print("[PASS] Baseline test completed")
        return True
        
    except Exception as e:
        print(f"✗ Baseline test error: {e}")
        return False


def run_optimized_test():
    """Run optimized performance test"""
    print("\n" + "="*70)
    print("OPTIMIZED PERFORMANCE TEST (After Optimization)")
    print("="*70)
    
    try:
        # Reset server for optimized test
        reset_server()
        configure_server(optimized=True)
        
        # Run optimized_test.py
        result = subprocess.run(
            [sys.executable, "optimized_test.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print(result.stdout)
        
        if result.returncode != 0:
            print(f"[FAIL] Optimized test failed")
            if result.stderr:
                print(f"Error: {result.stderr}")
            return False
        
        print("[PASS] Optimized test completed")
        return True
        
    except Exception as e:
        print(f"✗ Optimized test error: {e}")
        return False


def run_comparison():
    """Run comparison analysis"""
    print("\n" + "="*70)
    print("COMPARISON AND ANALYSIS")
    print("="*70)
    
    try:
        result = subprocess.run(
            [sys.executable, "comparison.py"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent
        )
        
        print(result.stdout)
        
        if result.stderr and "Traceback" in result.stderr:
            print(f"Error: {result.stderr}")
            return False
        
        # Return True if comparison was successful (exit code 0 means SLA met)
        return result.returncode == 0
        
    except Exception as e:
        print(f"✗ Comparison error: {e}")
        return False


def main():
    """Main test execution"""
    print("\n" + "="*70)
    print("PERFORMANCE OPTIMIZATION TEST SUITE")
    print("="*70)
    
    test_dir = Path(__file__).parent
    os.chdir(test_dir)
    
    # Step 1: Functional tests (no external service needed)
    print("\n[1/5] Running functional verification tests...")
    functional_ok = run_all_functional_tests()
    
    if not functional_ok:
        print("\n[FAIL] Functional tests failed - aborting")
        return 1
    
    # Step 2-4: Performance tests (need mock server)
    mock_server = None
    try:
        # Start mock server
        print("[2/5] Starting mock server...")
        mock_server = start_mock_server()
        
        # Small delay to ensure server is fully ready
        time.sleep(1)
        
        # Step 3: Baseline test
        print("[3/5] Running baseline performance test...")
        baseline_ok = run_baseline_test()
        
        if not baseline_ok:
            print("\n[FAIL] Baseline test failed")
            return 1
        
        # Step 4: Optimized test
        print("[4/5] Running optimized performance test...")
        optimized_ok = run_optimized_test()
        
        if not optimized_ok:
            print("\n[FAIL] Optimized test failed")
            return 1
        
    finally:
        if mock_server:
            stop_mock_server(mock_server)
    
    # Step 5: Comparison
    print("[5/5] Running comparison and analysis...")
    sla_met = run_comparison()
    
    # Final summary
    print("\n" + "="*70)
    if sla_met:
        print("[SUCCESS] SLA REQUIREMENT MET (P95 <= 800 ms)")
        print("="*70 + "\n")
        return 0
    else:
        print("[FAILURE] SLA REQUIREMENT NOT MET (P95 > 800 ms)")
        print("="*70 + "\n")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
