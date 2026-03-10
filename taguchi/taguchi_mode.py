"""
Taguchi Orthogonal Array Hyperparameter Optimization

This module implements Taguchi experimental design for systematic
hyperparameter optimization, providing statistically sound methods
for identifying optimal configurations with reduced experimental cost.

Usage:
    from taguchi.taguchi_mode import run_taguchi_sweep
    
    factors = {
        "DEPTH": ["6", "8", "10"],
        "MATRIX_LR": ["0.02", "0.04", "0.08"],
    }
    
    optimal = run_taguchi_sweep(factors, metric="val_bpb", higher_is_better=False)
"""

import subprocess
import re
from pathlib import Path
from typing import Dict, List, Optional, Union, Any, Callable

from . import Experiment, Analyzer
from .errors import TaguchiError
from .signal_analysis import SignalAnalyzer
from .config import TaguchiConfig, ConfigManager
from .system import SystemRunner, FileManager


def run_taguchi_sweep(
    factors: Dict[str, List[str]],
    metric: str = "val_bpb",
    higher_is_better: bool = False,
    array_type: Optional[str] = None,
    config: Optional[Union[Dict[str, Any], TaguchiConfig]] = None,
    runner: Optional[SystemRunner] = None,
    file_manager: Optional[FileManager] = None,
) -> Dict[str, str]:
    """
    Execute a Taguchi orthogonal array experimental design for hyperparameter optimization.
    
    Args:
        factors: Dict mapping factor names to list of level values
        metric: Metric name to optimize (default: "val_bpb")
        higher_is_better: If True, maximize metric; if False, minimize
        array_type: Specific orthogonal array (e.g., "L9"). If None, auto-select.
        config: Optional config dict or TaguchiConfig instance.
        runner: Optional SystemRunner for command execution (allows mocking).
        file_manager: Optional FileManager for file operations (allows mocking).
    
    Returns:
        Dict mapping factor names to optimal level values
    """
    # Initialize components
    runner = runner or SystemRunner()
    file_manager = file_manager or FileManager()
    
    # Resolve configuration
    if config is None:
        cfg = ConfigManager.get_default_config()
    elif isinstance(config, dict):
        cfg = ConfigManager.get_default_config().copy(**config)
    else:
        cfg = config

    with Experiment(array_type=array_type) as exp:
        for name, levels in factors.items():
            exp.add_factor(name, levels)
        
        runs = exp.generate()
        
        _print_header(exp, factors, metric, higher_is_better, cfg.dry_run)
        
        with Analyzer(exp, metric_name=metric) as analyzer:
            for i, run in enumerate(runs):
                print(f"\n[{i+1}/{len(runs)}] Run {run['run_id']}: {run['factors']}")
                
                if cfg.dry_run:
                    print(f"  → [DRY RUN] Would update {cfg.config_file} and run {' '.join(cfg.training_command)}")
                    # Simulate a result for dry run analysis if needed, or just skip
                    continue

                value = _execute_single_run(run, cfg, runner, file_manager, metric)
                if value is not None:
                    print(f"  → {metric}: {value}")
                    analyzer.add_result(run['run_id'], value)
            
            if cfg.dry_run:
                print("\nDry run completed. No actual runs were executed.")
                return {}

            if not analyzer._results:
                print("\nNo successful runs!")
                return {}
            
            _print_summary(analyzer, runs, optimal := analyzer.recommend_optimal(higher_is_better=higher_is_better))
            
            # Basic SNR Analysis for original version  
            if cfg.debug_mode:
                _print_snr_analysis(runs, analyzer._results, factors, higher_is_better)
            
            return optimal


def _print_header(exp, factors, metric, higher_is_better, dry_run):
    print(f"\n{'='*60}")
    print(f"Taguchi Hyperparameter Sweep {'(DRY RUN)' if dry_run else ''}")
    print(f"{'='*60}")
    print(f"Array: {exp.array_type} ({exp.num_runs} runs)")
    print(f"Factors: {len(factors)}")
    print(f"Metric: {metric} ({'higher' if higher_is_better else 'lower'} is better)")
    print(f"{'='*60}\n")


