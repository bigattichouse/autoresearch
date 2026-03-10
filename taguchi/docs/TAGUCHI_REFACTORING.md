# Taguchi Integration Refactoring Plan

## Overview
This document outlines critical issues found in the Taguchi integration and provides a systematic refactoring plan to improve safety, reliability, and maintainability.

## Critical Issues (Must Fix)

### 1. File Backup Race Condition 🚨
**File**: `taguchi_mode.py:64-89`
**Severity**: Critical - Data Loss Risk

**Problem**: 
```python
backup = Path("train.py").read_text()  # Outside try block
try:
    update_train_py(run['factors'])
    # ... training code
except Exception as e:
    # ... error handling  
finally:
    Path("train.py").write_text(backup)  # backup may be undefined
```

**Risk**: If exception occurs before backup assignment, original `train.py` is lost permanently.

**Fix**: Move backup inside try block and add validation:
```python
try:
    if not Path("train.py").exists():
        raise TaguchiError("train.py not found")
    backup = Path("train.py").read_text()
    update_train_py(run['factors'])
    # ... rest of code
finally:
    if 'backup' in locals():
        Path("train.py").write_text(backup)
```

### 2. Subprocess Security & Error Handling 🔐
**File**: `taguchi_mode.py:68-73`
**Severity**: High - Security & Reliability

**Problem**: 
- Hardcoded `["uv", "run", "train.py"]` command
- No validation that `uv` exists
- Could fail silently if `uv` not in PATH

**Fix**: Add executable validation and better error messages:
```python
def validate_environment():
    if not shutil.which("uv"):
        raise TaguchiError("uv command not found. Install with: pip install uv")
    if not Path("train.py").exists():
        raise TaguchiError("train.py not found in current directory")
```

### 3. Regex-based Python Modification 🔧
**File**: `taguchi_mode.py:114-116`
**Severity**: Medium - Fragility

**Problem**:
```python
pattern = rf'^(\s*){key}\s*=\s*[^#\n]+(#.*)?$'
replacement = rf'\1{key} = {value}\2'
```
- Fragile regex that may not handle all valid Python syntax
- No validation that target variables exist
- Could corrupt Python files with complex expressions

**Fix**: Add validation and safer replacement:
```python
def update_train_py(factors: Dict[str, str]) -> None:
    train_py = Path("train.py")
    content = train_py.read_text()
    
    # Validate all required variables exist first
    missing_vars = []
    for key in factors.keys():
        pattern = rf'^(\s*){re.escape(key)}\s*='
        if not re.search(pattern, content, flags=re.MULTILINE):
            missing_vars.append(key)
    
    if missing_vars:
        raise TaguchiError(f"Variables not found in train.py: {missing_vars}")
    
    # Apply replacements with better pattern matching
    for key, value in factors.items():
        pattern = rf'^(\s*)({re.escape(key)})\s*=\s*[^#\n]+(#.*)?$'
        replacement = rf'\1\2 = {value}\3'
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        if new_content == content:
            raise TaguchiError(f"Failed to update variable: {key}")
        content = new_content
    
    train_py.write_text(content)
```

## High Priority Issues

### 4. Hardcoded Configuration Values
**Files**: Multiple
**Severity**: Medium

**Problems**:
- 400s timeout hardcoded (`taguchi_mode.py:72`)
- 30s CLI timeout hardcoded (`core.py:11`)
- No way to configure paths or behavior

**Fix**: Create configuration class:
```python
@dataclass
class TaguchiConfig:
    training_timeout_seconds: int = 400
    cli_timeout_seconds: int = 30
    cli_path: Optional[str] = None
    retry_attempts: int = 1
    
    @classmethod
    def from_env(cls) -> "TaguchiConfig":
        return cls(
            training_timeout_seconds=int(os.getenv("TAGUCHI_TRAINING_TIMEOUT", "400")),
            cli_timeout_seconds=int(os.getenv("TAGUCHI_CLI_TIMEOUT", "30")),
            cli_path=os.getenv("TAGUCHI_CLI_PATH"),
            retry_attempts=int(os.getenv("TAGUCHI_RETRY_ATTEMPTS", "1")),
        )
```

