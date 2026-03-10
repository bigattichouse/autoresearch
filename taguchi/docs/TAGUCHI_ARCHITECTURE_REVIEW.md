# Taguchi Implementation - Architecture & SOLID Principles Review

## Overview
This review focuses specifically on the Taguchi integration code added to autoresearch, analyzing violations of SOLID principles and separation of concerns.

## Files Under Review
- `taguchi_mode.py` - Main integration module
- `taguchi/` package - Core Taguchi functionality
- `test_taguchi_integration.py` - Test suite

---

## 🚨 Critical SOLID Violations

### 1. Single Responsibility Principle (SRP) - Major Violations

#### `taguchi_mode.py:26-105` - `run_taguchi_sweep()`
**Violation**: Function handles 6+ distinct responsibilities:

```python
def run_taguchi_sweep(factors, metric, higher_is_better, array_type):
    # 1. Experiment setup & configuration
    with Experiment(array_type=array_type) as exp:
        
    # 2. File backup/restore management  
    backup = Path("train.py").read_text()
    
    # 3. Subprocess execution
    result = subprocess.run(["uv", "run", "train.py"], ...)
    
    # 4. Output parsing & validation
    value = parse_metric(result.stdout, metric)
    
    # 5. Progress reporting & logging
    print(f"[{i+1}/{len(runs)}] Run {run['run_id']}")
    
    # 6. Analysis & recommendation
    optimal = analyzer.recommend_optimal(higher_is_better)
```

**Impact**: Impossible to test individual concerns, high coupling, maintenance nightmare.

#### `taguchi/core.py:19-161` - `Taguchi` class
**Violation**: Class mixes multiple concerns:

```python
class Taguchi:
    # 1. CLI binary discovery
    def _find_cli(self, cli_path): ...
    
    # 2. Command execution
    def _run_command(self, args): ...
    
    # 3. Output parsing
    def _get_arrays_info(self): ...
    
    # 4. Caching logic
    self._array_cache = None
    
    # 5. File format handling
    def generate_runs(self, tgu_path): ...
```

### 2. Open/Closed Principle (OCP) - Extension Impossible

#### `taguchi_mode.py:108-118` - `update_train_py()`
**Violation**: Hardcoded to specific Python file format:

```python
def update_train_py(factors: Dict[str, str]) -> None:
    # Hardcoded regex pattern - cannot extend to other formats
    pattern = rf'^(\s*){key}\s*=\s*[^#\n]+(#.*)?$'
    replacement = rf'\1{key} = {value}\2'
    content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
```

**Problem**: To support YAML, JSON, or TOML configs requires modifying this function.

#### `taguchi_mode.py:121-125` - `parse_metric()`
**Violation**: Hardcoded parsing logic:

```python
def parse_metric(output: str, metric: str) -> Optional[float]:
    pattern = rf'{metric}:\s*([\d.]+)'  # Only handles this format
    match = re.search(pattern, output)
    return float(match.group(1)) if match else None
```

**Problem**: Cannot extend to parse different output formats without modification.

### 3. Dependency Inversion Principle (DIP) - Major Violations

#### `taguchi_mode.py` - Concrete Dependencies
**Violation**: Direct dependencies on concrete implementations:

```python
# Direct file system dependency
backup = Path("train.py").read_text()

# Direct subprocess dependency  
result = subprocess.run(["uv", "run", "train.py"], ...)

# Hard-coded command
subprocess.run(["uv", "run", "train.py"])  # Should be configurable
```

**Problem**: Cannot mock for testing, cannot swap implementations.

#### `taguchi/analyzer.py:24-30` - Constructor Dependencies
**Violation**: Creates its own dependencies:

```python
class Analyzer:
    def __init__(self, experiment: Any, metric_name: str = "response"):
        self._taguchi = Taguchi()  # Creates concrete dependency
```

**Problem**: Cannot inject mock Taguchi for testing.

### 4. Interface Segregation Principle (ISP) - Fat Interfaces

#### `taguchi/analyzer.py` - Bloated Interface
**Violation**: Clients forced to depend on unused methods:

```python
class Analyzer:
    # Analysis methods - needed by business logic
    def add_result(self, run_id: int, value: float): ...
    def main_effects(self): ...
    def recommend_optimal(self): ...
    
    # Infrastructure methods - not needed by business logic
    def cleanup(self): ...
    def __enter__(self): ...
    def __exit__(self): ...
    def __del__(self): ...
    
    # Internal helpers - should be private
    def _ensure_files(self): ...
    def _parse_effects(self): ...
```

**Problem**: Business logic clients must depend on file management concerns.

---

## 🔧 Separation of Concerns Violations

### 1. Business Logic Mixed with Infrastructure

#### `taguchi_mode.py:60-89` - Training Execution
**Problem**: Domain logic mixed with subprocess management:

