"""Tests for configuration loading."""

from __future__ import annotations

from pathlib import Path

from repolens.config import load_config


def test_load_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "repolens.toml"
    config_path.write_text(
        """
[thresholds]
max_file_lines = 420
max_function_count = 12

[llm]
provider = "openai"
model = "gpt-4o"
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config.max_file_lines == 420
    assert config.max_function_count == 12
    assert config.llm_provider == "openai"
    assert config.llm_model == "gpt-4o"
