#!/usr/bin/env python3
"""
Advanced Taguchi Optimization Example

This example shows advanced features like custom configuration,
environment validation, and error handling.
"""

from ..taguchi_mode import run_taguchi_sweep
from .. import TaguchiConfig

def main():
    """Run advanced hyperparameter optimization with custom configuration."""
    print("🚀 Advanced Taguchi Optimization Example")
    print("=" * 50)
    
    # Validate environment first
    print("1. Validating environment...")
    try:
        diagnostics = validate_environment()
        if not diagnostics['taguchi_installation']['cli_found']:
            print("❌ Taguchi CLI not found! Please install it first.")
            return
        print("✅ Environment validated")
    except Exception as e:
        print(f"❌ Environment validation failed: {e}")
        return
    
    # Custom configuration
    print("\n2. Setting up custom configuration...")
    config = TaguchiConfig(
        cli_timeout=120,         # Longer timeout for complex arrays
        debug_mode=True,         # Enable debug output
        max_retries=2,           # Retry failed commands
    )
    print(f"✅ Configuration: timeout={config.cli_timeout}s, debug={config.debug_mode}")
    
    # Advanced factor definition
    print("\n3. Defining optimization factors...")
    factors = {
        # Architecture factors
        "DEPTH": ["6", "8", "10", "12"],
        "HEAD_DIM": ["64", "128", "256"],
        "WINDOW_PATTERN": ["L", "SSSL", "SSSS"],
        
        # Learning factors  
        "MATRIX_LR": ["0.02", "0.04", "0.08"],
        "EMBEDDING_LR": ["0.4", "0.6", "0.8"],
        "WEIGHT_DECAY": ["0.1", "0.2", "0.3"],
        
        # Training factors
        "DEVICE_BATCH_SIZE": ["64", "128", "256"],
        "WARMUP_RATIO": ["0.0", "0.1", "0.2"],
    }
    
    total_factorial = 1
    for factor, levels in factors.items():
        total_factorial *= len(levels)
        print(f"  {factor}: {levels}")
    
    print(f"\nFull factorial would need: {total_factorial} runs")
    print("Taguchi array will use: ~27-64 runs (95%+ savings)")
    
    # Uncomment to run actual optimization
    # print("\n4. Running Taguchi optimization...")
    # try:
    #     optimal = run_taguchi_sweep(
    #         factors=factors,
    #         metric="val_bpb",
    #         higher_is_better=False,
    #         config=config
    #     )
    #     
    #     print(f"\n✅ Optimal configuration found:")
    #     for factor, value in optimal.items():
    #         print(f"  {factor} = {value}")
    #         
    # except Exception as e:
    #     print(f"❌ Optimization failed: {e}")
    #     if hasattr(e, 'suggestions'):
    #         print("Suggestions:")
    #         for suggestion in e.suggestions:
    #             print(f"  💡 {suggestion}")
    
    print("\n💡 To run this example:")
    print("1. Make sure you have train.py in your autoresearch directory")
    print("2. Set TAGUCHI_CLI_PATH if needed")
    print("3. Uncomment the optimization code above")  
    print("4. Run: python advanced_optimization.py")

if __name__ == "__main__":
    main()