"""
Logging configuration and tracking for RepoLens.
"""

import logging
from logging.handlers import RotatingFileHandler
import os
import time

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(os.getcwd(), "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure the base logger
_logger = logging.getLogger("repolens")
_logger.setLevel(logging.INFO)
# Avoid adding multiple handlers if this module is reloaded
if not _logger.handlers:
    formatter = logging.Formatter(
        fmt="[%(asctime)s] %(levelname)-7s [%(name)s]  %(message)s",
        datefmt="%H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    file_handler = RotatingFileHandler(
        os.path.join(LOGS_DIR, "repolens.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=3,
    )
    file_handler.setFormatter(formatter)

    _logger.addHandler(console_handler)
    _logger.addHandler(file_handler)


_session = {
    "total_calls": 0,
    "total_tokens": 0,
    "prompt_tokens": 0,
    "completion_tokens": 0,
    "total_duration": 0.0,
    "calls": []
}

def get_logger(component: str) -> logging.Logger:
    """Return a child logger for a named component e.g. get_logger('ast')"""
    return _logger.getChild(component)

def set_level(verbose: bool) -> None:
    """Set logger to DEBUG if verbose=True, INFO otherwise."""
    level = logging.DEBUG if verbose else logging.INFO
    _logger.setLevel(level)

def log_node_start(node_name: str, **kwargs) -> float:
    """
    Log that a node has started.
    Returns time.time() so the caller can compute duration.
    Example: start = log_node_start("analysis", files=23)
    Logs: [INFO] [node.analysis] started  files=23
    """
    start_time = time.time()
    logger = get_logger(f"node.{node_name}")
    msg = "started"
    if kwargs:
        msg += "  " + "  ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(msg)
    return start_time

def log_node_end(node_name: str, start_time: float, **kwargs) -> None:
    """
    Log that a node has completed.
    Computes duration from start_time.
    Example: log_node_end("analysis", start, issues=7, candidates=3)
    Logs: [INFO] [node.analysis] completed  duration=4.21s  issues=7  candidates=3
    """
    duration = time.time() - start_time
    logger = get_logger(f"node.{node_name}")
    msg = f"completed  duration={duration:.2f}s"
    if kwargs:
        msg += "  " + "  ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(msg)

def log_llm_call(
    provider: str,
    model: str,
    node: str,
    prompt_tokens: int,
    completion_tokens: int,
    duration: float,
    attempt: int = 1,
) -> None:
    """
    Log one LLM API call and accumulate into _session totals.
    Logs: [INFO] [llm] call_end  provider=groq  model=...  node=...
          prompt_tokens=842  completion_tokens=310  total_tokens=1152
          duration=2.11s  attempt=1
    """
    total_tokens = prompt_tokens + completion_tokens
    _session["total_calls"] += 1
    _session["total_tokens"] += total_tokens
    _session["prompt_tokens"] += prompt_tokens
    _session["completion_tokens"] += completion_tokens
    _session["total_duration"] += duration
    
    call_info = {
        "provider": provider,
        "model": model,
        "node": node,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "duration": duration,
        "attempt": attempt,
    }
    _session["calls"].append(call_info)

    logger = get_logger("llm")
    msg = (
        f"call_end  provider={provider}  model={model}  node={node}  "
        f"prompt_tokens={prompt_tokens}  completion_tokens={completion_tokens}  "
        f"total_tokens={total_tokens}  duration={duration:.2f}s  attempt={attempt}"
    )
    logger.info(msg)

def log_llm_warning(node: str, message: str, **kwargs) -> None:
    """Log a warning from an LLM node."""
    logger = get_logger("llm")
    msg = f"warning  node={node}  {message}"
    if kwargs:
        msg += "  " + "  ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.warning(msg)

def log_session_summary() -> None:
    """
    Log and print the full session summary.
    Called once after the graph finishes.
    Logs:
      [INFO] [session] summary
        total_calls=3
        total_tokens=4217
        prompt_tokens=2046
        completion_tokens=2171
        total_duration=7.88s
    """
    logger = get_logger("session")
    msg = (
        "summary\n"
        f"  total_calls={_session['total_calls']}\n"
        f"  total_tokens={_session['total_tokens']}\n"
        f"  prompt_tokens={_session['prompt_tokens']}\n"
        f"  completion_tokens={_session['completion_tokens']}\n"
        f"  total_duration={_session['total_duration']:.2f}s"
    )
    logger.info(msg)

def reset_session() -> None:
    """Reset _session to zero. Used in tests."""
    _session["total_calls"] = 0
    _session["total_tokens"] = 0
    _session["prompt_tokens"] = 0
    _session["completion_tokens"] = 0
    _session["total_duration"] = 0.0
    _session["calls"] = []
