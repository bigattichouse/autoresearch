#!/usr/bin/env python3
"""
Test script for core Taguchi functionality.

This script validates that the Taguchi implementation works correctly
including experiment generation, signal analysis, and SNR calculations.
"""

from ..signal_analysis import SignalAnalyzer
from .. import Experiment, Analyzer

def test_experiment_generation():
    """Test basic experiment generation with L9 array."""
    print("🧪 Testing Experiment Generation...")
    
    try:
        with Experiment() as exp:
            exp.add_factor('DEPTH', ['6', '8', '10'])
            exp.add_factor('MATRIX_LR', ['0.02', '0.04', '0.08'])
            exp.add_factor('WEIGHT_DECAY', ['0.1', '0.2', '0.3'])
            
            runs = exp.generate()
            assert len(runs) == 9, f"Expected 9 runs, got {len(runs)}"
            assert exp.array_type == "L9", f"Expected L9 array, got {exp.array_type}"
            
            # Verify all factors are present in each run
            for run in runs:
                assert 'DEPTH' in run['factors'], "Missing DEPTH factor"
                assert 'MATRIX_LR' in run['factors'], "Missing MATRIX_LR factor"
                assert 'WEIGHT_DECAY' in run['factors'], "Missing WEIGHT_DECAY factor"
            
            print(f"✅ Generated {len(runs)} runs using {exp.array_type} array")
            return True
            
    except Exception as e:
        print(f"❌ Experiment generation failed: {e}")
        return False

def test_signal_analysis():
    """Test signal analysis functionality."""
    print("📊 Testing Signal Analysis...")
    
    # Create realistic experimental data
    runs = [
        {'run_id': 1, 'factors': {'DEPTH': '6', 'MATRIX_LR': '0.02'}},
        {'run_id': 2, 'factors': {'DEPTH': '6', 'MATRIX_LR': '0.04'}},
        {'run_id': 3, 'factors': {'DEPTH': '8', 'MATRIX_LR': '0.02'}},
        {'run_id': 4, 'factors': {'DEPTH': '8', 'MATRIX_LR': '0.04'}},
    ]
    
    # Simulated validation loss results (lower is better)
    results = {1: 1.45, 2: 1.32, 3: 1.28, 4: 1.22}
    factors = {
        'DEPTH': ['6', '8'], 
        'MATRIX_LR': ['0.02', '0.04']
    }
    
    try:
        analyzer = SignalAnalyzer()
        analyzer.set_experimental_data(runs, results, factors)
        
        # Generate SNR report (lower loss is better)
        report = analyzer.generate_signal_report(higher_is_better=False)
        
        # Verify report contains key sections
        assert "SNR ANALYSIS" in report, "Missing SNR analysis section"
        assert "FACTOR" in report, "Missing factor analysis section"
        assert "DEPTH" in report, "Missing DEPTH factor analysis"
        assert "MATRIX_LR" in report, "Missing MATRIX_LR factor analysis"
        
        print("✅ Signal analysis report generated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Signal analysis test failed: {e}")
        return False

def test_analyzer_workflow():
    """Test the complete Analyzer workflow."""
    print("🔬 Testing Analyzer Workflow...")
    
    try:
        with Experiment() as exp:
            exp.add_factor('A', ['1', '2', '3'])
            exp.add_factor('B', ['low', 'high'])
            
            runs = exp.generate()
            
            with Analyzer(exp, metric_name="response") as analyzer:
                # Add some test results
                analyzer.add_result(1, 0.85)
                analyzer.add_result(2, 0.92) 
                analyzer.add_result(3, 0.78)
                
                # Test optimal recommendation
                optimal = analyzer.recommend_optimal(higher_is_better=True)
                assert isinstance(optimal, dict), "Optimal should return a dict"
                assert 'A' in optimal, "Missing factor A in optimal"
                assert 'B' in optimal, "Missing factor B in optimal"
                
                # Test summary
                summary = analyzer.summary()
                assert isinstance(summary, str), "Summary should return a string"
                assert len(summary) > 0, "Summary should not be empty"
                
                print("✅ Analyzer workflow completed successfully")
                return True
                
    except Exception as e:
        print(f"❌ Analyzer workflow test failed: {e}")
        return False

def main():
    """Run all core functionality tests."""
    print("🧪 Taguchi Core Functionality Test Suite")
    print("=" * 60)
    
    tests = [
        test_experiment_generation,
        test_signal_analysis,
        test_analyzer_workflow,
    ]
    
    passed = 0
    total = len(tests)
    
    for test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ Test {test_func.__name__} crashed: {e}")
    
    print("\n" + "=" * 60)
    print("📊 Core Functionality Test Results Summary")
    print(f"  - Passed: {passed}/{total}")
    print(f"  - Success rate: {passed/total*100:.1f}%")
    
    if passed == total:
        print("✅ All core functionality tests passed!")
        return True
    else:
        print("⚠️  Some tests failed. Check output above.")
        return False

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)