def _print_summary(analyzer, runs, optimal):
    print(f"\n{'='*60}")
    print(f"Analysis ({len(analyzer._results)}/{len(runs)} successful)")
    print(f"{'='*60}")
    print(analyzer.summary())
    
    print(f"\nRecommended:")
    for factor, level in optimal.items():
        print(f"  {factor}: {level}")


def _print_snr_analysis(runs, results, factors, higher_is_better):
    print(f"\n{'='*60}")
    print("SIGNAL-TO-NOISE RATIO ANALYSIS (Debug Mode)")
    print(f"{'='*60}")
    
    signal_analyzer = SignalAnalyzer()
    signal_analyzer.set_experimental_data(runs, results, factors)
    
    # Generate basic SNR report
    snr_report = signal_analyzer.generate_signal_report(higher_is_better)
    print(snr_report)


def _execute_single_run(
    run: Dict[str, Any],
    cfg: TaguchiConfig,
    runner: SystemRunner,
    file_manager: FileManager,
    metric: str
) -> Optional[float]:
    """Handles the lifecycle of a single experimental run."""
    backup = None
    config_path = Path(cfg.config_file)
    
    try:
        # 1. Prepare: Validate and Backup
        if not file_manager.exists(config_path):
            print(f"  → Error: {cfg.config_file} not found")
            return None
            
        backup = file_manager.read_text(config_path)
        
        # 2. Modify: Update config file
        update_config_file(cfg.config_file, run['factors'], file_manager)
        
        # 3. Execute: Run training with retry logic
        result = _run_training_with_retries(cfg, runner, file_manager)
        
        # 4. Process: Parse results
        if result:
            value = parse_metric(result.stdout, metric)
            if value is None and result.returncode != 0:
                print(f"  → Exit code: {result.returncode}")
                stderr_preview = (result.stderr.strip()[:100] + "...") if len(result.stderr.strip()) > 100 else result.stderr.strip()
                if stderr_preview:
                    print(f"  → Error: {stderr_preview}")
            return value
            
    except Exception as e:
        print(f"  → Error: {e}")
    finally:
        # 5. Restore: Always return to original state
        if backup is not None:
            try:
                file_manager.write_text(config_path, backup)
            except Exception as restore_error:
                print(f"  → Critical: Failed to restore {cfg.config_file}: {restore_error}")
                
    return None


def _run_training_with_retries(
    cfg: TaguchiConfig,
    runner: SystemRunner,
    file_manager: FileManager
) -> Optional[subprocess.CompletedProcess]:
    """Executes training command with retry logic and real-time progress reporting."""
    cmd_executable = cfg.training_command[0]
    if not file_manager.which(cmd_executable):
        print(f"  → Error: '{cmd_executable}' command not found")
        return None

    attempt = 0
    max_attempts = cfg.max_retries + 1
    
    def progress_callback(line: str):
        # Look for patterns like "step 000xx" or "loss: x.xxxx"
        step_match = re.search(r'step\s+(\d+)', line, re.IGNORECASE)
        loss_match = re.search(r'loss:\s*([\d.]+)', line, re.IGNORECASE)
        
        report_parts = []
        if step_match:
            report_parts.append(f"step {step_match.group(1)}")
        if loss_match:
            report_parts.append(f"loss {loss_match.group(1)}")
            
        if report_parts:
            # Overwrite the same line for cleaner progress reporting
            print(f"      → progress: {' | '.join(report_parts)}", end="\r", flush=True)

    while attempt < max_attempts:
        try:
            if cfg.debug_mode:
                print(f"  → Debug: Running {' '.join(cfg.training_command)} (attempt {attempt + 1})")
            
            result = runner.run_streaming(
                cfg.training_command,
                timeout=cfg.training_timeout,
                callback=progress_callback
            )
            # Ensure next print starts on a new line after progress reporting
            print() 
            return result
            
        except subprocess.TimeoutExpired as e:
            print() # New line after potential progress reporting
            attempt += 1
            if attempt >= max_attempts:
                print(f"  → Timeout (>{cfg.training_timeout}s) after {max_attempts} attempts")
                return None
            print(f"  → Timeout (>{cfg.training_timeout}s), retrying... ({attempt + 1}/{max_attempts})")
        except Exception as e:
            print() # New line after potential progress reporting
            attempt += 1
            if attempt >= max_attempts:
                raise e
            print(f"  → Error: {e}, retrying... ({attempt + 1}/{max_attempts})")
            
    return None


