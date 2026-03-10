# Taguchi Hyperparameter Optimization for Autoresearch

## What is This?

Taguchi arrays let you find optimal hyperparameters with **67-94% fewer experiments** than trying every combination. Instead of running 81 experiments to test 4 factors at 3 levels each, you only need 9 carefully chosen experiments that give you the same insights.

**How Taguchi Arrays Work**: Traditional "full factorial" experiments test every possible combination of your hyperparameters, which grows exponentially (3 factors × 3 levels each = 27 experiments). Taguchi orthogonal arrays are mathematically designed grids that test only strategic combinations while maintaining statistical balance - every factor level appears the same number of times and is evenly paired with levels of other factors. This orthogonal property lets you isolate each factor's individual effect on your metric, so you can find optimal settings with a fraction of the experiments. The method comes from quality engineering where it's used to optimize manufacturing processes, but works excellently for ML hyperparameter tuning.

## Quick Example

**Traditional approach** (testing all combinations):
- DEPTH: [6, 8, 10] 
- MATRIX_LR: [0.02, 0.04, 0.08]  
- WEIGHT_DECAY: [0.1, 0.2, 0.3]
- **Total experiments needed: 3 × 3 × 3 = 27 runs**

**Taguchi approach** (L9 orthogonal array):
- Same 3 factors, same 3 levels each
- **Total experiments needed: 9 runs**
- **Savings: 67% fewer experiments**
- **Result: Finds the same optimal configuration**

## Installation

You'll need the Taguchi library from `bigattichouse/taguchi`. The Python bindings are already included in your autoresearch installation, but you need the CLI binary:

### Option 1: Build from Source (Recommended)
```bash
# Clone the taguchi repository
git clone https://github.com/bigattichouse/taguchi.git
cd taguchi

# Build the CLI binary
make cli

# The binary will be at: build/taguchi
# Copy it somewhere in your PATH or set TAGUCHI_CLI_PATH
```

### Option 2: Check if Already Available
```bash
# Check if taguchi CLI is already available
which taguchi

# If found, you're ready to go!
```

### Option 3: Use Environment Variable
```bash
# If you have the binary but it's not in PATH
export TAGUCHI_CLI_PATH=/path/to/your/taguchi/build/taguchi
```

The autoresearch integration will automatically find the CLI binary in these locations:
1. `TAGUCHI_CLI_PATH` environment variable
2. Current directory (`./taguchi_cli`) 
3. Standard system paths (`/usr/local/bin/taguchi`, `/usr/bin/taguchi`)
4. Your system PATH

## Basic Usage

### 1. Define Your Hyperparameters

Look at your `train.py` file and identify the variables you want to optimize:

```python
# Example train.py variables you can optimize:
DEPTH = 8               # Number of transformer layers  
MATRIX_LR = 0.04        # Learning rate for matrix parameters
WEIGHT_DECAY = 0.2      # Weight decay for regularization
WARMUP_RATIO = 0.1      # Learning rate warmup fraction
DEVICE_BATCH_SIZE = 128 # Batch size per device
```

### 2. Run Taguchi Optimization

Create a simple Python script:

```python
# optimize_hyperparams.py
from taguchi_mode import run_taguchi_sweep

# Define the hyperparameters and values you want to test
factors = {
    "DEPTH": ["6", "8", "10"],              # Try 6, 8, or 10 layers
    "MATRIX_LR": ["0.02", "0.04", "0.08"],  # Try different learning rates  
    "WEIGHT_DECAY": ["0.1", "0.2", "0.3"],  # Try different regularization
}

# Run the optimization
print("Starting Taguchi hyperparameter optimization...")
optimal = run_taguchi_sweep(
    factors=factors,
    metric="val_bpb",           # The metric to optimize (lower is better)
    higher_is_better=False      # We want to minimize validation bits-per-byte
)

print(f"✅ Optimal hyperparameters found: {optimal}")
```

Run it:
```bash
python optimize_hyperparams.py
```

### 3. What Happens

The script will:
1. Generate an L9 array (9 strategic combinations)
2. For each combination:
   - Update your `train.py` with the new hyperparameters
   - Run `uv run train.py` 
   - Parse the `val_bpb` metric from the output
   - Restore `train.py` to its original state
3. Analyze all results and recommend the best combination

