"""
Tests for shell_utils module
"""

import pytest
import os
import tempfile
import subprocess
from unittest.mock import patch, MagicMock
from github_events_monitor.utils.shell_utils import (
    run_command, run_command_safe, which, is_command_available,
    create_temp_file, create_temp_dir, cleanup_temp_file, cleanup_temp_dir,
    get_environment_variable, set_environment_variable, get_user_home,
    get_current_working_directory, change_directory, file_exists,
    directory_exists, path_exists, make_directory, remove_file,
    remove_directory, copy_file, move_file, read_file_content,
    write_file_content, append_file_content, get_file_size,
    get_file_permissions, set_file_permissions, execute_with_timeout
)


class TestShellUtils:
    """Test cases for shell utilities."""
    
    @patch('subprocess.run')
    def test_run_command_success(self, mock_run):
        """Test successful command execution."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = run_command("echo test", capture=True)
        
        mock_run.assert_called_once()
        assert result == mock_result
    
    @patch('subprocess.run')
    def test_run_command_failure(self, mock_run):
        """Test command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "echo")
        
        with pytest.raises(subprocess.CalledProcessError):
            run_command("echo test")
    
    @patch('subprocess.run')
    def test_run_command_safe_success(self, mock_run):
        """Test safe command execution success."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        success, result = run_command_safe("echo test")
        
        assert success is True
        assert result == mock_result
    
    @patch('subprocess.run')
    def test_run_command_safe_failure(self, mock_run):
        """Test safe command execution failure."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "echo")
        
        success, result = run_command_safe("echo test")
        
        assert success is False
        assert isinstance(result, subprocess.CalledProcessError)
    
    @patch('subprocess.run')
    def test_run_command_timeout(self, mock_run):
        """Test command execution with timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("echo", 5)
        
        success, result = run_command_safe("echo test", timeout=5)
        
        assert success is False
        assert isinstance(result, subprocess.TimeoutExpired)
    
    @patch('shutil.which')
    def test_which_success(self, mock_which):
        """Test finding executable."""
        mock_which.return_value = "/usr/bin/git"
        
        result = which("git")
        
        assert result == "/usr/bin/git"
        mock_which.assert_called_once_with("git")
    
    @patch('shutil.which')
    def test_which_not_found(self, mock_which):
        """Test finding non-existent executable."""
        mock_which.return_value = None
        
        result = which("nonexistent")
        
        assert result is None
    
    @patch('github_events_monitor.utils.shell_utils.which')
    def test_is_command_available_true(self, mock_which):
        """Test command availability when available."""
        mock_which.return_value = "/usr/bin/git"
        
        result = is_command_available("git")
        
        assert result is True
    
    @patch('github_events_monitor.utils.shell_utils.which')
    def test_is_command_available_false(self, mock_which):
        """Test command availability when not available."""
        mock_which.return_value = None
        
        result = is_command_available("nonexistent")
        
        assert result is False
    
    def test_create_temp_file(self):
        """Test temporary file creation."""
        content = "test content"
        file_path = create_temp_file(suffix=".txt", content=content)
        
        try:
            assert os.path.exists(file_path)
            assert file_path.endswith(".txt")
            with open(file_path, 'r') as f:
                assert f.read() == content
        finally:
            cleanup_temp_file(file_path)
    
    def test_create_temp_dir(self):
        """Test temporary directory creation."""
        dir_path = create_temp_dir(suffix="_test", prefix="temp")
        
        try:
            assert os.path.exists(dir_path)
            assert os.path.isdir(dir_path)
        finally:
            cleanup_temp_dir(dir_path)
    
    def test_cleanup_temp_file(self):
        """Test temporary file cleanup."""
        file_path = create_temp_file()
        
        # File should exist
        assert os.path.exists(file_path)
        
        # Cleanup
        cleanup_temp_file(file_path)
        
        # File should not exist
        assert not os.path.exists(file_path)
    
    def test_cleanup_temp_dir(self):
        """Test temporary directory cleanup."""
        dir_path = create_temp_dir()
        
        # Directory should exist
        assert os.path.exists(dir_path)
        
        # Cleanup
        cleanup_temp_dir(dir_path)
        
        # Directory should not exist
        assert not os.path.exists(dir_path)
    
    @patch.dict(os.environ, {'TEST_VAR': 'test_value'})
    def test_get_environment_variable_exists(self):
        """Test getting existing environment variable."""
        result = get_environment_variable('TEST_VAR')
        
        assert result == 'test_value'
    
    def test_get_environment_variable_not_exists(self):
        """Test getting non-existent environment variable."""
        result = get_environment_variable('NONEXISTENT_VAR')
        
        assert result is None
    
    def test_get_environment_variable_with_default(self):
        """Test getting environment variable with default."""
        result = get_environment_variable('NONEXISTENT_VAR', 'default_value')
        
        assert result == 'default_value'
    
    def test_set_environment_variable(self):
        """Test setting environment variable."""
        set_environment_variable('TEST_SET_VAR', 'set_value')
        
        assert os.environ['TEST_SET_VAR'] == 'set_value'
    
    def test_get_user_home(self):
        """Test getting user home directory."""
        result = get_user_home()
        
        assert os.path.isdir(result)
        assert result == os.path.expanduser("~")
    
    def test_get_current_working_directory(self):
        """Test getting current working directory."""
        result = get_current_working_directory()
        
        assert os.path.isdir(result)
        assert result == os.getcwd()
    
    def test_change_directory(self):
        """Test changing directory."""
        original_cwd = os.getcwd()
        temp_dir = create_temp_dir()
        
        try:
            change_directory(temp_dir)
            assert os.getcwd() == temp_dir
        finally:
            change_directory(original_cwd)
            cleanup_temp_dir(temp_dir)
    
    def test_file_exists_true(self):
        """Test file existence when file exists."""
        file_path = create_temp_file()
        
        try:
            result = file_exists(file_path)
            assert result is True
        finally:
            cleanup_temp_file(file_path)
    
    def test_file_exists_false(self):
        """Test file existence when file doesn't exist."""
        result = file_exists("nonexistent_file.txt")
        
        assert result is False
    
    def test_directory_exists_true(self):
        """Test directory existence when directory exists."""
        dir_path = create_temp_dir()
        
        try:
            result = directory_exists(dir_path)
            assert result is True
        finally:
            cleanup_temp_dir(dir_path)
    
    def test_directory_exists_false(self):
        """Test directory existence when directory doesn't exist."""
        result = directory_exists("nonexistent_dir")
        
        assert result is False
    
    def test_path_exists_true(self):
        """Test path existence when path exists."""
        file_path = create_temp_file()
        
        try:
            result = path_exists(file_path)
            assert result is True
        finally:
            cleanup_temp_file(file_path)
    
    def test_path_exists_false(self):
        """Test path existence when path doesn't exist."""
        result = path_exists("nonexistent_path")
        
        assert result is False
    
    def test_make_directory(self):
        """Test directory creation."""
        dir_path = os.path.join(tempfile.gettempdir(), "test_dir")
        
        try:
            make_directory(dir_path)
            assert os.path.isdir(dir_path)
        finally:
            if os.path.exists(dir_path):
                os.rmdir(dir_path)
    
    def test_remove_file(self):
        """Test file removal."""
        file_path = create_temp_file()
        
        # File should exist
        assert os.path.exists(file_path)
        
        # Remove file
        remove_file(file_path)
        
        # File should not exist
        assert not os.path.exists(file_path)
    
    def test_remove_directory(self):
        """Test directory removal."""
        dir_path = create_temp_dir()
        
        # Directory should exist
        assert os.path.exists(dir_path)
        
        # Remove directory
        remove_directory(dir_path)
        
        # Directory should not exist
        assert not os.path.exists(dir_path)
    
    def test_copy_file(self):
        """Test file copying."""
        source_file = create_temp_file(content="test content")
        dest_file = os.path.join(tempfile.gettempdir(), "copied_file.txt")
        
        try:
            copy_file(source_file, dest_file)
            assert os.path.exists(dest_file)
            with open(dest_file, 'r') as f:
                assert f.read() == "test content"
        finally:
            cleanup_temp_file(source_file)
            if os.path.exists(dest_file):
                cleanup_temp_file(dest_file)
    
    def test_move_file(self):
        """Test file moving."""
        source_file = create_temp_file(content="test content")
        dest_file = os.path.join(tempfile.gettempdir(), "moved_file.txt")
        
        try:
            move_file(source_file, dest_file)
            assert not os.path.exists(source_file)
            assert os.path.exists(dest_file)
            with open(dest_file, 'r') as f:
                assert f.read() == "test content"
        finally:
            if os.path.exists(dest_file):
                cleanup_temp_file(dest_file)
    
    def test_read_file_content(self):
        """Test file content reading."""
        content = "test content with unicode: 测试"
        file_path = create_temp_file(content=content)
        
        try:
            result = read_file_content(file_path)
            assert result == content
        finally:
            cleanup_temp_file(file_path)
    
    def test_write_file_content(self):
        """Test file content writing."""
        content = "test content with unicode: 测试"
        file_path = os.path.join(tempfile.gettempdir(), "test_write.txt")
        
        try:
            write_file_content(file_path, content)
            assert os.path.exists(file_path)
            with open(file_path, 'r', encoding='utf-8') as f:
                assert f.read() == content
        finally:
            if os.path.exists(file_path):
                cleanup_temp_file(file_path)
    
    def test_append_file_content(self):
        """Test file content appending."""
        initial_content = "initial content"
        file_path = create_temp_file(content=initial_content)
        
        try:
            append_file_content(file_path, " appended content")
            with open(file_path, 'r') as f:
                assert f.read() == initial_content + " appended content"
        finally:
            cleanup_temp_file(file_path)
    
    def test_get_file_size(self):
        """Test getting file size."""
        content = "test content"
        file_path = create_temp_file(content=content)
        
        try:
            size = get_file_size(file_path)
            assert size == len(content.encode('utf-8'))
        finally:
            cleanup_temp_file(file_path)
    
    def test_get_file_permissions(self):
        """Test getting file permissions."""
        file_path = create_temp_file()
        
        try:
            permissions = get_file_permissions(file_path)
            assert isinstance(permissions, int)
            assert 0 <= permissions <= 0o777
        finally:
            cleanup_temp_file(file_path)
    
    def test_set_file_permissions(self):
        """Test setting file permissions."""
        file_path = create_temp_file()
        
        try:
            set_file_permissions(file_path, 0o644)
            permissions = get_file_permissions(file_path)
            assert permissions == 0o644
        finally:
            cleanup_temp_file(file_path)
    
    @patch('subprocess.run')
    def test_execute_with_timeout_success(self, mock_run):
        """Test command execution with timeout success."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        success, result = execute_with_timeout("echo test", 5)
        
        assert success is True
        assert result == mock_result
    
    @patch('subprocess.run')
    def test_execute_with_timeout_failure(self, mock_run):
        """Test command execution with timeout failure."""
        mock_run.side_effect = subprocess.TimeoutExpired("echo", 5)
        
        success, result = execute_with_timeout("echo test", 5)
        
        assert success is False
        assert isinstance(result, subprocess.TimeoutExpired)