"""
Shell Utilities Module

Provides reusable functions for shell command execution, process management, and system operations.
Designed to be consistent with the existing codebase patterns.
"""

import os
import shlex
import subprocess
import sys
import tempfile
from typing import List, Optional, Tuple, Union


def run_command(cmd: Union[str, List[str]], cwd: Optional[str] = None, check: bool = True, capture: bool = False, timeout: Optional[int] = None) -> subprocess.CompletedProcess:
    """
    Run a shell command with consistent error handling and logging.
    
    Args:
        cmd: Command to run (string or list of strings)
        cwd: Working directory for the command
        check: Whether to raise exception on non-zero exit code
        capture: Whether to capture stdout/stderr
        timeout: Command timeout in seconds
        
    Returns:
        CompletedProcess object with command results
    """
    if isinstance(cmd, list):
        cmd_str = " ".join(shlex.quote(arg) for arg in cmd)
    else:
        cmd_str = cmd
    
    print(f"+ {cmd_str}")
    
    if capture:
        return subprocess.run(
            cmd, 
            cwd=cwd, 
            shell=isinstance(cmd, str), 
            check=check, 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True,
            timeout=timeout
        )
    else:
        return subprocess.run(
            cmd, 
            cwd=cwd, 
            shell=isinstance(cmd, str), 
            check=check,
            timeout=timeout
        )


def run_command_safe(cmd: Union[str, List[str]], cwd: Optional[str] = None, capture: bool = False, timeout: Optional[int] = None) -> Tuple[bool, subprocess.CompletedProcess]:
    """
    Run a command safely without raising exceptions.
    
    Args:
        cmd: Command to run (string or list of strings)
        cwd: Working directory for the command
        capture: Whether to capture stdout/stderr
        timeout: Command timeout in seconds
        
    Returns:
        Tuple of (success, CompletedProcess)
    """
    try:
        result = run_command(cmd, cwd=cwd, check=False, capture=capture, timeout=timeout)
        return result.returncode == 0, result
    except subprocess.TimeoutExpired as e:
        return False, e
    except Exception as e:
        return False, e


def which(program: str) -> Optional[str]:
    """
    Find the full path of an executable program.
    
    Args:
        program: Program name to find
        
    Returns:
        Full path if found, None otherwise
    """
    import shutil
    return shutil.which(program)


def is_command_available(command: str) -> bool:
    """
    Check if a command is available in the system PATH.
    
    Args:
        command: Command name to check
        
    Returns:
        True if command is available, False otherwise
    """
    return which(command) is not None


def create_temp_file(suffix: str = "", prefix: str = "tmp", content: str = "") -> str:
    """
    Create a temporary file with optional content.
    
    Args:
        suffix: File suffix
        prefix: File prefix
        content: Initial content to write
        
    Returns:
        Path to the temporary file
    """
    with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, prefix=prefix, delete=False) as f:
        if content:
            f.write(content)
        return f.name


def create_temp_dir(suffix: str = "", prefix: str = "tmp") -> str:
    """
    Create a temporary directory.
    
    Args:
        suffix: Directory suffix
        prefix: Directory prefix
        
    Returns:
        Path to the temporary directory
    """
    return tempfile.mkdtemp(suffix=suffix, prefix=prefix)


def cleanup_temp_file(file_path: str) -> None:
    """
    Clean up a temporary file.
    
    Args:
        file_path: Path to the temporary file
    """
    try:
        os.unlink(file_path)
    except OSError:
        pass  # File may not exist or already be deleted


def cleanup_temp_dir(dir_path: str) -> None:
    """
    Clean up a temporary directory and all its contents.
    
    Args:
        dir_path: Path to the temporary directory
    """
    import shutil
    try:
        shutil.rmtree(dir_path)
    except OSError:
        pass  # Directory may not exist or already be deleted