### 5. Poor Error Recovery
**File**: `taguchi_mode.py:75-89`
**Severity**: Medium

**Problems**:
- Failed runs aren't retried
- No distinction between different failure types
- Timeouts treated same as parsing errors

**Fix**: Add retry logic and better error classification:
```python
class TrainingError(TaguchiError):
    pass

class TimeoutError(TaguchiError):
    pass

class ParseError(TaguchiError):
    pass

def run_training_with_retry(factors: Dict[str, str], config: TaguchiConfig) -> Optional[float]:
    for attempt in range(config.retry_attempts):
        try:
            result = subprocess.run(
                ["uv", "run", "train.py"],
                capture_output=True,
                text=True,
                timeout=config.training_timeout_seconds
            )
            
            if result.returncode != 0:
                raise TrainingError(f"Training failed: {result.stderr}")
                
            value = parse_metric(result.stdout, metric)
            if value is None:
                raise ParseError(f"Could not parse metric: {metric}")
                
            return value
            
        except subprocess.TimeoutExpired:
            if attempt == config.retry_attempts - 1:
                raise TimeoutError(f"Training timeout after {config.training_timeout_seconds}s")
            time.sleep(2 ** attempt)  # exponential backoff
        except (TrainingError, ParseError):
            if attempt == config.retry_attempts - 1:
                raise
            time.sleep(1)
    
    return None
```

## Medium Priority Issues

### 6. Memory Management
**File**: `taguchi_mode.py:68-73`
**Issue**: Large subprocess output captured entirely in memory

**Fix**: Consider streaming for very long outputs:
```python
def run_training_streaming(config: TaguchiConfig):
    process = subprocess.Popen(
        ["uv", "run", "train.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    stdout, stderr = process.communicate(timeout=config.training_timeout_seconds)
    # ... rest of processing
```

### 7. Type Safety & Validation
**Files**: Multiple
**Issues**: 
- Missing type hints in several functions
- No runtime validation of inputs
- Inconsistent error handling

**Fix**: Add comprehensive type hints and validation:
```python
from typing import Dict, List, Optional, Union
import pydantic

class FactorDefinition(pydantic.BaseModel):
    name: str = pydantic.Field(regex=r'^[A-Za-z_][A-Za-z0-9_]*$')
    levels: List[str] = pydantic.Field(min_items=2)

def run_taguchi_sweep(
    factors: Dict[str, List[str]],
    metric: str = "val_bpb",
    higher_is_better: bool = False,
    array_type: Optional[str] = None,
    config: Optional[TaguchiConfig] = None,
) -> Dict[str, str]:
    # Validate inputs
    if not factors:
        raise TaguchiError("No factors provided")
    
    for name, levels in factors.items():
        FactorDefinition(name=name, levels=levels)  # Validates format
```

## Low Priority Issues

### 8. Code Style & Consistency
- Mixed f-string vs format string usage
- Some functions lack docstrings  
- Inconsistent variable naming

### 9. Testing Gaps
- No integration tests for actual subprocess calls
- Missing edge case tests for file modification
- No performance tests for large factor spaces

## Implementation Plan

### Phase 1: Critical Fixes (Required)
1. Fix file backup race condition
2. Add subprocess validation and error handling
3. Improve Python file modification safety
4. Add basic configuration management

### Phase 2: Reliability Improvements
1. Implement retry logic and better error recovery
2. Add comprehensive input validation
3. Improve type safety

### Phase 3: Polish & Optimization  
1. Memory management improvements
2. Code style cleanup
3. Enhanced testing coverage

## Testing Strategy

Before implementing fixes:
1. Run existing test suite: `python -m pytest test_taguchi_integration.py -v`
2. Create backup of current working system
3. Implement fixes incrementally with tests for each change
4. Validate integration still works with real training runs

## Rollback Plan

If issues arise during refactoring:
1. Revert to commit: `e5c6e7a` (last known working state)
2. Apply fixes more incrementally
3. Test each change in isolation

---

**Next Steps**: Begin with Phase 1 critical fixes, starting with the file backup race condition.