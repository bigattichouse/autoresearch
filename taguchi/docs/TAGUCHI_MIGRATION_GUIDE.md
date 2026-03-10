# Taguchi Integration Migration Guide

## Overview

This guide covers migrating from the original `taguchi_mode.py` to the enhanced `taguchi_mode_enhanced.py` which leverages the improved Taguchi library v1.6.0.

## What's New in Enhanced Integration

### ✅ Fixed Critical Issues
- **File backup race condition**: Proper backup/restore with context managers
- **Subprocess validation**: Better error handling and retry logic
- **Configuration management**: Environment variable support
- **Error messages**: Rich context with actionable suggestions

### 🚀 New Features
- **Environment configuration**: Configure via `TAGUCHI_*` environment variables
- **Validation**: Pre-flight validation of experiments and configuration
- **Retry logic**: Automatic retry for transient failures
- **Debug mode**: Enhanced logging and diagnostic information
- **Dependency injection**: Testable, modular architecture

## Migration Steps

### 1. Update Imports (Backward Compatible)

**Old way** (still works):
```python
from taguchi_mode import run_taguchi_sweep

factors = {"DEPTH": ["6", "8", "10"]}
optimal = run_taguchi_sweep(factors)
```

**New enhanced way**:
```python
from taguchi_mode_enhanced import run_taguchi_sweep

factors = {"DEPTH": ["6", "8", "10"]}
optimal = run_taguchi_sweep(factors)  # Same API, better implementation
```

### 2. Environment Configuration (Recommended)

Set up environment variables for robust deployment:

```bash
# Required: CLI binary location
export TAGUCHI_CLI_PATH=/usr/local/bin/taguchi

# Optional: Timeouts and behavior
export TAGUCHI_CLI_TIMEOUT=60          # CLI command timeout
export TAGUCHI_DEBUG=true              # Enable debug logging
export TAGUCHI_MAX_RETRIES=2           # Retry failed commands

# Autoresearch specific
export AUTORESEARCH_TRAINING_TIMEOUT=600    # Training timeout
export AUTORESEARCH_TRAINING_RETRIES=1      # Retry failed training
export AUTORESEARCH_CONFIG_FILE=train.py    # Config file to modify
```

### 3. Enhanced Usage with Configuration

**Advanced configuration**:
```python
from taguchi_mode_enhanced import run_taguchi_sweep
from taguchi import TaguchiConfig

# Custom configuration
config = TaguchiConfig(
    debug_mode=True,
    cli_timeout=120,
    max_retries=2
)

factors = {"DEPTH": ["6", "8", "10"]}
optimal = run_taguchi_sweep(
    factors,
    metric="val_bpb", 
    config=config  # Pass custom config
)
```

### 4. Error Handling Improvements

**Old error handling**:
```python
try:
    optimal = run_taguchi_sweep(factors)
except Exception as e:
    print(f"Error: {e}")  # Generic, unhelpful
```

**Enhanced error handling**:
```python
from taguchi_mode_enhanced import run_taguchi_sweep, ConfigurationError, TrainingError

try:
    optimal = run_taguchi_sweep(factors)
except ConfigurationError as e:
    print(f"Configuration problem: {e}")
    if hasattr(e, 'suggestions'):
        print("Suggestions:")
        for suggestion in e.suggestions:
            print(f"  - {suggestion}")
except TrainingError as e:
    print(f"Training failed: {e}")
    if hasattr(e, 'command'):
        print(f"Failed command: {' '.join(e.command)}")
```

### 5. Pre-flight Validation

**New validation capabilities**:
```python
from taguchi_mode_enhanced import validate_environment
import json

# Check environment before starting experiments
diagnostics = validate_environment()
print(json.dumps(diagnostics, indent=2))

if not diagnostics['taguchi_installation']['cli_found']:
    print("❌ Taguchi CLI not found!")
    exit(1)

if not diagnostics['config_file_exists']:
    print("❌ Training config file not found!")
    exit(1)

print("✅ Environment validated, proceeding with experiment...")
```

## Comparison: Old vs Enhanced

### Original Implementation Issues

```python
# taguchi_mode.py - PROBLEMS:
def run_taguchi_sweep(...):
    backup = Path("train.py").read_text()  # ❌ Race condition
    try:
        update_train_py(run['factors'])
        
        result = subprocess.run(["uv", "run", "train.py"], ...)  # ❌ Hardcoded
        
        value = parse_metric(result.stdout, metric)  # ❌ Fragile parsing
        if value is not None:
            analyzer.add_result(run['run_id'], value)
        else:
            print(f"  → Failed to parse {metric}")  # ❌ No context
            
    except subprocess.TimeoutExpired:
        print(f"  → Timeout (>400s)")  # ❌ No retry
    except Exception as e:
        print(f"  → Error: {e}")  # ❌ Generic error
    finally:
        Path("train.py").write_text(backup)  # ❌ May not restore
```

