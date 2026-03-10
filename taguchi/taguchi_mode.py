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
import shutil
import os
from pathlib import Path
from typing import Dict, List, Optional

from . import Experiment, Analyzer, TaguchiError
from .signal_analysis import SignalAnalyzer


# Basic configuration from environment variables
def get_config():
    """Get configuration from environment variables with defaults."""
    return {
        'training_timeout': int(os.getenv('TAGUCHI_TRAINING_TIMEOUT', '400')),
        'training_command': os.getenv('TAGUCHI_TRAINING_CMD', 'uv run train.py').split(),
        'config_file': os.getenv('TAGUCHI_CONFIG_FILE', 'train.py'),
        'debug_mode': os.getenv('TAGUCHI_DEBUG', 'false').lower() == 'true',
        'max_retries': int(os.getenv('TAGUCHI_MAX_RETRIES', '0')),
    }


def run_taguchi_sweep(
    factors: Dict[str, List[str]],
    metric: str = "val_bpb",
    higher_is_better: bool = False,
    array_type: Optional[str] = None,
    config: Optional[Dict] = None,
) -> Dict[str, str]:
    """
    Execute a Taguchi orthogonal array experimental design for hyperparameter optimization.
    
    Implements systematic experimental design with automatic resource management.
    
    Args:
        factors: Dict mapping factor names to list of level values
        metric: Metric name to optimize (default: "val_bpb")
        higher_is_better: If True, maximize metric; if False, minimize
        array_type: Specific orthogonal array (e.g., "L9"). If None, auto-select.
        config: Optional config dict. If None, loads from environment variables.
    
    Environment Variables:
        TAGUCHI_TRAINING_TIMEOUT: Training command timeout in seconds (default: 400)
        TAGUCHI_TRAINING_CMD: Training command (default: "uv run train.py")
        TAGUCHI_CONFIG_FILE: Config file to modify (default: "train.py")
        TAGUCHI_DEBUG: Enable debug output (default: false)
        TAGUCHI_MAX_RETRIES: Max retries for training (default: 0)
    
    Returns:
        Dict mapping factor names to optimal level values
    """
    # Load configuration
    cfg = config or get_config()
    with Experiment(array_type=array_type) as exp:
        for name, levels in factors.items():
            exp.add_factor(name, levels)
        
        runs = exp.generate()
        
        print(f"\n{'='*60}")
        print(f"Taguchi Hyperparameter Sweep")
        print(f"{'='*60}")
        print(f"Array: {exp.array_type} ({exp.num_runs} runs)")
        print(f"Factors: {len(factors)}")
        print(f"Metric: {metric} ({'higher' if higher_is_better else 'lower'} is better)")
        print(f"{'='*60}\n")
        
        with Analyzer(exp, metric_name=metric) as analyzer:
            for i, run in enumerate(runs):
                print(f"\n[{i+1}/{len(runs)}] Run {run['run_id']}: {run['factors']}")
                
                # Fix critical race condition: backup inside try block
                backup = None
                try:
                    # Validate config file exists before proceeding
                    config_file_path = Path(cfg['config_file'])
                    if not config_file_path.exists():
                        print(f"  → Error: {cfg['config_file']} not found in current directory")
                        continue
                    
                    backup = config_file_path.read_text()
                    
                    # Update configuration file with factors
                    if cfg['config_file'] == 'train.py':
                        update_train_py(run['factors'])
                    else:
                        # For non-train.py files, use generic update
                        update_config_file(cfg['config_file'], run['factors'])
                    
                    # Validate training command exists
                    cmd_executable = cfg['training_command'][0]
                    if not shutil.which(cmd_executable):
                        print(f"  → Error: '{cmd_executable}' command not found")
                        continue
                    
                    # Execute training with retry logic
                    attempt = 0
                    max_attempts = cfg['max_retries'] + 1
                    
                    while attempt < max_attempts:
                        try:
                            if cfg['debug_mode']:
                                print(f"  → Debug: Running {' '.join(cfg['training_command'])} (attempt {attempt + 1})")
                            
                            result = subprocess.run(
                                cfg['training_command'],
                                capture_output=True,
                                text=True,
                                timeout=cfg['training_timeout']
                            )
                            break  # Success, exit retry loop
                            
                        except subprocess.TimeoutExpired:
                            attempt += 1
                            if attempt >= max_attempts:
                                raise
                            print(f"  → Timeout (>{cfg['training_timeout']}s), retrying... ({attempt + 1}/{max_attempts})")
                            continue
                        except Exception as e:
                            attempt += 1
                            if attempt >= max_attempts:
                                raise
                            print(f"  → Error: {e}, retrying... ({attempt + 1}/{max_attempts})")
                            continue
                    
                    value = parse_metric(result.stdout, metric)
                    if value is not None:
                        print(f"  → {metric}: {value}")
                        analyzer.add_result(run['run_id'], value)
                    else:
                        print(f"  → Failed to parse {metric}")
                        if result.returncode != 0:
                            print(f"  → Exit code: {result.returncode}")
                            stderr_preview = (result.stderr.strip()[:100] + "...") if len(result.stderr.strip()) > 100 else result.stderr.strip()
                            if stderr_preview:
                                print(f"  → Error: {stderr_preview}")
                            
                except subprocess.TimeoutExpired:
                    print(f"  → Timeout (>400s)")
                except Exception as e:
                    print(f"  → Error: {e}")
                finally:
                    # Only restore if backup was successfully created
                    if backup is not None:
                        try:
                            Path(cfg['config_file']).write_text(backup)
                        except Exception as restore_error:
                            print(f"  → Critical: Failed to restore {cfg['config_file']}: {restore_error}")
                            print(f"  → Manual intervention required!")
            
            if not analyzer._results:
                print("\nNo successful runs!")
                return {}
            
            print(f"\n{'='*60}")
            print(f"Analysis ({len(analyzer._results)}/{len(runs)} successful)")
            print(f"{'='*60}")
            print(analyzer.summary())
            
            optimal = analyzer.recommend_optimal(higher_is_better=higher_is_better)
            print(f"\nRecommended:")
            for factor, level in optimal.items():
                print(f"  {factor}: {level}")
            
            # Basic SNR Analysis for original version  
            if cfg.get('debug_mode', False):
                print(f"\n{'='*60}")
                print("SIGNAL-TO-NOISE RATIO ANALYSIS (Debug Mode)")
                print(f"{'='*60}")
                
                signal_analyzer = SignalAnalyzer()
                signal_analyzer.set_experimental_data(runs, analyzer._results, factors)
                
                # Generate basic SNR report
                snr_report = signal_analyzer.generate_signal_report(higher_is_better)
                print(snr_report)
            
            return optimal


