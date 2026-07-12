"""Tests for the logger utility."""

from repolens.utils.logger import (
    get_logger,
    log_node_start,
    log_node_end,
    log_llm_call,
    log_session_summary,
    reset_session,
    _session,
)

def test_get_logger_returns_child_logger():
    result = get_logger("ast")
    assert result.name == "repolens.ast"

def test_log_node_start_returns_float():
    result = log_node_start("test_node")
    assert isinstance(result, float)
    assert result > 0

def test_log_node_end_does_not_raise():
    start = log_node_start("test_node")
    log_node_end("test_node", start, files=5)  # should not raise

def test_log_llm_call_increments_session():
    reset_session()
    log_llm_call("groq", "llama-3.3-70b", "planning", 100, 200, 1.5)
    assert _session["total_calls"] == 1
    assert _session["total_tokens"] == 300
    assert _session["prompt_tokens"] == 100
    assert _session["completion_tokens"] == 200

def test_log_llm_call_accumulates_multiple():
    reset_session()
    log_llm_call("groq", "llama-3.3-70b", "planning", 100, 200, 1.5)
    log_llm_call("groq", "llama-3.3-70b", "semantic_classification", 50, 100, 0.8)
    assert _session["total_calls"] == 2
    assert _session["total_tokens"] == 450

def test_reset_session_clears_totals():
    log_llm_call("groq", "llama-3.3-70b", "planning", 100, 200, 1.5)
    reset_session()
    assert _session["total_calls"] == 0
    assert _session["total_tokens"] == 0

def test_log_session_summary_does_not_raise():
    reset_session()
    log_llm_call("groq", "llama-3.3-70b", "planning", 100, 200, 1.5)
    log_session_summary()  # should not raise