Example output:
```
============================================================
Taguchi Hyperparameter Sweep  
============================================================
Array: L9 (9 runs)
Factors: 3
Metric: val_bpb (lower is better)
============================================================

[1/9] Run 1: {'DEPTH': '6', 'MATRIX_LR': '0.02', 'WEIGHT_DECAY': '0.1'}
  → val_bpb: 1.234

[2/9] Run 2: {'DEPTH': '6', 'MATRIX_LR': '0.04', 'WEIGHT_DECAY': '0.2'}  
  → val_bpb: 1.189

...

[9/9] Run 9: {'DEPTH': '10', 'MATRIX_LR': '0.08', 'WEIGHT_DECAY': '0.2'}
  → val_bpb: 1.156

============================================================
Analysis (9/9 successful)
============================================================
Main Effects (sorted by range, descending):
  MATRIX_LR            range=  0.0234  means=[1.198, 1.167, 1.145]
  WEIGHT_DECAY         range=  0.0156  means=[1.187, 1.171, 1.156]  
  DEPTH                range=  0.0089  means=[1.173, 1.169, 1.164]

Recommended optimal configuration:
  DEPTH: 10
  MATRIX_LR: 0.08
  WEIGHT_DECAY: 0.3
```

## Advanced Usage

### Environment Configuration

Set these environment variables for better control:

```bash
# Training timeout (if your runs take longer than 400 seconds)
export TAGUCHI_TRAINING_TIMEOUT=600

# Enable debug output to see what's happening
export TAGUCHI_DEBUG=true

# Retry failed training runs automatically  
export TAGUCHI_MAX_RETRIES=1

# Use different training command
export TAGUCHI_TRAINING_CMD="python train.py"

# Use different config file  
export TAGUCHI_CONFIG_FILE="config.py"
```

### Multiple Factors

You can optimize many hyperparameters at once:

```python
factors = {
    # Model architecture
    "DEPTH": ["6", "8", "10"],
    "HEAD_DIM": ["64", "128", "256"], 
    "WINDOW_PATTERN": ["L", "SSSL", "SSSS"],
    
    # Training parameters  
    "MATRIX_LR": ["0.02", "0.04", "0.08"],
    "EMBEDDING_LR": ["0.4", "0.6", "0.8"],
    "WEIGHT_DECAY": ["0.1", "0.2", "0.3"],
    
    # Batch and schedule
    "DEVICE_BATCH_SIZE": ["64", "128", "256"],
    "WARMUP_RATIO": ["0.0", "0.1", "0.2"],
}

# This will automatically select a larger array (like L27) 
# Still much more efficient than full factorial!
optimal = run_taguchi_sweep(factors)
```

### Different Metrics

Optimize any metric that appears in your training output:

```python
# Minimize validation loss
optimal = run_taguchi_sweep(factors, metric="val_loss", higher_is_better=False)

# Maximize accuracy  
optimal = run_taguchi_sweep(factors, metric="accuracy", higher_is_better=True)

# Minimize training time
optimal = run_taguchi_sweep(factors, metric="epoch_time", higher_is_better=False)
```

## How It Works

### Orthogonal Arrays

Taguchi uses "orthogonal arrays" that ensure every factor level appears equally often and in balanced combination with other factors. This means you can determine each factor's individual effect even with fewer experiments.

### Factor Effects Analysis

The output shows:
- **Range**: How much each factor affects your metric
- **Level means**: Average performance at each factor level  
- **Recommendations**: Optimal combination based on individual effects

### Efficiency Examples

| Your Setup | Full Factorial | Taguchi Array | Time Savings |
|------------|---------------|---------------|--------------|
| 3 factors, 3 levels | 27 runs | L9 (9 runs) | 67% |
| 4 factors, 3 levels | 81 runs | L9 (9 runs) | 89% |  
| 5 factors, 3 levels | 243 runs | L27 (27 runs) | 89% |
| 7 factors, 2 levels | 128 runs | L8 (8 runs) | 94% |

## Common Use Cases

### 1. Quick Architecture Search
```python
factors = {
    "DEPTH": ["6", "8", "10", "12"],
    "N_HEAD": ["4", "6", "8"],  
    "HEAD_DIM": ["64", "128"],
}
# L16 array: 16 runs instead of 24 runs (33% savings)
```

### 2. Learning Rate Tuning
```python
factors = {
    "MATRIX_LR": ["0.01", "0.02", "0.04", "0.08"],
    "EMBEDDING_LR": ["0.3", "0.6", "0.9"],
    "WARMUP_RATIO": ["0.0", "0.1", "0.2"],
}
# L16 array: 16 runs instead of 36 runs (56% savings)
```

### 3. Regularization Optimization
```python
factors = {
    "WEIGHT_DECAY": ["0.05", "0.1", "0.2", "0.4"],
    "DROPOUT": ["0.0", "0.1", "0.2"],
    "GRAD_CLIP": ["1.0", "2.0", "5.0"],  
}
# L16 array: 16 runs instead of 36 runs (56% savings)
```