def update_train_py(factors: Dict[str, str], file_manager: Optional[FileManager] = None) -> None:
    """Update train.py hyperparameters with validation."""
    update_config_file("train.py", factors, file_manager)


def update_config_file(
    config_file: str, 
    factors: Dict[str, str], 
    file_manager: Optional[FileManager] = None
) -> None:
    """
    Update configuration file variables with robust regex matching.
    
    Args:
        config_file: Path to the file to modify
        factors: Dictionary of variable names and their new values
        file_manager: Optional FileManager instance
    """
    fm = file_manager or FileManager()
    path = Path(config_file)
    content = fm.read_text(path)
    
    original_content = content
    for key, value in factors.items():
        # Robust regex for Python variable assignment
        # Matches:
        #   VAR = VAL
        #   VAR: type = VAL
        #   VAR=VAL
        # Handles comments on the same line and preserves their spacing.
        # Only matches at the start of a line (with optional indentation).
        pattern = rf'^(\s*)({re.escape(key)})(\s*(?::\s*[^=]+)?\s*=\s*)([^#\n]*?)([ \t]*)(#.*)?$'
        
        # Verify if variable exists
        if not re.search(pattern, content, flags=re.MULTILINE):
            raise TaguchiError(f"Variable '{key}' not found in {config_file} with expected assignment pattern.")
            
        replacement = rf'\g<1>\g<2>\g<3>{value}\g<5>\g<6>'
        content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
    
    if content == original_content:
        raise TaguchiError(f"No changes made to {config_file}. Verify factor names and file content.")
        
    fm.write_text(path, content)


def parse_metric(output: str, metric: str) -> Optional[float]:
    """
    Parse metric value from training output.
    
    Returns None if metric not found or invalid format.
    """
    pattern = rf'{re.escape(metric)}:\s*([\d.]+(?:[eE][+-]?\d+)?)'
    match = re.search(pattern, output)
    
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def get_factor_suggestions(factor_type: str) -> Dict[str, List[str]]:
    """Get suggested factor levels for common hyperparameter types."""
    suggestions = {
        "learning_rate": {"MATRIX_LR": ["0.02", "0.04", "0.08"]},
        "depth": {"DEPTH": ["6", "8", "10"]},
        "weight_decay": {"WEIGHT_DECAY": ["0.1", "0.2", "0.3"]},
        "warmup": {"WARMUP_RATIO": ["0.0", "0.1", "0.2"]},
        "architecture": {"WINDOW_PATTERN": ["L", "SSSL", "SSSS"]},
    }
    return suggestions.get(factor_type, {})


if __name__ == "__main__":
    print("Taguchi Mode for Autoresearch")
    print("=" * 60)
    print("\nUsage example:")
    print("""
    from taguchi_mode import run_taguchi_sweep
    
    factors = {
        "DEPTH": ["6", "8", "10"],
        "MATRIX_LR": ["0.02", "0.04", "0.08"],
    }
    
    optimal = run_taguchi_sweep(factors, metric="val_bpb", higher_is_better=False)
    """)
