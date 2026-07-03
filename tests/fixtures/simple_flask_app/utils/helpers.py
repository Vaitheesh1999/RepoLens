"""Helper utility functions."""


def get_user_summary(user):
    """Get user summary for API responses."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
    }


def format_response(data, status="success"):
    """Format API response."""
    return {
        "status": status,
        "data": data,
    }


def extract_user_email(user):
    """Extract email from user object."""
    return user.email if hasattr(user, "email") else None
