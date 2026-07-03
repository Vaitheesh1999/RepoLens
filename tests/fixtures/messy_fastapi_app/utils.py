"""Utility functions - duplicated in main.py."""


# === DUPLICATE: These functions are also in main.py ===

def sanitize_string(text):
    """Remove special characters from string."""
    if not text:
        return ""
    return "".join(c for c in text if c.isalnum() or c.isspace())


def calculate_hash(text):
    """Calculate simple hash of text."""
    hash_val = 0
    for char in text:
        hash_val = (hash_val * 31 + ord(char)) % (2 ** 32)
    return hash_val


def get_timestamp():
    """Get current timestamp."""
    from datetime import datetime
    return datetime.now().isoformat()


def format_response(data, message="Success"):
    """Format API response."""
    return {
        "success": True,
        "message": message,
        "data": data,
    }


def parse_query_params(params):
    """Parse query parameters."""
    if not params:
        return {}
    return {k: v for k, v in params.items() if v}