### Enhanced Implementation Benefits

```python
# taguchi_mode_enhanced.py - SOLUTIONS:
def run_taguchi_sweep(...):
    # ✅ Proper dependency injection
    config_manager = ConfigurationManager(autoresearch_config.config_file)
    training_executor = TrainingExecutor(autoresearch_config)
    
    try:
        with config_manager:  # ✅ Safe backup/restore
            config_manager.update_configuration(run['factors'])
            result = training_executor.execute_training()  # ✅ Retry logic
            
        value = metric_parser.parse_metric(result.stdout, metric)  # ✅ Better parsing
        if value is not None:
            analyzer.add_result(run['run_id'], value)
        else:
            print(f"  → Failed to parse {metric} from output")
            if config.debug_mode:  # ✅ Debug context
                print(f"  → Debug: stdout={result.stdout[:200]}...")
            
    except (TrainingError, ConfigurationError) as e:  # ✅ Specific errors
        print(f"  → Error: {e}")
        if hasattr(e, 'suggestions') and e.suggestions:  # ✅ Actionable help
            print("  → Suggestions:")
            for suggestion in e.suggestions[:3]:
                print(f"    - {suggestion}")
```

## Performance and Reliability Improvements

### Original Issues
- **Silent failures**: Errors logged but experiment continues with invalid data
- **No retries**: Transient failures cause complete experiment failure
- **Poor debugging**: No visibility into what went wrong
- **Hardcoded timeouts**: 400s timeout doesn't work for all use cases

### Enhanced Solutions
- **Fail-fast validation**: Validate environment and configuration before starting
- **Exponential backoff retry**: Automatic retry for transient failures  
- **Rich diagnostics**: Full context for debugging issues
- **Configurable timeouts**: Adapt to different training requirements

## Deployment Improvements

### Container/CI Friendly

**Original deployment issues**:
- Binary discovery fails in containers
- No way to configure paths
- Silent failures in CI environments

**Enhanced deployment**:
```dockerfile
# Dockerfile
FROM python:3.12
RUN apt-get update && apt-get install -y taguchi
ENV TAGUCHI_CLI_PATH=/usr/bin/taguchi
ENV TAGUCHI_DEBUG=true
ENV TAGUCHI_CLI_TIMEOUT=120
```

```yaml
# CI pipeline
env:
  TAGUCHI_CLI_PATH: /usr/local/bin/taguchi
  TAGUCHI_DEBUG: true
  AUTORESEARCH_TRAINING_TIMEOUT: 300
```

## Testing Improvements

### Original Testing Challenges
```python
# Hard to test due to tight coupling
def test_taguchi_sweep():
    # Can't mock subprocess calls
    # Can't control file system operations  
    # No way to inject dependencies
    pass
```

### Enhanced Testing Capabilities
```python
# Easy to test with dependency injection
def test_taguchi_sweep():
    from unittest.mock import Mock
    
    # Mock components
    mock_config_manager = Mock()
    mock_training_executor = Mock()
    mock_metric_parser = Mock()
    
    # Inject mocks and test business logic
    result = run_enhanced_experiment(
        factors={"A": ["1", "2"]},
        config_manager=mock_config_manager,
        training_executor=mock_training_executor,
        metric_parser=mock_metric_parser
    )
    
    # Verify interactions
    mock_config_manager.update_configuration.assert_called()
    mock_training_executor.execute_training.assert_called()
```

## Backward Compatibility

The enhanced integration maintains **100% backward compatibility**:

- Existing `taguchi_mode.py` code continues to work unchanged
- Same function signatures and return values
- Enhanced features are opt-in via configuration
- Original `taguchi` package imports still work

## Migration Checklist

- [ ] **Test current setup**: Verify existing `taguchi_mode.py` works
- [ ] **Install enhanced library**: Copy updated taguchi package  
- [ ] **Set environment variables**: Configure `TAGUCHI_CLI_PATH` etc.
- [ ] **Test enhanced version**: Run `test_enhanced_integration.py`
- [ ] **Update imports**: Switch to `taguchi_mode_enhanced`
- [ ] **Add error handling**: Use specific exception types
- [ ] **Configure for deployment**: Set environment variables for containers/CI
- [ ] **Update documentation**: Document new configuration options

## Rollback Plan

If issues arise, rollback is simple:

```python
# Change this:
from taguchi_mode_enhanced import run_taguchi_sweep

# Back to this:  
from taguchi_mode import run_taguchi_sweep

# Everything else works the same
```

The original `taguchi_mode.py` remains available as a fallback.

---

## Summary

The enhanced integration provides significant improvements in reliability, debuggability, and maintainability while maintaining full backward compatibility. The migration is low-risk and can be done incrementally.