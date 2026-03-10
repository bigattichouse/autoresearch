#!/usr/bin/env python3
"""
SNR Analysis Demo

This example demonstrates the Signal-to-Noise Ratio analysis capabilities
that help understand factor importance and guide future experiments.
"""

from ..signal_analysis import SignalAnalyzer

def demo_snr_analysis():
    """Demonstrate SNR analysis with simulated data."""
    print("🔍 Signal-to-Noise Ratio Analysis Demo")
    print("=" * 60)
    
    # Simulate experimental data
    runs = [
        {'run_id': 1, 'factors': {'DEPTH': '6', 'MATRIX_LR': '0.02', 'WEIGHT_DECAY': '0.1'}},
        {'run_id': 2, 'factors': {'DEPTH': '6', 'MATRIX_LR': '0.04', 'WEIGHT_DECAY': '0.2'}},
        {'run_id': 3, 'factors': {'DEPTH': '6', 'MATRIX_LR': '0.08', 'WEIGHT_DECAY': '0.3'}},
        {'run_id': 4, 'factors': {'DEPTH': '8', 'MATRIX_LR': '0.02', 'WEIGHT_DECAY': '0.2'}},
        {'run_id': 5, 'factors': {'DEPTH': '8', 'MATRIX_LR': '0.04', 'WEIGHT_DECAY': '0.3'}},
        {'run_id': 6, 'factors': {'DEPTH': '8', 'MATRIX_LR': '0.08', 'WEIGHT_DECAY': '0.1'}},
        {'run_id': 7, 'factors': {'DEPTH': '10', 'MATRIX_LR': '0.02', 'WEIGHT_DECAY': '0.3'}},
        {'run_id': 8, 'factors': {'DEPTH': '10', 'MATRIX_LR': '0.04', 'WEIGHT_DECAY': '0.1'}},
        {'run_id': 9, 'factors': {'DEPTH': '10', 'MATRIX_LR': '0.08', 'WEIGHT_DECAY': '0.2'}},
    ]
    
    # Simulate results - MATRIX_LR has strong effect, DEPTH moderate, WEIGHT_DECAY weak  
    results = {
        1: 1.234,  # DEPTH=6, LR=0.02 (high loss - low LR)
        2: 1.187,  # DEPTH=6, LR=0.04 (better)
        3: 1.145,  # DEPTH=6, LR=0.08 (best LR)
        4: 1.198,  # DEPTH=8, LR=0.02 
        5: 1.156,  # DEPTH=8, LR=0.04
        6: 1.123,  # DEPTH=8, LR=0.08
        7: 1.189,  # DEPTH=10, LR=0.02
        8: 1.167,  # DEPTH=10, LR=0.04  
        9: 1.134,  # DEPTH=10, LR=0.08
    }
    
    factors = {
        'DEPTH': ['6', '8', '10'],
        'MATRIX_LR': ['0.02', '0.04', '0.08'],
        'WEIGHT_DECAY': ['0.1', '0.2', '0.3']
    }
    
    # Perform SNR analysis
    signal_analyzer = SignalAnalyzer()
    signal_analyzer.set_experimental_data(runs, results, factors)
    
    print("📊 Simulated experimental data:")
    print("   - 3 factors: DEPTH, MATRIX_LR, WEIGHT_DECAY")
    print("   - 9 runs (L9 orthogonal array)")
    print("   - Metric: val_bpb (lower is better)")
    print("   - MATRIX_LR has strong effect")
    print("   - DEPTH has moderate effect")  
    print("   - WEIGHT_DECAY has weak effect")
    print()
    
    # Generate full SNR report
    snr_report = signal_analyzer.generate_signal_report(higher_is_better=False)
    print(snr_report)
    
    # Get suggestions for next experiments
    suggestions = signal_analyzer.suggest_next_experiments()
    
    print("\n" + "=" * 60)
    print("INTERPRETING SNR ANALYSIS")
    print("=" * 60)
    
    print("📚 What SNR tells us:")
    print("   • SNR Range shows how much each factor affects the outcome")
    print("   • Higher SNR Range = More important factor")
    print("   • MATRIX_LR should have highest SNR range (strongest effect)")
    print("   • WEIGHT_DECAY should have lowest SNR range (weakest effect)")
    print()
    
    print("🎯 How to use this information:")
    print("   • Focus future experiments on high-SNR factors")
    print("   • Eliminate or fix low-SNR factors")
    print("   • Refine ranges around optimal levels for important factors")
    print("   • Study interactions between top factors")
    print()
    
    print("🔄 Next experiment suggestions:")
    print("   Based on this analysis, you might:")
    print("   1. Test more MATRIX_LR values around 0.08 (0.06, 0.08, 0.10)")
    print("   2. Fix WEIGHT_DECAY at its best level from this experiment")  
    print("   3. Test DEPTH values around the optimal range")
    print("   4. Study DEPTH × MATRIX_LR interactions")

def main():
    """Run the SNR analysis demo."""
    demo_snr_analysis()

if __name__ == "__main__":
    main()