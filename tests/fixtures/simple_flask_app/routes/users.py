"""User management routes."""

from flask import Blueprint, request, jsonify
from models.user import User
from utils.helpers import get_user_summary

users_bp = Blueprint("users", __name__, url_prefix="/users")


@users_bp.route("/", methods=["GET"])
def list_users():
    """List all users."""
    users = User.list_all()
    return {"users": [get_user_summary(u) for u in users]}, 200


@users_bp.route("/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user by ID."""
    user = User.find_by_id(user_id)
    if not user:
        return {"error": "User not found"}, 404

    return get_user_summary(user), 200


@users_bp.route("/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    """Update user details."""
    user = User.find_by_id(user_id)
    if not user:
        return {"error": "User not found"}, 404

    data = request.get_json()
    user.update(data)
    return get_user_summary(user), 200


@users_bp.route("/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    """Delete user by ID."""
    user = User.find_by_id(user_id)
    if not user:
        return {"error": "User not found"}, 404

    user.delete()
    return {"message": "User deleted"}, 204


@users_bp.route("/<int:user_id>/profile", methods=["GET"])
def get_user_profile(user_id):
    """Get detailed user profile."""
    user = User.find_by_id(user_id)
    if not user:
        return {"error": "User not found"}, 404

    return user.to_dict(), 200