def update_train_py(factors: Dict[str, str]) -> None:
    """
    Update train.py hyperparameters with validation.
    
    Validates that all required variables exist before making any changes.
    Raises TaguchiError if any variables are missing or updates fail.
    """
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
    
    # Apply replacements with safer pattern matching
    original_content = content
    for key, value in factors.items():
        pattern = rf'^(\s*)({re.escape(key)})\s*=\s*[^#\n]+(#.*)?$'
        replacement = rf'\1\2 = {value}\3'
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Verify the replacement actually happened
        if new_content == content:
            raise TaguchiError(f"Failed to update variable: {key}")
        content = new_content
    
    # Verify we actually made changes
    if content == original_content:
        raise TaguchiError("No variables were updated - check factor names")
    
    train_py.write_text(content)


def update_config_file(config_file: str, factors: Dict[str, str]) -> None:
    """
    Generic config file update function.
    
    Uses the same validation and safety checks as update_train_py.
    """
    config_path = Path(config_file)
    content = config_path.read_text()
    
    # Validate all required variables exist first
    missing_vars = []
    for key in factors.keys():
        pattern = rf'^(\s*){re.escape(key)}\s*='
        if not re.search(pattern, content, flags=re.MULTILINE):
            missing_vars.append(key)
    
    if missing_vars:
        raise TaguchiError(f"Variables not found in {config_file}: {missing_vars}")
    
    # Apply replacements with safer pattern matching
    original_content = content
    for key, value in factors.items():
        pattern = rf'^(\s*)({re.escape(key)})\s*=\s*[^#\n]+(#.*)?$'
        replacement = rf'\1\2 = {value}\3'
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        # Verify the replacement actually happened
        if new_content == content:
            raise TaguchiError(f"Failed to update variable: {key}")
        content = new_content
    
    # Verify we actually made changes
    if content == original_content:
        raise TaguchiError("No variables were updated - check factor names")
    
    config_path.write_text(content)


def parse_metric(output: str, metric: str) -> Optional[float]:
    """
    Parse metric value from training output with better error handling.
    
    Returns None if metric not found or invalid format.
    """
    pattern = rf'{re.escape(metric)}:\s*([\d.]+(?:[eE][+-]?\d+)?)'
    match = re.search(pattern, output)
    
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            print(f"  → Warning: Found {metric} but could not parse value: {match.group(1)}")
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
