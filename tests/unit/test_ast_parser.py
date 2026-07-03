"""Tests for AST parser module."""

import tempfile
from pathlib import Path

import pytest

from repolens.analysis.ast_parser import (
    ParseError,
    parse_file,
    _compute_branch_complexity,
    _extract_decorators,
    _extract_dunder_all,
    _extract_functions,
    _extract_imports,
)


class TestParseFile:
    """Tests for parse_file function."""

    def test_parses_simple_file(self) -> None:
        """Test parsing a simple Python file."""
        code = """
def hello():
    return "hello"

def goodbye():
    return "goodbye"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert facts.line_count > 0
            assert len(facts.functions) == 2
            assert facts.functions[0].name == "hello"
            assert facts.functions[1].name == "goodbye"
            assert facts.import_fan_out == 0
        finally:
            path.unlink()

    def test_extracts_decorators(self) -> None:
        """Test extracting decorators from functions."""
        code = """
@app.route("/")
def home():
    return "home"

@login_required
@app.post("/users")
def create_user():
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert len(facts.functions) == 2
            assert "app.route" in facts.functions[0].decorators
            assert "login_required" in facts.functions[1].decorators
            assert "app.post" in facts.functions[1].decorators
            assert facts.has_route_decorators
        finally:
            path.unlink()

    def test_detects_async(self) -> None:
        """Test detecting async functions."""
        code = """
async def fetch_data():
    await do_something()

def sync_function():
    return 42
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert len(facts.functions) == 2
            assert facts.functions[0].is_async
            assert not facts.functions[1].is_async
        finally:
            path.unlink()

    def test_extracts_imports(self) -> None:
        """Test extracting import information."""
        code = """
import os
import sys as system
from pathlib import Path
from flask import Flask, render_template
from . import utils
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert len(facts.imports) >= 4
            # Check for absolute imports
            os_imports = [i for i in facts.imports if i.module == "os"]
            assert len(os_imports) > 0
            assert not os_imports[0].is_relative

            # Check for relative imports
            relative_imports = [i for i in facts.imports if i.is_relative]
            assert len(relative_imports) > 0

            # Check for from imports with names
            flask_imports = [i for i in facts.imports if i.module == "flask"]
            assert len(flask_imports) > 0
            assert "Flask" in flask_imports[0].names
        finally:
            path.unlink()

    def test_branch_complexity(self) -> None:
        """Test branch complexity calculation."""
        code = """
def complex_function(x):
    if x > 0:
        if x > 10:
            return "big"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert len(facts.functions) == 1
            # Should count: if, if, elif, else (4 branches)
            assert facts.functions[0].branch_complexity >= 3
        finally:
            path.unlink()

    def test_dunder_all(self) -> None:
        """Test extracting __all__ definition."""
        code = """
__all__ = ["public_function", "PublicClass"]

def public_function():
    pass

def _private_function():
    pass

class PublicClass:
    pass
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert len(facts.dunder_all) == 2
            assert "public_function" in facts.dunder_all
            assert "PublicClass" in facts.dunder_all
            # Check that the function is marked as in __all__
            pub_func = next(f for f in facts.functions if f.name == "public_function")
            assert pub_func.in_dunder_all
            priv_func = next(f for f in facts.functions if f.name == "_private_function")
            assert not priv_func.in_dunder_all
        finally:
            path.unlink()

    def test_syntax_error(self) -> None:
        """Test that ParseError is raised for invalid Python."""
        code = """
def broken(
    this is invalid syntax !!!
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            with pytest.raises(ParseError) as exc_info:
                parse_file(path)

            assert str(path) in str(exc_info.value)
        finally:
            path.unlink()

    def test_parses_file_with_classes(self) -> None:
        """Test parsing file with classes."""
        code = """
class User:
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello {self.name}"

class Admin(User):
    def is_admin(self):
        return True
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert len(facts.classes) == 2
            user_class = next(c for c in facts.classes if c.name == "User")
            assert len(user_class.methods) == 2
            assert "greet" in user_class.methods

            admin_class = next(c for c in facts.classes if c.name == "Admin")
            assert "User" in admin_class.base_classes
        finally:
            path.unlink()

    def test_parse_simple_flask_app(self) -> None:
        """Test parsing all files in simple_flask_app fixture."""
        fixture_path = Path("tests/fixtures/simple_flask_app")

        files = list(fixture_path.rglob("*.py"))
        assert len(files) > 0, "Should find Python files in fixture"

        errors = []
        for file_path in files:
            try:
                facts = parse_file(file_path, fixture_path)
                assert facts.path == str(file_path)
                assert len(facts.relative_path) > 0
            except ParseError as e:
                errors.append(str(e))

        assert len(errors) == 0, f"Parse errors: {errors}"

    def test_detects_flask_framework(self) -> None:
        """Test that Flask framework is detected from imports."""
        code = """
from flask import Flask

app = Flask(__name__)
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert any("flask" in imp.module.lower() for imp in facts.imports)
        finally:
            path.unlink()

    def test_detects_db_operations(self) -> None:
        """Test that DB operations are detected."""
        code = """
from sqlalchemy import create_engine

