"""
Taguchi Array Tool - Python Bindings

A Python interface to the Taguchi orthogonal array library for design of experiments.

Basic Usage:
    from taguchi import Experiment, Analyzer
    
    exp = Experiment()
    exp.add_factor("temp", ["350F", "375F", "400F"])
    runs = exp.generate()

Advanced Usage:
    from taguchi import Experiment, Analyzer, TaguchiConfig, Taguchi
    
    config = TaguchiConfig(cli_timeout=120, debug_mode=True)
    taguchi = Taguchi(config=config)
    
    with Experiment(taguchi=taguchi) as exp:
        exp.add_factor("temp", ["350F", "375F", "400F"])
        runs = exp.generate()
        
        with Analyzer(exp, taguchi=taguchi) as analyzer:
            analyzer.add_results_from_dict({1: 0.95, 2: 0.87, 3: 0.92})
            print(analyzer.summary())

Environment Variables:
    TAGUCHI_CLI_PATH       - Path to CLI binary
    TAGUCHI_CLI_TIMEOUT    - Command timeout in seconds  
    TAGUCHI_DEBUG          - Enable debug logging (true/false)
    TAGUCHI_MAX_RETRIES    - Number of retry attempts
"""

from .core import Taguchi, TaguchiError
from .experiment import Experiment  
from .analyzer import Analyzer
from .config import TaguchiConfig
from .errors import (
    BinaryDiscoveryError, CommandExecutionError, 
    TimeoutError, ValidationError
)

__version__ = "1.0.0"

__all__ = [
    "Taguchi", 
    "TaguchiError",
    "Experiment", 
    "Analyzer",
    "TaguchiConfig",
    "BinaryDiscoveryError",
    "CommandExecutionError", 
    "TimeoutError",
    "ValidationError",
]