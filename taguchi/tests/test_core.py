import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import subprocess
from taguchi.core import Taguchi
from taguchi.errors import TaguchiError, CommandExecutionError, TimeoutError
from taguchi.system import SystemRunner, FileManager

@pytest.fixture
def mock_runner():
    return MagicMock(spec=SystemRunner)

@pytest.fixture
def mock_file_manager():
    fm = MagicMock(spec=FileManager)
    fm.exists.return_value = True
    fm.is_executable.return_value = True
    fm.which.return_value = "/mock/path/taguchi"
    return fm

@pytest.fixture
def taguchi(mock_runner, mock_file_manager):
    return Taguchi(cli_path="/mock/path/taguchi", runner=mock_runner, file_manager=mock_file_manager)

def test_find_cli_explicit(mock_runner, mock_file_manager):
    mock_file_manager.is_executable.side_effect = lambda p: str(p) == "/custom/taguchi"
    t = Taguchi(cli_path="/custom/taguchi", runner=mock_runner, file_manager=mock_file_manager)
    assert t._cli_path == "/custom/taguchi"

def test_find_cli_not_found(mock_runner, mock_file_manager):
    mock_file_manager.exists.return_value = False
    mock_file_manager.is_executable.return_value = False
    mock_file_manager.which.return_value = None
    with pytest.raises(TaguchiError, match="Could not find taguchi CLI"):
        Taguchi(runner=mock_runner, file_manager=mock_file_manager)

def test_run_command_success(taguchi, mock_runner):
    mock_runner.run.return_value = MagicMock(returncode=0, stdout="success output")
    result = taguchi._run_command(["test"])
    assert result == "success output"
    mock_runner.run.assert_called_once()

def test_run_command_failure(taguchi, mock_runner):
    mock_runner.run.return_value = MagicMock(returncode=1, stdout="", stderr="error message")
    with pytest.raises(CommandExecutionError):
        taguchi._run_command(["test"])

def test_run_command_timeout(taguchi, mock_runner):
    mock_runner.run.side_effect = subprocess.TimeoutExpired(["taguchi"], 30)
    with pytest.raises(TimeoutError):
        taguchi._run_command(["test"])

def test_list_arrays(taguchi, mock_runner):
    mock_runner.run.return_value = MagicMock(
        returncode=0, 
        stdout="  L4 (4 runs, 3 cols, 2 levels)\n  L8 (8 runs, 7 cols, 2 levels)"
    )
    arrays = taguchi.list_arrays()
    assert arrays == ["L4", "L8"]
    assert taguchi.get_array_info("L4") == {"rows": 4, "cols": 3, "levels": 2}

def test_suggest_array(taguchi, mock_runner):
    mock_runner.run.return_value = MagicMock(
        returncode=0, 
        stdout="  L4 (4 runs, 3 cols, 2 levels)\n  L9 (9 runs, 4 cols, 3 levels)"
    )
    # 2 factors, 2 levels -> L4
    assert taguchi.suggest_array(2, 2) == "L4"
    # 2 factors, 3 levels -> L9
    assert taguchi.suggest_array(2, 3) == "L9"
    # 5 factors, 2 levels -> L9 (best effort, L4 too small)
    assert taguchi.suggest_array(5, 2) == "L9"

def test_generate_runs_from_file(taguchi, mock_runner, mock_file_manager):
    mock_file_manager.exists.return_value = True
    mock_runner.run.return_value = MagicMock(
        returncode=0,
        stdout="Run 1: factor1=val1, factor2=val2\nRun 2: factor1=val3, factor2=val4"
    )
    runs = taguchi.generate_runs("experiment.tgu")
    assert len(runs) == 2
    assert runs[0]["run_id"] == 1
    assert runs[0]["factors"] == {"factor1": "val1", "factor2": "val2"}
    mock_file_manager.create_temp_file.assert_not_called()

def test_generate_runs_from_content(taguchi, mock_runner, mock_file_manager):
    mock_file_manager.exists.return_value = False
    mock_file_manager.create_temp_file.return_value = Path("/tmp/temp.tgu")
    mock_runner.run.return_value = MagicMock(
        returncode=0,
        stdout="Run 1: f=v"
    )
    runs = taguchi.generate_runs("raw content")
    assert len(runs) == 1
    mock_file_manager.create_temp_file.assert_called_once()
    mock_file_manager.remove.assert_called_once_with(Path("/tmp/temp.tgu"))

def test_generate_runs_disk_error(taguchi, mock_file_manager):
    mock_file_manager.exists.return_value = False
    mock_file_manager.create_temp_file.side_effect = OSError("Disk full")
    with pytest.raises(OSError, match="Disk full"):
        taguchi.generate_runs("raw content")

def test_parse_effects(taguchi):
    output = """
factor1    0.500   L1=1.0, L2=1.5
factor2    1.200   L1=2.0, L2=0.8, L3=1.5
"""
    effects = taguchi._parse_effects(output)
    assert len(effects) == 2
    assert effects[0]["factor"] == "factor1"
    assert effects[0]["range"] == 0.5
    assert effects[0]["level_means"] == [1.0, 1.5]
    assert effects[1]["factor"] == "factor2"
    assert effects[1]["range"] == 1.2
    assert effects[1]["level_means"] == [2.0, 0.8, 1.5]

def test_malformed_list_arrays(taguchi, mock_runner):
    mock_runner.run.return_value = MagicMock(returncode=0, stdout="garbage")
    with pytest.raises(TaguchiError, match="list-arrays returned no arrays"):
        taguchi.list_arrays()
