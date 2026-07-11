"""Tests for repository scanner module."""

import tempfile
from pathlib import Path


from repolens.analysis.scanner import discover_python_files, detect_framework, detect_python_version
from repolens.models.config_models import AnalysisConfig


class TestDiscoverPythonFiles:
    """Tests for discover_python_files function."""

    def test_discovers_python_files(self) -> None:
        """Test discovering Python files in simple_flask_app fixture."""
        fixture_path = Path("tests/fixtures/simple_flask_app")
        config = AnalysisConfig()

        files = discover_python_files(fixture_path, config)

        assert len(files) > 0, "Should find at least one Python file"
        assert all(f.suffix == ".py" for f in files), "All files should be .py"
        assert all(f.is_absolute() for f in files), "All paths should be absolute"
        # Expected: __init__.py, app.py, routes/__init__.py, auth.py, users.py,
        #           models/__init__.py, user.py, utils/__init__.py, validators.py, helpers.py
        assert len(files) == 10, f"Expected 10 Python files, got {len(files)}"

    def test_excludes_pycache(self) -> None:
        """Test that __pycache__ directories are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create normal Python file
            (tmpdir_path / "main.py").write_text("print('hello')")

            # Create __pycache__ with .pyc file
            pycache_dir = tmpdir_path / "__pycache__"
            pycache_dir.mkdir()
            (pycache_dir / "main.cpython-311.pyc").write_text("compiled")

            config = AnalysisConfig()
            files = discover_python_files(tmpdir_path, config)

            # Should find only main.py, not the .pyc in __pycache__
            assert len(files) == 1
            assert files[0].name == "main.py"

    def test_excludes_venv(self) -> None:
        """Test that venv directories are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create normal Python file
            (tmpdir_path / "app.py").write_text("# app")

            # Create venv with Python files
            venv_dir = tmpdir_path / "venv"
            venv_dir.mkdir()
            (venv_dir / "lib.py").write_text("# lib")

            config = AnalysisConfig()
            files = discover_python_files(tmpdir_path, config)

            # Should find only app.py
            assert len(files) == 1
            assert files[0].name == "app.py"

    def test_excludes_dist(self) -> None:
        """Test that dist directories are excluded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create source file
            (tmpdir_path / "main.py").write_text("# main")

            # Create dist directory with Python files
            dist_dir = tmpdir_path / "dist"
            dist_dir.mkdir()
            (dist_dir / "package.py").write_text("# package")

            config = AnalysisConfig()
            files = discover_python_files(tmpdir_path, config)

            assert len(files) == 1
            assert files[0].name == "main.py"

    def test_returns_empty_list_when_no_files(self) -> None:
        """Test that empty list is returned when no Python files found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create only non-Python files
            (tmpdir_path / "readme.txt").write_text("readme")
            (tmpdir_path / "data.json").write_text("{}")

            config = AnalysisConfig()
            files = discover_python_files(tmpdir_path, config)

            assert files == []

    def test_returns_empty_for_nonexistent_path(self) -> None:
        """Test that empty list is returned for nonexistent path."""
        config = AnalysisConfig()
        files = discover_python_files(Path("/nonexistent/path"), config)

        assert files == []

    def test_returns_sorted_paths(self) -> None:
        """Test that returned paths are sorted alphabetically."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create files in random order
            names = ["zebra.py", "apple.py", "monkey.py"]
            for name in names:
                (tmpdir_path / name).write_text("# " + name)

            config = AnalysisConfig()
            files = discover_python_files(tmpdir_path, config)

            file_names = [f.name for f in files]
            assert file_names == ["apple.py", "monkey.py", "zebra.py"]


class TestDetectFramework:
    """Tests for detect_framework function."""

    def test_detects_flask(self) -> None:
        """Test that Flask is detected from simple_flask_app fixture."""
        fixture_path = Path("tests/fixtures/simple_flask_app")
        from repolens.analysis.scanner import discover_python_files
        from repolens.models.config_models import AnalysisConfig

        config = AnalysisConfig()
        files = discover_python_files(fixture_path, config)

        framework = detect_framework(files)
        assert framework == "flask"

    def test_detects_fastapi(self) -> None:
        """Test that FastAPI is detected from messy_fastapi_app fixture."""
        fixture_path = Path("tests/fixtures/messy_fastapi_app")
        from repolens.analysis.scanner import discover_python_files
        from repolens.models.config_models import AnalysisConfig

        config = AnalysisConfig()
        files = discover_python_files(fixture_path, config)

        framework = detect_framework(files)
        assert framework == "fastapi"

    def test_detects_unknown(self) -> None:
        """Test that 'unknown' is returned for repository with no framework imports."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create Python files without Flask or FastAPI imports
            (tmpdir_path / "utils.py").write_text("""
def add(a, b):
    return a + b

def multiply(a, b):
    return a * b
""")
            (tmpdir_path / "helpers.py").write_text("""
import json
import re

def parse_data(data):
    return json.loads(data)
""")

            files = list(tmpdir_path.glob("*.py"))
            framework = detect_framework(files)
            assert framework == "unknown"

    def test_detects_flask_import_variants(self) -> None:
        """Test various Flask import styles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Test "from flask import"
            (tmpdir_path / "test1.py").write_text("from flask import Flask")
            files = list(tmpdir_path.glob("*.py"))
            assert detect_framework(files) == "flask"

            # Clean up and test "import flask"
            (tmpdir_path / "test1.py").unlink()
            (tmpdir_path / "test2.py").write_text("import flask")
            files = list(tmpdir_path.glob("*.py"))
            assert detect_framework(files) == "flask"

    def test_detects_fastapi_import_variants(self) -> None:
        """Test various FastAPI import styles."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Test "from fastapi import"
            (tmpdir_path / "test1.py").write_text("from fastapi import FastAPI")
            files = list(tmpdir_path.glob("*.py"))
            assert detect_framework(files) == "fastapi"

            # Clean up and test "import fastapi"
            (tmpdir_path / "test1.py").unlink()
            (tmpdir_path / "test2.py").write_text("import fastapi")
            files = list(tmpdir_path.glob("*.py"))
            assert detect_framework(files) == "fastapi"

    def test_detects_flask_over_fastapi(self) -> None:
        """Test that Flask is detected when both frameworks are present (Flask checked first)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            (tmpdir_path / "app1.py").write_text("from flask import Flask")
            (tmpdir_path / "app2.py").write_text("from fastapi import FastAPI")

            files = list(tmpdir_path.glob("*.py"))
            framework = detect_framework(files)
            # Should detect flask since it's checked first
            assert framework == "flask"

    def test_handles_unreadable_files(self) -> None:
        """Test that unreadable files don't crash the function."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a readable file
            (tmpdir_path / "readable.py").write_text("from flask import Flask")

            files = [
                tmpdir_path / "readable.py",
                Path("/nonexistent/file.py"),  # This file doesn't exist
            ]

            # Should not crash and should find Flask from readable file
            framework = detect_framework(files)
            assert framework == "flask"

    def test_empty_file_list(self) -> None:
        """Test that empty file list returns 'unknown'."""
        framework = detect_framework([])
        assert framework == "unknown"


