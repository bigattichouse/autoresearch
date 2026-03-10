#!/usr/bin/env python3
"""
Basic Taguchi Optimization Example

This example shows how to optimize hyperparameters using Taguchi arrays
in a typical autoresearch workflow.
"""

from ..taguchi_mode import run_taguchi_sweep

def main():
    """Run a basic hyperparameter optimization."""
    print("🚀 Basic Taguchi Optimization Example")
    print("=" * 50)
    
    # Define hyperparameters to optimize
    factors = {
        "DEPTH": ["6", "8", "10"],              # Model depth
        "MATRIX_LR": ["0.02", "0.04", "0.08"],  # Learning rate
        "WEIGHT_DECAY": ["0.1", "0.2", "0.3"],  # Regularization
    }
    
    print("Factors to optimize:")
    for factor, levels in factors.items():
        print(f"  {factor}: {levels}")
    
    print(f"\nFull factorial would need: {len(factors['DEPTH']) * len(factors['MATRIX_LR']) * len(factors['WEIGHT_DECAY'])} runs")
    print("Taguchi L9 array will use: 9 runs (67% savings)")
    
    # Uncomment to run actual optimization
    # optimal = run_taguchi_sweep(
    #     factors=factors,
    #     metric="val_bpb",
    #     higher_is_better=False
    # )
    # 
    # print(f"\n✅ Optimal configuration found:")
    # for factor, value in optimal.items():
    #     print(f"  {factor} = {value}")
    
    print("\n💡 To run this example:")
    print("1. Make sure you have train.py in your autoresearch directory")
    print("2. Uncomment the optimization code above")  
    print("3. Run: python basic_optimization.py")

if __name__ == "__main__":
    main()