def init_db():
    engine = create_engine("sqlite:///:memory:")
    return engine
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert facts.has_db_operations
        finally:
            path.unlink()

    def test_detects_business_logic(self) -> None:
        """Test that business logic is detected."""
        code = """
@app.route("/")
def route():
    return "hi"

def calculate_total(items):
    result = 0
    for item in items:
        result += item.price
    return result
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert facts.has_business_logic
        finally:
            path.unlink()

    def test_relative_path_calculation(self) -> None:
        """Test that relative paths are calculated correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Create a file
            file_path = tmpdir_path / "test.py"
            file_path.write_text("x = 1")

            facts = parse_file(file_path, tmpdir_path)

            assert facts.relative_path == "test.py"
            assert facts.path == str(file_path)
        

    def test_handles_nonexistent_file(self) -> None:
        """Test that ParseError is raised for nonexistent file."""
        with pytest.raises(ParseError):
            parse_file(Path("/nonexistent/file.py"))

    def test_empty_file(self) -> None:
        """Test parsing empty file."""
        code = ""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert facts.line_count == 1  # Single empty line
            assert len(facts.functions) == 0
            assert len(facts.classes) == 0
        finally:
            path.unlink()

    def test_file_with_docstring_only(self) -> None:
        """Test parsing file with only module docstring."""
        code = '''"""Module docstring."""
'''

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            f.flush()
            path = Path(f.name)

        try:
            facts = parse_file(path)

            assert facts.line_count > 0
            assert len(facts.functions) == 0
        finally:
            path.unlink()


class TestExtractDecorators:
    """Tests for decorator extraction."""

    def test_simple_decorator(self) -> None:
        """Test extracting simple decorator."""
        import ast

        code = """
@login_required
def protected():
    pass
"""
        tree = ast.parse(code)
        func = tree.body[0]

        decorators = _extract_decorators(func)
        assert decorators == ["login_required"]

    def test_chained_decorators(self) -> None:
        """Test extracting chained decorators."""
        import ast

        code = """
@app.route("/")
@login_required
def home():
    pass
"""
        tree = ast.parse(code)
        func = tree.body[0]

        decorators = _extract_decorators(func)
        assert "app.route" in decorators
        assert "login_required" in decorators

    def test_decorator_with_args(self) -> None:
        """Test extracting decorator with arguments."""
        import ast

        code = """
@app.route("/users", methods=["GET", "POST"])
def users():
    pass
"""
        tree = ast.parse(code)
        func = tree.body[0]

        decorators = _extract_decorators(func)
        assert decorators == ["app.route"]


class TestBranchComplexity:
    """Tests for branch complexity calculation."""

    def test_no_branches(self) -> None:
        """Test function with no branches."""
        import ast

        code = """
def simple():
    x = 1
    y = 2
    return x + y
"""
        tree = ast.parse(code)
        func = tree.body[0]

        complexity = _compute_branch_complexity(func)
        assert complexity == 0

    def test_single_if(self) -> None:
        """Test function with single if."""
        import ast

        code = """
def with_if(x):
    if x > 0:
        return "positive"
    return "not positive"
"""
        tree = ast.parse(code)
        func = tree.body[0]

        complexity = _compute_branch_complexity(func)
        assert complexity >= 1

    def test_multiple_branches(self) -> None:
        """Test function with multiple branch types."""
        import ast

        code = """
def complex_func(items):
    result = []
    for item in items:
        if item > 0:
            result.append(item)
    while len(result) > 10:
        result.pop()
    return result
"""
        tree = ast.parse(code)
        func = tree.body[0]

        complexity = _compute_branch_complexity(func)
        # Should count: for, if, while
        assert complexity >= 3

    def test_try_except(self) -> None:
        """Test function with try/except."""
        import ast

        code = """
def with_exception():
    try:
        risky()
    except ValueError:
        pass
    except TypeError:
        pass
"""
        tree = ast.parse(code)
        func = tree.body[0]

        complexity = _compute_branch_complexity(func)
        # Should count each except as a branch
        assert complexity >= 2


class TestExtractImports:
    """Tests for import extraction."""

    def test_simple_import(self) -> None:
        """Test extracting simple import."""
        import ast

        code = "import os"

        tree = ast.parse(code)
        imports = _extract_imports(tree)

        assert len(imports) == 1
        assert imports[0].module == "os"
        assert imports[0].names == []
        assert not imports[0].is_relative

    def test_from_import(self) -> None:
        """Test extracting from import."""
        import ast

        code = "from pathlib import Path, PurePath"

        tree = ast.parse(code)
        imports = _extract_imports(tree)

        assert len(imports) == 1
        assert imports[0].module == "pathlib"
        assert "Path" in imports[0].names
        assert "PurePath" in imports[0].names

    def test_relative_import(self) -> None:
        """Test extracting relative import."""
        import ast

        code = "from . import utils\nfrom .. import config"

        tree = ast.parse(code)
        imports = _extract_imports(tree)

        relative_imports = [i for i in imports if i.is_relative]
        assert len(relative_imports) >= 1


class TestExtractDunderAll:
    """Tests for __all__ extraction."""

    def test_extracts_dunder_all(self) -> None:
        """Test extracting __all__."""
        import ast

        code = """
__all__ = ["func1", "func2", "Class1"]
"""

        tree = ast.parse(code)
        dunder_all = _extract_dunder_all(tree)

        assert dunder_all == ["func1", "func2", "Class1"]

    def test_no_dunder_all(self) -> None:
        """Test when __all__ is not defined."""
        import ast

        code = """
def func1():
    pass
"""

        tree = ast.parse(code)
        dunder_all = _extract_dunder_all(tree)

        assert dunder_all == []

    def test_dunder_all_empty(self) -> None:
        """Test empty __all__."""
        import ast

        code = """
__all__ = []
"""

        tree = ast.parse(code)
        dunder_all = _extract_dunder_all(tree)

        assert dunder_all == []
