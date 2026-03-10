import pytest
from unittest.mock import MagicMock
from pathlib import Path
from taguchi.analyzer import Analyzer
from taguchi.core import Taguchi
from taguchi.system import FileManager
from taguchi.errors import TaguchiError

@pytest.fixture
def mock_experiment():
    exp = MagicMock()
    exp.get_tgu_path.return_value = "experiment.tgu"
    exp.factors = {"factor1": ["v1", "v2"], "factor2": ["v3", "v4", "v5"]}
    return exp

@pytest.fixture
def mock_taguchi():
    return MagicMock(spec=Taguchi)

@pytest.fixture
def mock_file_manager():
    fm = MagicMock(spec=FileManager)
    fm.create_temp_file.return_value = Path("/tmp/results.csv")
    return fm

@pytest.fixture
def analyzer(mock_experiment, mock_taguchi, mock_file_manager):
    return Analyzer(
        experiment=mock_experiment,
        taguchi=mock_taguchi,
        file_manager=mock_file_manager
    )

def test_add_results(analyzer):
    analyzer.add_result(1, 0.5)
    analyzer.add_results_from_dict({2: 0.8, 3: 0.2})
    assert analyzer._results == {1: 0.5, 2: 0.8, 3: 0.2}

def test_main_effects_calls_cli(analyzer, mock_taguchi, mock_file_manager):
    analyzer.add_result(1, 0.5)
    mock_taguchi.effects.return_value = "mock output"
    mock_taguchi._parse_effects.return_value = [{"factor": "f1", "range": 0.5, "level_means": [1.0, 1.5]}]
    
    effects = analyzer.main_effects()
    
    assert effects[0]["factor"] == "f1"
    mock_taguchi.effects.assert_called_once()
    mock_taguchi._parse_effects.assert_called_once_with("mock output")
    mock_file_manager.create_temp_file.assert_called_once()

def test_main_effects_raw_data(analyzer, mock_taguchi):
    raw_output = "some raw output"
    mock_taguchi._parse_effects.return_value = [{"factor": "f1", "range": 0.5, "level_means": [1.0, 1.5]}]
    
    effects = analyzer.main_effects(raw_output=raw_output)
    
    assert effects[0]["factor"] == "f1"
    mock_taguchi._parse_effects.assert_called_once_with(raw_output)
    mock_taguchi.effects.assert_not_called()

def test_recommend_optimal(analyzer, mock_taguchi):
    mock_taguchi._parse_effects.return_value = [
        {"factor": "factor1", "range": 0.5, "level_means": [1.0, 1.5]}, # L2 is better (1.5 > 1.0)
        {"factor": "factor2", "range": 1.2, "level_means": [2.0, 0.8, 1.5]} # L1 is better (2.0)
    ]
    # We need to simulate main_effects already having data or being called
    analyzer._effects = mock_taguchi._parse_effects.return_value
    
    optimal = analyzer.recommend_optimal(higher_is_better=True)
    assert optimal == {"factor1": "v2", "factor2": "v3"} # factor1 L2="v2", factor2 L1="v3"

    optimal_lower = analyzer.recommend_optimal(higher_is_better=False)
    assert optimal_lower == {"factor1": "v1", "factor2": "v4"} # factor1 L1="v1", factor2 L2="v4"

def test_significant_factors(analyzer, mock_taguchi):
    mock_taguchi._parse_effects.return_value = [
        {"factor": "f1", "range": 1.0, "level_means": [1, 2]},
        {"factor": "f2", "range": 0.05, "level_means": [1, 1.05]},
        {"factor": "f3", "range": 0.5, "level_means": [1, 1.5]}
    ]
    analyzer._effects = mock_taguchi._parse_effects.return_value
    
    sig = analyzer.get_significant_factors(threshold=0.1) # > 1.0 * 0.1 = 0.1
    assert sig == ["f1", "f3"]

def test_no_results_error(analyzer):
    with pytest.raises(TaguchiError, match="No results added"):
        analyzer.main_effects()

def test_cleanup(analyzer, mock_file_manager):
    analyzer._csv_path = Path("/tmp/test.csv")
    analyzer.cleanup()
    mock_file_manager.remove.assert_called_once_with(Path("/tmp/test.csv"))
    assert analyzer._csv_path is None

def test_summary(analyzer, mock_taguchi):
    mock_taguchi._parse_effects.return_value = [
        {"factor": "factor1", "range": 0.5, "level_means": [1.0, 1.5]}
    ]
    analyzer._effects = mock_taguchi._parse_effects.return_value
    
    summary = analyzer.summary()
    assert "Taguchi Experiment Analysis" in summary
    assert "factor1" in summary
    assert "0.5000" in summary
