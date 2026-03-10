"""
Core Taguchi library interface using shell commands.
"""

import os
import re
import subprocess
from pathlib import Path
from typing import List, Optional, Dict, Any

from .system import SystemRunner, FileManager
from .errors import TaguchiError, CommandExecutionError, TimeoutError

# Subprocess timeout in seconds — prevents hangs if the binary stalls.
_CLI_TIMEOUT = 30


class Taguchi:
    """
    Python interface to the Taguchi orthogonal array CLI tool.
    Uses shell commands which is more robust than ctypes for complex structures.
    """

    def __init__(
        self, 
        cli_path: Optional[str] = None,
        runner: Optional[SystemRunner] = None,
        file_manager: Optional[FileManager] = None
    ):
        self._runner = runner or SystemRunner()
        self._file_manager = file_manager or FileManager()
        self._cli_path = self._find_cli(cli_path)
        self._array_cache: Optional[List[Dict]] = None

    def _find_cli(self, cli_path: Optional[str]) -> str:
        """Find the taguchi CLI binary."""
        possible_paths: List[Path] = []

        if cli_path:
            possible_paths.append(Path(cli_path))

        # Search relative to this file and common locations
        current_dir = Path(__file__).parent
        project_root = current_dir.parent  # autoresearch root
        possible_paths.extend([
            project_root / "taguchi_cli",  # In autoresearch root
            current_dir.parent.parent.parent / "build" / "taguchi",
            current_dir.parent.parent / "build" / "taguchi",
        ])

        # Common system install locations
        possible_paths.extend([
            Path("/usr/local/bin/taguchi"),
            Path("/usr/bin/taguchi"),
        ])

        for path in possible_paths:
            if self._file_manager.is_executable(path):
                return str(path.absolute())

        # Fall back to PATH lookup
        found = self._file_manager.which("taguchi")
        if found:
            return found

        raise TaguchiError("Could not find taguchi CLI. Build with 'make' first.")

    def _run_command(self, args: List[str]) -> str:
        """Run a taguchi command and return stdout."""
        cmd = [self._cli_path] + args
        try:
            result = self._runner.run(
                cmd,
                timeout=_CLI_TIMEOUT,
            )
        except subprocess.TimeoutExpired:
            raise TimeoutError(
                cmd,
                _CLI_TIMEOUT,
                operation="cli_execution",
                cli_path=self._cli_path
            )
        
        if result.returncode != 0:
            raise CommandExecutionError.from_subprocess_error(
                cmd,
                result,
                operation="cli_execution",
                cli_path=self._cli_path
            )
        return result.stdout

    def _parse_list_arrays(self, output: str) -> List[Dict]:
        """Parse the output of 'list-arrays' command."""
        arrays = []
        for line in output.strip().split('\n'):
            match = re.search(
                r'(L\d+)\s+\(\s*(\d+)\s+runs,\s*(\d+)\s+cols,\s*(\d+)\s+levels\)',
                line,
            )
            if match:
                arrays.append({
                    'name': match.group(1),
                    'rows': int(match.group(2)),
                    'cols': int(match.group(3)),
                    'levels': int(match.group(4)),
                })
        return arrays

    def _get_arrays_info(self) -> List[Dict]:
        """Return cached array metadata."""
        if self._array_cache is not None:
            return self._array_cache

        output = self._run_command(["list-arrays"])
        arrays = self._parse_list_arrays(output)

        if not arrays:
            raise TaguchiError(
                "list-arrays returned no arrays — CLI output may have changed format",
                operation="list_arrays",
                stdout=output
            )

        self._array_cache = arrays
        return arrays

    def list_arrays(self) -> List[str]:
        """List all available orthogonal array names."""
        return [a['name'] for a in self._get_arrays_info()]

    def get_array_info(self, name: str) -> dict:
        """Get run/column/level counts for a named array."""
        for array in self._get_arrays_info():
            if array['name'] == name:
                return {
                    'rows': array['rows'],
                    'cols': array['cols'],
                    'levels': array['levels'],
                }
        raise TaguchiError(f"Array '{name}' not found", operation="get_array_info")

    def suggest_array(self, num_factors: int, max_levels: int) -> str:
        """Suggest the smallest orthogonal array that fits the experiment."""
        if num_factors < 1:
            raise TaguchiError("num_factors must be at least 1")
        if max_levels < 2:
            raise TaguchiError("max_levels must be at least 2")

        arrays = self._get_arrays_info()

        # Prefer arrays whose native level count matches; fall back to any
        candidates = [a for a in arrays if a['levels'] >= max_levels] or arrays

        # Among candidates, keep those with enough columns
        sufficient = [a for a in candidates if a['cols'] >= num_factors]
        if not sufficient:
            # No perfect fit — return the largest available as best effort
            return max(candidates, key=lambda a: a['cols'])['name']

        # Return the smallest sufficient array (fewest runs)
        return min(sufficient, key=lambda a: a['rows'])['name']

    def _parse_generate(self, output: str) -> List[Dict[str, Any]]:
        """Parse the output of 'generate' command."""
        runs = []
        for line in output.strip().split("\n"):
            if not line.startswith("Run "):
                continue
            parts = line.split(": ", 1)
            if len(parts) < 2:
                continue
            try:
                run_id_str = parts[0][4:].strip()
                run_id = int(run_id_str)
            except ValueError:
                continue
            factors: Dict[str, str] = {}
            for pair in parts[1].split(", "):
                if "=" in pair:
                    key, _, value = pair.partition("=")
                    factors[key.strip()] = value.strip()
            runs.append({"run_id": run_id, "factors": factors})
        return runs

    def generate_runs(self, tgu_path: str) -> List[Dict[str, Any]]:
        """
        Generate experiment runs from a .tgu file path or raw .tgu content string.

        Returns a list of dicts: [{'run_id': int, 'factors': {name: value}}, ...]
        """
        if self._file_manager.exists(Path(tgu_path)):
            output = self._run_command(["generate", tgu_path])
        else:
            # Treat the argument as raw .tgu content
            temp_path = self._file_manager.create_temp_file(suffix='.tgu', content=tgu_path)
            try:
                output = self._run_command(["generate", str(temp_path)])
            finally:
                self._file_manager.remove(temp_path)

        return self._parse_generate(output)

    def analyze(self, tgu_path: str, results_csv: str, metric: str = "response") -> str:
        """Run full analysis with main effects and optimal recommendations."""
        return self._run_command(
            ["analyze", tgu_path, results_csv, "--metric", metric]
        )

    def effects(self, tgu_path: str, results_csv: str, metric: str = "response") -> str:
        """Calculate and return the main effects table."""
        return self._run_command(
            ["effects", tgu_path, results_csv, "--metric", metric]
        )

    def _parse_effects(self, output: str) -> List[Dict]:
        """
        Parse the main-effects table from CLI output.
        """
        effects = []
        for line in output.strip().split('\n'):
            # Factor name (word chars), range (number), then level means
            match = re.match(r'\s*(\w+)\s+([\d.]+)\s+(.+)', line)
            if not match:
                continue

            factor = match.group(1)
            try:
                range_val = float(match.group(2))
            except ValueError:
                continue

            means_str = match.group(3)
            # Match L<n>=<signed float> — handles negatives and scientific notation
            level_matches = re.findall(r'L\d+=(-?[\d.]+(?:[eE][+-]?\d+)?)', means_str)
            means = []
            for m in level_matches:
                try:
                    means.append(float(m))
                except ValueError:
                    pass

            if means:
                effects.append({
                    'factor': factor,
                    'range': range_val,
                    'level_means': means,
                })

        return effects
