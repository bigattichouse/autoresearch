"""
System abstractions for Taguchi optimization.

Provides interfaces for file system operations and subprocess execution
to enable better testability and isolation of concerns.
"""

import subprocess
import shutil
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Callable


class SystemRunner:
    """Handles subprocess execution for training and CLI commands."""
    
    def run(
        self, 
        command: List[str], 
        timeout: int, 
        env: Optional[Dict[str, str]] = None, 
        cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Execute a command as a subprocess.
        
        Args:
            command: The command and its arguments as a list of strings
            timeout: Timeout in seconds
            env: Optional environment variables dictionary
            cwd: Optional working directory
            
        Returns:
            CompletedProcess instance
        """
        return subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=cwd
        )

    def run_streaming(
        self,
        command: List[str],
        timeout: int,
        callback: Optional[Callable[[str], None]] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Execute a command and stream stdout/stderr line-by-line.
        
        Args:
            command: The command and its arguments
            timeout: Timeout in seconds
            callback: Function called for each line of output
            env: Optional environment variables
            cwd: Optional working directory
            
        Returns:
            CompletedProcess instance with full captured output
        """
        start_time = time.time()
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
            cwd=cwd,
            bufsize=1,
            universal_newlines=True
        )

        stdout_lines = []
        
        def reader():
            try:
                for line in process.stdout:
                    stdout_lines.append(line)
                    if callback:
                        callback(line.rstrip())
            except Exception:
                pass
            finally:
                process.stdout.close()

        thread = threading.Thread(target=reader)
        thread.daemon = True
        thread.start()

        while thread.is_alive():
            if time.time() - start_time > timeout:
                process.kill()
                thread.join(timeout=2.0)
                raise subprocess.TimeoutExpired(command, timeout, output="".join(stdout_lines))
            time.sleep(0.1)

        returncode = process.wait()
        return subprocess.CompletedProcess(
            args=command,
            returncode=returncode,
            stdout="".join(stdout_lines),
            stderr="" # stderr is redirected to stdout in this implementation
        )


class FileManager:
    """Handles file operations for the 'Backup-Modify-Restore' lifecycle."""
    
    def read_text(self, path: Path) -> str:
        """Read text from a file."""
        return path.read_text()
    
    def write_text(self, path: Path, content: str) -> None:
        """Write text to a file."""
        path.write_text(content)
    
    def exists(self, path: Path) -> bool:
        """Check if a path exists."""
        return path.exists()
    
    def which(self, cmd: str) -> Optional[str]:
        """Locate a command in the system PATH."""
        return shutil.which(cmd)

    def is_executable(self, path: Path) -> bool:
        """Check if a path is an executable file."""
        import os
        return path.exists() and os.access(path, os.X_OK)

    def remove(self, path: Path) -> None:
        """Remove a file."""
        if path.exists():
            path.unlink()

    def create_temp_file(self, suffix: str = "", content: Optional[str] = None) -> Path:
        """Create a temporary file and optionally write content to it."""
        import tempfile
        import os
        fd, path_str = tempfile.mkstemp(suffix=suffix)
        path = Path(path_str)
        try:
            if content is not None:
                with os.fdopen(fd, 'w') as f:
                    f.write(content)
            else:
                os.close(fd)
        except Exception:
            os.close(fd)
            path.unlink(missing_ok=True)
            raise
        return path
