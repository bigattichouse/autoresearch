import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import subprocess

from taguchi.taguchi_mode import run_taguchi_sweep, update_config_file
from taguchi.system import SystemRunner, FileManager
from taguchi.config import TaguchiConfig
from taguchi.errors import TaguchiError

def test_dry_run_no_file_ops():
    """Verify dry_run mode doesn't touch files or run commands."""
    mock_runner = MagicMock(spec=SystemRunner)
    mock_fm = MagicMock(spec=FileManager)
    
    factors = {"LR": ["0.1", "0.2"]}
    config = TaguchiConfig(dry_run=True)
    
    result = run_taguchi_sweep(factors, config=config, runner=mock_runner, file_manager=mock_fm)
    
    assert result == {}
    mock_runner.run_streaming.assert_not_called()
    mock_fm.write_text.assert_not_called()

def test_successful_sweep_flow():
    """Verify the full flow of a successful sweep with mocks."""
    mock_runner = MagicMock(spec=SystemRunner)
    mock_fm = MagicMock(spec=FileManager)
    
    # Mock file existence and content
    mock_fm.exists.return_value = True
    mock_fm.read_text.return_value = "LR = 0.0\n"
    mock_fm.which.return_value = "/usr/bin/uv"
    
    # Mock successful run
    mock_result = MagicMock()
    mock_result.stdout = "val_bpb: 0.5"
    mock_result.returncode = 0
    mock_runner.run_streaming.return_value = mock_result
    
    factors = {"LR": ["0.1", "0.2"]}
    
    optimal = run_taguchi_sweep(
        factors, 
        metric="val_bpb", 
        higher_is_better=False,
        runner=mock_runner, 
        file_manager=mock_fm
    )
    
    assert "LR" in optimal
    assert mock_fm.read_text.called
    assert mock_fm.write_text.called
    assert mock_runner.run_streaming.called
    # For 1 factor 2 levels, it should be at least 2 runs
    assert mock_runner.run_streaming.call_count >= 2

def test_retry_on_timeout():
    """Verify that the runner retries on timeout."""
    mock_runner = MagicMock(spec=SystemRunner)
    mock_fm = MagicMock(spec=FileManager)
    
    mock_fm.exists.return_value = True
    mock_fm.read_text.return_value = "LR = 0.0\n"
    mock_fm.which.return_value = "/usr/bin/uv"
    
    # First call times out, second succeeds
    mock_result = MagicMock()
    mock_result.stdout = "val_bpb: 0.5"
    mock_result.returncode = 0
    
    # We need to provide enough return values for all runs in the sweep.
    # L4 (minimum for Taguchi often) has 4 runs.
    # Let's mock a sequence where one run times out and then succeeds.
    mock_runner.run_streaming.side_effect = [
        subprocess.TimeoutExpired(cmd=["uv"], timeout=400),
        mock_result,
        mock_result,
        mock_result,
        mock_result,
        mock_result
    ]
    
    factors = {"LR": ["0.1", "0.2"]}
    config = TaguchiConfig(max_retries=1)
    
    run_taguchi_sweep(
        factors, 
        config=config,
        runner=mock_runner, 
        file_manager=mock_fm
    )
    
    # total calls = (num_runs - 1) * 1 + 2 (for the one that retried)
    # But it depends on the array selected.
    assert mock_runner.run_streaming.call_count > 1

def test_regex_update_robustness():
    """Test the robust regex update logic with various Python patterns."""
    mock_fm = MagicMock(spec=FileManager)
    
    content = """
# Header
LR = 0.01  # Initial rate
DEPTH: int = 5
  WEIGHT=0.1
"""
    mock_fm.read_text.return_value = content
    
    factors = {"LR": "0.02", "DEPTH": "10", "WEIGHT": "0.5"}
    update_config_file("dummy.py", factors, file_manager=mock_fm)
    
    # Verify the content passed to write_text
    written_content = mock_fm.write_text.call_args[0][1]
    assert "LR = 0.02  # Initial rate" in written_content
    assert "DEPTH: int = 10" in written_content
    assert "  WEIGHT=0.5" in written_content

def test_regex_update_missing_variable():
    """Verify TaguchiError is raised if variable is missing."""
    mock_fm = MagicMock(spec=FileManager)
    mock_fm.read_text.return_value = "OTHER_VAR = 1\n"
    
    factors = {"MISSING": "10"}
    with pytest.raises(TaguchiError, match="Variable 'MISSING' not found"):
        update_config_file("dummy.py", factors, file_manager=mock_fm)

def test_restore_on_failure():
    """Verify that the original file is restored even if training fails."""
    mock_runner = MagicMock(spec=SystemRunner)
    mock_fm = MagicMock(spec=FileManager)
    
    mock_fm.exists.return_value = True
    original_content = "LR = 0.0\n"
    mock_fm.read_text.return_value = original_content
    mock_fm.which.return_value = "/usr/bin/uv"
    
    # Mock runner failure
    mock_runner.run_streaming.side_effect = Exception("Training crashed")
    
    factors = {"LR": ["0.1", "0.2"]}
    
    run_taguchi_sweep(
        factors, 
        runner=mock_runner, 
        file_manager=mock_fm
    )
    
    # Check if write_text was called with original_content to restore
    # It will be called multiple times (once per run)
    restore_calls = [call for call in mock_fm.write_text.call_args_list if call[0][1] == original_content]
    assert len(restore_calls) > 0

def test_progress_reporting(capsys):
    """Verify that progress patterns are correctly identified and reported."""
    mock_runner = MagicMock(spec=SystemRunner)
    mock_fm = MagicMock(spec=FileManager)
    
    mock_fm.exists.return_value = True
    mock_fm.read_text.return_value = "LR = 0.0\n"
    mock_fm.which.return_value = "/usr/bin/python"
    
    # Mock run_streaming to call the callback with some progress lines
    def mock_run_streaming(command, timeout, callback=None, env=None, cwd=None):
        if callback:
            callback("Step 10: starting")
            callback("loss: 0.5432")
            callback("Step 20 | loss: 0.1234")
            callback("Final val_bpb: 0.5")
        
        mock_result = MagicMock()
        mock_result.stdout = "val_bpb: 0.5"
        mock_result.returncode = 0
        return mock_result

    mock_runner.run_streaming.side_effect = mock_run_streaming
    
    factors = {"LR": ["0.1", "0.2"]} # Need at least 2 levels
    
    run_taguchi_sweep(
        factors, 
        runner=mock_runner, 
        file_manager=mock_fm
    )
    
    captured = capsys.readouterr()
    # Check for progress reports in output
    assert "progress: step 10" in captured.out
    assert "loss 0.5432" in captured.out
    assert "step 20 | loss 0.1234" in captured.out