class TestDetectPythonVersion:
    """Tests for detect_python_version function."""

    def test_reads_python_version_file(self) -> None:
        """Test reading Python version from .python-version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create .python-version file
            (tmpdir_path / ".python-version").write_text("3.11.4")

            version = detect_python_version(tmpdir_path)
            assert version == "3.11.4"

    def test_reads_requires_python_from_pyproject(self) -> None:
        """Test reading Python version from pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create pyproject.toml with requires-python
            pyproject_content = """
[project]
name = "test-project"
requires-python = ">=3.11"
"""
            (tmpdir_path / "pyproject.toml").write_text(pyproject_content)

            version = detect_python_version(tmpdir_path)
            assert version == ">=3.11"

    def test_prefers_python_version_file(self) -> None:
        """Test that .python-version file is checked before pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create both files with different versions
            (tmpdir_path / ".python-version").write_text("3.12.0")

            pyproject_content = """
[project]
requires-python = ">=3.11"
"""
            (tmpdir_path / "pyproject.toml").write_text(pyproject_content)

            version = detect_python_version(tmpdir_path)
            # Should prefer .python-version
            assert version == "3.12.0"

    def test_returns_none_when_no_version_found(self) -> None:
        """Test that None is returned when neither file specifies version."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create empty pyproject.toml without requires-python
            pyproject_content = """
[project]
name = "test-project"
"""
            (tmpdir_path / "pyproject.toml").write_text(pyproject_content)

            version = detect_python_version(tmpdir_path)
            assert version is None

    def test_returns_none_for_nonexistent_path(self) -> None:
        """Test that None is returned for nonexistent path."""
        version = detect_python_version(Path("/nonexistent/path"))
        assert version is None

    def test_handles_empty_python_version_file(self) -> None:
        """Test handling of empty .python-version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create empty .python-version file
            (tmpdir_path / ".python-version").write_text("")

            # Should check pyproject.toml or return None
            version = detect_python_version(tmpdir_path)
            assert version is None

    def test_handles_malformed_pyproject(self) -> None:
        """Test handling of malformed pyproject.toml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create malformed TOML
            (tmpdir_path / "pyproject.toml").write_text("invalid [[ toml ]]")

            # Should not crash, return None
            version = detect_python_version(tmpdir_path)
            assert version is None

    def test_strips_whitespace_from_python_version_file(self) -> None:
        """Test that whitespace is stripped from .python-version file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create .python-version file with whitespace
            (tmpdir_path / ".python-version").write_text("  3.11.0  \n")

            version = detect_python_version(tmpdir_path)
            assert version == "3.11.0"
