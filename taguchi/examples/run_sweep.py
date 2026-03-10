#!/usr/bin/env python3
"""
Example script to run a Taguchi hyperparameter sweep using the platform-agnostic
taguchi_train.py script.

Usage:
    python taguchi/examples/run_sweep.py
"""

import os
from taguchi.taguchi_mode import run_taguchi_sweep

def main():
    # Define the hyperparameters and levels to optimize
    # Note: These must match variable names in taguchi_train.py
    factors = {
        "DEPTH": ["4", "8", "12"],
        "MATRIX_LR": ["0.02", "0.04", "0.08"],
        "WEIGHT_DECAY": ["0.1", "0.2", "0.3"],
        "WARMUP_RATIO": ["0.0", "0.05", "0.1"],
    }

    # Training configuration
    # Use the platform-agnostic script in the same directory
    example_dir = os.path.dirname(os.path.abspath(__file__))
    train_script = os.path.join(example_dir, "taguchi_train.py")
    
    config = {
        "training_timeout": 1200,  # 20 minutes (useful for CPU training)
        "training_command": [".venv/bin/python3", train_script],
        "config_file": train_script,
        "debug_mode": True,
        "max_retries": 0,
    }

    print("🚀 Starting Taguchi Hyperparameter Sweep...")
    print(f"📍 Using training script: {train_script}")
    
    optimal = run_taguchi_sweep(
        factors=factors,
        metric="val_bpb",
        higher_is_better=False,
        config=config
    )

    if optimal:
        print("\n✅ Sweep Complete!")
        print(f"Optimal configuration found: {optimal}")
    else:
        print("\n❌ Sweep failed to find an optimal configuration.")

if __name__ == "__main__":
    main()
