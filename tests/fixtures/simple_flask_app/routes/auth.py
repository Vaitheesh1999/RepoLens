"""Authentication routes."""

from flask import Blueprint, request, jsonify
from models.user import User
from utils.validators import validate_email, validate_password

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["POST"])
def login():
    """Handle user login."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not validate_email(email):
        return {"error": "Invalid email"}, 400

    if not validate_password(password):
        return {"error": "Password too weak"}, 400

    user = User.authenticate(email, password)
    if user:
        return {"message": "Login successful", "user_id": user.id}, 200

    return {"error": "Invalid credentials"}, 401


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Handle user logout."""
    return {"message": "Logged out successfully"}, 200


@auth_bp.route("/register", methods=["POST"])
def register():
    """Handle user registration."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not validate_email(email):
        return {"error": "Invalid email"}, 400

    if not validate_password(password):
        return {"error": "Password too weak"}, 400

    existing = User.find_by_email(email)
    if existing:
        return {"error": "Email already registered"}, 409

    user = User.create(email, password)
    return {"message": "User created", "user_id": user.id}, 201