```python
# Business concern: experiment orchestration
for i, run in enumerate(runs):
    print(f"\n[{i+1}/{len(runs)}] Run {run['run_id']}: {run['factors']}")
    
    # Infrastructure concern: file management
    backup = Path("train.py").read_text()
    
    # Infrastructure concern: subprocess execution
    result = subprocess.run(["uv", "run", "train.py"], ...)
    
    # Business concern: result analysis  
    value = parse_metric(result.stdout, metric)
    analyzer.add_result(run['run_id'], value)
```

### 2. Presentation Mixed with Data Processing

#### `taguchi/analyzer.py:193-222` - Summary Generation
**Problem**: Data analysis class handles presentation:

```python
class Analyzer:
    def summary(self) -> str:  # Should be in separate presenter
        lines = ["=" * 60, f"Taguchi Experiment Analysis: {self._metric_name}"]
        # ... formatting logic mixed with analysis class
```

### 3. Configuration Mixed with Execution

#### `taguchi_mode.py:46-50` - Setup Mixed with Execution
**Problem**: Experiment configuration mixed with execution loop:

```python
def run_taguchi_sweep(...):
    with Experiment(array_type=array_type) as exp:
        for name, levels in factors.items():  # Configuration
            exp.add_factor(name, levels)
        
        runs = exp.generate()  # Generation
        
        # Immediately jumps to execution - no separation
        for i, run in enumerate(runs):
```

---

## 🎯 Architectural Refactoring Plan

### Phase 1: Extract Core Abstractions

```python
# Domain layer - pure business logic
class TaguchiExperiment:
    def __init__(self, factors: Dict[str, List[str]]):
        self._factors = factors
    
    def plan_experimental_runs(self) -> List[ExperimentRun]:
        # Pure domain logic, no infrastructure

# Application layer - orchestration
class ExperimentOrchestrator:
    def __init__(self, 
                 training_runner: TrainingRunner,
                 config_manager: ConfigManager,
                 result_analyzer: ResultAnalyzer):
        self._training_runner = training_runner
        self._config_manager = config_manager
        self._result_analyzer = result_analyzer
    
    def execute_experiment(self, experiment: TaguchiExperiment) -> ExperimentResult:
        # Orchestrates without knowing implementation details

# Infrastructure layer
class FileBasedConfigManager(ConfigManager):
    def update_training_config(self, parameters: Dict[str, str]) -> None:
        # File-specific implementation

class SubprocessTrainingRunner(TrainingRunner):
    def run_training(self, config_backup: ConfigBackup) -> TrainingOutput:
        # Subprocess-specific implementation
```

### Phase 2: Introduce Proper Interfaces

```python
from abc import ABC, abstractmethod

class TrainingRunner(ABC):
    @abstractmethod
    def run_training(self, config_backup: ConfigBackup) -> TrainingOutput:
        pass

class ConfigManager(ABC):
    @abstractmethod
    def backup_config(self) -> ConfigBackup:
        pass
    
    @abstractmethod
    def update_training_config(self, parameters: Dict[str, str]) -> None:
        pass
    
    @abstractmethod
    def restore_config(self, backup: ConfigBackup) -> None:
        pass

class OutputParser(ABC):
    @abstractmethod
    def parse_metric(self, output: str, metric_name: str) -> Optional[float]:
        pass
```

### Phase 3: Dependency Injection

```python
class TaguchiMode:
    def __init__(self,
                 orchestrator: ExperimentOrchestrator,
                 presenter: ExperimentPresenter):
        self._orchestrator = orchestrator
        self._presenter = presenter
    
    def run_sweep(self, config: ExperimentConfig) -> None:
        experiment = TaguchiExperiment(config.factors)
        result = self._orchestrator.execute_experiment(experiment)
        self._presenter.present_results(result)

# Factory for dependency injection
def create_taguchi_mode() -> TaguchiMode:
    config_manager = FileBasedConfigManager("train.py")
    training_runner = SubprocessTrainingRunner("uv", timeout=400)
    output_parser = RegexOutputParser()
    result_analyzer = TaguchiResultAnalyzer()
    
    orchestrator = ExperimentOrchestrator(
        training_runner, config_manager, result_analyzer
    )
    presenter = ConsoleExperimentPresenter()
    
    return TaguchiMode(orchestrator, presenter)
```

---

## 📊 Current Architecture Problems Summary

| Principle | Violation Count | Severity | Examples |
|-----------|----------------|----------|----------|
| SRP | 8 major | Critical | `run_taguchi_sweep()` does everything |
| OCP | 4 major | High | Hardcoded parsers, file formats |
| LSP | 1 minor | Low | Context manager inheritance |
| ISP | 3 major | Medium | Fat `Analyzer` interface |
| DIP | 6 major | Critical | Direct subprocess, file dependencies |

**Technical Debt**: High - Code is difficult to test, extend, or maintain
**Refactoring Effort**: Medium - Core abstractions need extraction
**Risk**: Medium - Changes affect integration points

## Next Steps

1. **Extract domain models** from `run_taguchi_sweep()`
2. **Create abstractions** for external dependencies  
3. **Implement dependency injection** pattern
4. **Separate presentation** from business logic
5. **Add proper error handling** with specific exception types

This refactoring will make the code testable, extensible, and maintainable while following clean architecture principles.