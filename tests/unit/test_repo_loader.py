import subprocess
from unittest.mock import patch

import pytest

from repolens.utils.repo_loader import (
    is_github_url,
    normalize_github_url,
    clone_repo,
    cleanup_repo,
)


def test_is_github_url_valid():
    assert is_github_url("https://github.com/user/repo") is True
    assert is_github_url("http://github.com/user/repo.git") is True
    assert is_github_url("https://www.github.com/user/repo") is True
    assert is_github_url("https://github.com/user/repo/tree/main") is True
    assert is_github_url("github.com/user/repo") is True
    assert is_github_url("www.github.com/user/repo") is True
    assert is_github_url("https://token@github.com/user/repo") is True
    assert is_github_url("https://user:token@github.com/user/repo") is True


def test_is_github_url_invalid():
    assert is_github_url("https://gitlab.com/user/repo") is False
    assert is_github_url("https://github.com/user") is False  # Missing repo
    assert is_github_url("ftp://github.com/user/repo") is False
    assert is_github_url("") is False
    assert is_github_url("/local/path/to/repo") is False


def test_normalize_github_url_valid():
    expected = "https://github.com/user/repo.git"
    assert normalize_github_url("https://github.com/user/repo") == expected
    assert normalize_github_url("https://github.com/user/repo.git") == expected
    assert normalize_github_url("https://github.com/user/repo/") == expected
    assert normalize_github_url("https://github.com/user/repo/tree/main") == expected
    assert normalize_github_url("github.com/user/repo") == expected
    assert normalize_github_url("www.github.com/user/repo") == expected
    
    auth_expected = "https://token@github.com/user/repo.git"
    assert normalize_github_url("https://token@github.com/user/repo") == auth_expected
    assert normalize_github_url("https://token@www.github.com/user/repo") == auth_expected
    
    full_auth_expected = "https://user:token@github.com/user/repo.git"
    assert normalize_github_url("https://user:token@github.com/user/repo") == full_auth_expected


def test_normalize_github_url_invalid():
    with pytest.raises(ValueError, match="Invalid GitHub URL"):
        normalize_github_url("https://gitlab.com/user/repo")


def test_cleanup_repo_success(tmp_path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    (repo_dir / "file.txt").write_text("hello")
    
    cleanup_repo(repo_dir)
    
    assert not repo_dir.exists()


def test_cleanup_repo_handles_errors(tmp_path):
    # Pass a path that doesn't exist
    not_exist = tmp_path / "does_not_exist"
    cleanup_repo(not_exist)  # Should not raise
    
    # Pass a file instead of a directory
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    cleanup_repo(file_path)  # Should not raise


@patch("repolens.utils.repo_loader.subprocess.run")
@patch("repolens.utils.repo_loader.shutil.which")
@patch("repolens.utils.repo_loader.tempfile.mkdtemp")
def test_clone_repo_success(mock_mkdtemp, mock_which, mock_run, tmp_path):
    mock_which.return_value = "/usr/bin/git"
    
    fake_temp_dir = tmp_path / "fake_repolens_123"
    fake_temp_dir.mkdir()
    mock_mkdtemp.return_value = str(fake_temp_dir)
    
    result = clone_repo("https://github.com/user/repo")
    
    assert result == fake_temp_dir
    mock_run.assert_called_once()
    args, kwargs = mock_run.call_args
    assert args[0] == ["git", "clone", "--depth=1", "https://github.com/user/repo.git", str(fake_temp_dir)]


@patch("repolens.utils.repo_loader.subprocess.run")
@patch("repolens.utils.repo_loader.shutil.which")
@patch("repolens.utils.repo_loader.tempfile.mkdtemp")
def test_clone_repo_git_not_installed(mock_mkdtemp, mock_which, mock_run, tmp_path):
    mock_which.return_value = None
    
    fake_temp_dir = tmp_path / "fake_repolens_123"
    fake_temp_dir.mkdir()
    mock_mkdtemp.return_value = str(fake_temp_dir)
    
    with pytest.raises(RuntimeError, match="Git is not installed"):
        clone_repo("https://github.com/user/repo")
        
    mock_run.assert_not_called()
    assert not fake_temp_dir.exists()  # Ensure cleanup was called


@patch("repolens.utils.repo_loader.subprocess.run")
@patch("repolens.utils.repo_loader.shutil.which")
@patch("repolens.utils.repo_loader.tempfile.mkdtemp")
def test_clone_repo_auth_failure(mock_mkdtemp, mock_which, mock_run, tmp_path):
    mock_which.return_value = "/usr/bin/git"
    
    fake_temp_dir = tmp_path / "fake_repolens_123"
    fake_temp_dir.mkdir()
    mock_mkdtemp.return_value = str(fake_temp_dir)
    
    # Simulate auth failure
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=128,
        cmd=["git", "clone"],
        stderr="fatal: Authentication failed for 'https://github.com/user/repo.git/'\n"
    )
    
    with pytest.raises(RuntimeError, match="Authentication failed for private repository"):
        clone_repo("https://github.com/user/repo")
        
    assert not fake_temp_dir.exists()  # Ensure cleanup was called


@patch("repolens.utils.repo_loader.subprocess.run")
@patch("repolens.utils.repo_loader.shutil.which")
@patch("repolens.utils.repo_loader.tempfile.mkdtemp")
def test_clone_repo_not_found(mock_mkdtemp, mock_which, mock_run, tmp_path):
    mock_which.return_value = "/usr/bin/git"
    
    fake_temp_dir = tmp_path / "fake_repolens_123"
    fake_temp_dir.mkdir()
    mock_mkdtemp.return_value = str(fake_temp_dir)
    
    # Simulate repo not found
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=128,
        cmd=["git", "clone"],
        stderr="remote: Repository not found.\n"
    )
    
    with pytest.raises(RuntimeError, match="Repository does not exist or is private"):
        clone_repo("https://github.com/user/repo")
        
    assert not fake_temp_dir.exists()


@patch("repolens.utils.repo_loader.subprocess.run")
@patch("repolens.utils.repo_loader.shutil.which")
@patch("repolens.utils.repo_loader.tempfile.mkdtemp")
def test_clone_repo_network_error(mock_mkdtemp, mock_which, mock_run, tmp_path):
    mock_which.return_value = "/usr/bin/git"
    
    fake_temp_dir = tmp_path / "fake_repolens_123"
    fake_temp_dir.mkdir()
    mock_mkdtemp.return_value = str(fake_temp_dir)
    
    # Simulate network error
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=128,
        cmd=["git", "clone"],
        stderr="fatal: could not resolve host: github.com\n"
    )
    
    with pytest.raises(RuntimeError, match="Network failure while cloning"):
        clone_repo("https://github.com/user/repo")
        
    assert not fake_temp_dir.exists()