def get_environment_variable(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Get an environment variable with optional default.
    
    Args:
        name: Environment variable name
        default: Default value if not set
        
    Returns:
        Environment variable value or default
    """
    return os.getenv(name, default)


def set_environment_variable(name: str, value: str) -> None:
    """
    Set an environment variable.
    
    Args:
        name: Environment variable name
        value: Environment variable value
    """
    os.environ[name] = value


def get_user_home() -> str:
    """
    Get the user's home directory.
    
    Returns:
        Path to user's home directory
    """
    return os.path.expanduser("~")


def get_current_working_directory() -> str:
    """
    Get the current working directory.
    
    Returns:
        Current working directory path
    """
    return os.getcwd()


def change_directory(path: str) -> None:
    """
    Change the current working directory.
    
    Args:
        path: Directory path to change to
    """
    os.chdir(path)


def file_exists(path: str) -> bool:
    """
    Check if a file exists.
    
    Args:
        path: File path to check
        
    Returns:
        True if file exists, False otherwise
    """
    return os.path.isfile(path)


def directory_exists(path: str) -> bool:
    """
    Check if a directory exists.
    
    Args:
        path: Directory path to check
        
    Returns:
        True if directory exists, False otherwise
    """
    return os.path.isdir(path)


def path_exists(path: str) -> bool:
    """
    Check if a path exists (file or directory).
    
    Args:
        path: Path to check
        
    Returns:
        True if path exists, False otherwise
    """
    return os.path.exists(path)


def make_directory(path: str, parents: bool = True) -> None:
    """
    Create a directory.
    
    Args:
        path: Directory path to create
        parents: Whether to create parent directories
    """
    os.makedirs(path, exist_ok=parents)


def remove_file(path: str) -> None:
    """
    Remove a file.
    
    Args:
        path: File path to remove
    """
    os.remove(path)


def remove_directory(path: str) -> None:
    """
    Remove a directory and all its contents.
    
    Args:
        path: Directory path to remove
    """
    import shutil
    shutil.rmtree(path)


def copy_file(src: str, dst: str) -> None:
    """
    Copy a file.
    
    Args:
        src: Source file path
        dst: Destination file path
    """
    import shutil
    shutil.copy2(src, dst)


def move_file(src: str, dst: str) -> None:
    """
    Move a file.
    
    Args:
        src: Source file path
        dst: Destination file path
    """
    import shutil
    shutil.move(src, dst)


def read_file_content(path: str, encoding: str = "utf-8") -> str:
    """
    Read file content.
    
    Args:
        path: File path to read
        encoding: File encoding
        
    Returns:
        File content as string
    """
    with open(path, 'r', encoding=encoding) as f:
        return f.read()


def write_file_content(path: str, content: str, encoding: str = "utf-8") -> None:
    """
    Write content to a file.
    
    Args:
        path: File path to write
        content: Content to write
        encoding: File encoding
    """
    with open(path, 'w', encoding=encoding) as f:
        f.write(content)


def append_file_content(path: str, content: str, encoding: str = "utf-8") -> None:
    """
    Append content to a file.
    
    Args:
        path: File path to append to
        content: Content to append
        encoding: File encoding
    """
    with open(path, 'a', encoding=encoding) as f:
        f.write(content)


def get_file_size(path: str) -> int:
    """
    Get file size in bytes.
    
    Args:
        path: File path
        
    Returns:
        File size in bytes
    """
    return os.path.getsize(path)


def get_file_permissions(path: str) -> int:
    """
    Get file permissions.
    
    Args:
        path: File path
        
    Returns:
        File permissions as integer
    """
    return os.stat(path).st_mode & 0o777


def set_file_permissions(path: str, mode: int) -> None:
    """
    Set file permissions.
    
    Args:
        path: File path
        mode: Permission mode (e.g., 0o755)
    """
    os.chmod(path, mode)


def execute_with_timeout(cmd: Union[str, List[str]], timeout: int, cwd: Optional[str] = None) -> Tuple[bool, subprocess.CompletedProcess]:
    """
    Execute a command with a timeout.
    
    Args:
        cmd: Command to execute
        timeout: Timeout in seconds
        cwd: Working directory
        
    Returns:
        Tuple of (success, CompletedProcess)
    """
    try:
        result = run_command(cmd, cwd=cwd, check=False, capture=True, timeout=timeout)
        return result.returncode == 0, result
    except subprocess.TimeoutExpired as e:
        return False, e
    except Exception as e:
        return False, e