### 4. Full Hyperparameter Sweep
```python
factors = {
    "DEPTH": ["6", "8", "10"],
    "MATRIX_LR": ["0.02", "0.04", "0.08"], 
    "EMBEDDING_LR": ["0.4", "0.6", "0.8"],
    "WEIGHT_DECAY": ["0.1", "0.2", "0.3"],
    "WARMUP_RATIO": ["0.0", "0.1", "0.2"],
    "DEVICE_BATCH_SIZE": ["64", "128", "256"],
}
# L27 array: 27 runs instead of 729 runs (96% savings!)
```

## Troubleshooting

### "train.py not found"
```
Error: train.py not found in current directory
```
**Solution**: Run the optimization script from the same directory as your `train.py` file.

### "Variables not found in train.py"  
```
TaguchiError: Variables not found in train.py: ['SOME_VAR']
```
**Solution**: Make sure the variable names in your `factors` dict exactly match the variable names in `train.py`.

### "uv command not found"
```
Error: 'uv' command not found. Install with: pip install uv
```
**Solution**: Install uv or change the training command:
```bash
export TAGUCHI_TRAINING_CMD="python train.py"
```

### Training Takes Too Long
```
Timeout (>400s)
```
**Solution**: Increase the timeout:
```bash
export TAGUCHI_TRAINING_TIMEOUT=1200  # 20 minutes
```

### "Failed to parse val_bpb"
```
Failed to parse val_bpb
```
**Solution**: 
1. Check that your training script actually outputs the metric you specified
2. Make sure the format is like `val_bpb: 1.234` 
3. Try a different metric name that appears in your output

## Tips for Best Results

### 1. Choose Meaningful Ranges
Don't test random values. Choose ranges based on your experience:
```python
# Good: Sensible learning rate range
"MATRIX_LR": ["0.01", "0.04", "0.16"]   

# Bad: Too wide, includes unrealistic values  
"MATRIX_LR": ["0.001", "0.1", "10.0"]
```

### 2. Start Small
Begin with 2-3 important factors, then expand:
```python
# First experiment: Focus on the most important factors
factors = {
    "DEPTH": ["6", "8", "10"],
    "MATRIX_LR": ["0.02", "0.04", "0.08"],
}

# Later: Add more factors based on initial results
factors = {
    "DEPTH": ["7", "8", "9"],           # Refine around best value
    "MATRIX_LR": ["0.03", "0.04", "0.05"], # Refine around best value  
    "WEIGHT_DECAY": ["0.1", "0.2", "0.3"], # Add new factor
}
```

### 3. Use Consistent Naming
Make sure your factor names exactly match your `train.py` variables:
```python
# In train.py:
MATRIX_LR = 0.04

# In your factors (must match exactly):
factors = {
    "MATRIX_LR": ["0.02", "0.04", "0.08"],  # ✅ Correct
    # "matrix_lr": ["0.02", "0.04", "0.08"], # ❌ Wrong case
    # "LEARNING_RATE": ["0.02", "0.04", "0.08"], # ❌ Wrong name
}
```

### 4. Monitor Progress
Use debug mode to see what's happening:
```bash
export TAGUCHI_DEBUG=true
python optimize_hyperparams.py
```

## Integration with Your Workflow

### Automated Experiments
```python
# run_optimization.py
import json
from taguchi_mode import run_taguchi_sweep

# Define multiple experiment configurations
experiments = [
    {
        "name": "architecture_search",
        "factors": {
            "DEPTH": ["6", "8", "10"],
            "N_HEAD": ["4", "6", "8"],
        }
    },
    {
        "name": "learning_rate_search", 
        "factors": {
            "MATRIX_LR": ["0.02", "0.04", "0.08"],
            "EMBEDDING_LR": ["0.4", "0.6", "0.8"],
        }
    }
]

results = {}
for exp in experiments:
    print(f"Running {exp['name']}...")
    optimal = run_taguchi_sweep(exp['factors'])
    results[exp['name']] = optimal

# Save all results
with open('optimization_results.json', 'w') as f:
    json.dump(results, f, indent=2)
```

### Validation Runs
After finding optimal hyperparameters, run a few validation experiments:

```python
# After optimization, manually update train.py with optimal values
# Then run several times to confirm results:

for i in range(5):
    print(f"Validation run {i+1}/5...")
    # Run your training with optimal hyperparameters
    # Record results to confirm consistency
```

## Getting Help

- **Errors with factor names**: Check that variables exist in your `train.py`
- **Slow training**: Increase `TAGUCHI_TRAINING_TIMEOUT` 
- **Parse errors**: Verify the metric name appears in your training output
- **CLI not found**: Make sure the Taguchi CLI binary is installed

Remember: Taguchi optimization finds good hyperparameters much faster than exhaustive search, but it still requires some trial and error to get the factor ranges right. Start simple and iterate!