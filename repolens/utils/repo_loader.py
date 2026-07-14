"""
Repository loader utility for RepoLens.

Provides utilities to fetch repositories from GitHub into temporary directories.
"""
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlparse


def is_github_url(path: str) -> bool:
    """
    Check if a given string is a valid GitHub URL.

    Args:
        path: The path or URL to check.

    Returns:
        True if the path is a valid GitHub URL, False otherwise.
    """
    try:
        if path.startswith(("github.com/", "www.github.com/")):
            path = "https://" + path
            
        parsed = urlparse(path)
        if parsed.scheme not in ("http", "https"):
            return False
        if parsed.hostname not in ("github.com", "www.github.com"):
            return False
        
        # Check if it has at least user and repo parts
        path_parts = [p for p in parsed.path.split("/") if p]
        if len(path_parts) < 2:
            return False
            
        return True
    except Exception:
        return False


def normalize_github_url(url: str) -> str:
    """
    Normalize a GitHub URL to the standard cloning format.
    
    Examples:
    - https://github.com/user/repo
    - https://github.com/user/repo.git
    - https://github.com/user/repo/tree/main

    All normalize to: https://github.com/user/repo.git
    
    Args:
        url: The GitHub URL to normalize.
        
    Returns:
        The normalized GitHub clone URL.
        
    Raises:
        ValueError: If the URL is not a valid GitHub URL.
    """
    if url.startswith(("github.com/", "www.github.com/")):
        url = "https://" + url
        
    if not is_github_url(url):
        raise ValueError(f"Invalid GitHub URL: {url}")
        
    parsed = urlparse(url)
    path_parts = [p for p in parsed.path.split("/") if p]
    
    user = path_parts[0]
    repo = path_parts[1]
    
    if repo.endswith(".git"):
        repo = repo[:-4]
        
    auth = ""
    if "@" in parsed.netloc:
        auth = parsed.netloc.split("@", 1)[0] + "@"
        
    return f"https://{auth}github.com/{user}/{repo}.git"


def clone_repo(url: str) -> Path:
    """
    Clone a GitHub repository into a temporary directory using shallow clone.
    
    Args:
        url: The GitHub URL to clone.
        
    Returns:
        The Path to the cloned repository directory.
        
    Raises:
        ValueError: If the URL is not a valid GitHub URL.
        RuntimeError: If the git clone command fails.
    """
    normalized_url = normalize_github_url(url)
    
    try:
        temp_dir = tempfile.mkdtemp(prefix="repolens_")
    except Exception as exc:
        raise RuntimeError(f"Failed to create temporary directory: {exc}") from exc
        
    if shutil.which("git") is None:
        cleanup_repo(Path(temp_dir))
        raise RuntimeError(
            "Git is not installed or not found in PATH. "
            "Please install Git to analyze GitHub repositories."
        )
    
    try:
        subprocess.run(
            ["git", "clone", "--depth=1", normalized_url, temp_dir],
            check=True,
            capture_output=True,
            text=True
        )
        return Path(temp_dir)
    except subprocess.CalledProcessError as exc:
        cleanup_repo(Path(temp_dir))
        stderr = exc.stderr.strip()
        lower_stderr = stderr.lower()
        
        if "authentication failed" in lower_stderr or "could not read username" in lower_stderr:
            raise RuntimeError(
                f"Authentication failed for private repository: {url}\n"
                "Please ensure you have access and your Git credentials are configured."
            ) from exc
        elif "not found" in lower_stderr:
            raise RuntimeError(f"Repository does not exist or is private: {url}") from exc
        elif "could not resolve host" in lower_stderr or "connection timed out" in lower_stderr or "network is unreachable" in lower_stderr:
            raise RuntimeError(
                f"Network failure while cloning repository: {url}\n"
                "Please check your internet connection."
            ) from exc
        else:
            raise RuntimeError(f"Failed to clone repository: {stderr}") from exc


def cleanup_repo(path: Path) -> None:
    """
    Clean up a cloned repository directory.
    
    Args:
        path: The Path to the directory to remove.
        
    Note:
        This function never raises an exception.
    """
    try:
        if path.exists() and path.is_dir():
            # Handle Windows permission issues with removing read-only git files
            def onerror(func, p, exc_info):
                import stat
                if not os.access(p, os.W_OK):
                    os.chmod(p, stat.S_IWUSR)
                    try:
                        func(p)
                    except Exception:
                        pass
                else:
                    pass
            shutil.rmtree(path, onerror=onerror)
    except Exception:
        pass
