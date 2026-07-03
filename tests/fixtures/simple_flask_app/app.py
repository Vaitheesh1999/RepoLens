"""Flask application entry point."""

from flask import Flask
from routes.auth import auth_bp
from routes.users import users_bp


def create_app():
    """Create and configure Flask application."""
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key"
    app.config["DEBUG"] = True

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(users_bp)

    return app


def setup_routes(app):
    """Setup application routes."""
    @app.route("/")
    def index():
        """Root endpoint."""
        return {"message": "Welcome to Flask API"}

    @app.route("/health")
    def health():
        """Health check endpoint."""
        return {"status": "ok"}

    return app


def setup_error_handlers(app):
    """Setup error handlers."""
    @app.errorhandler(404)
    def not_found(error):
        """Handle 404 errors."""
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 errors."""
        return {"error": "Internal server error"}, 500

    return app


def init_app():
    """Initialize application with all setup."""
    app = create_app()
    app = setup_routes(app)
    app = setup_error_handlers(app)
    return app


if __name__ == "__main__":
    app = init_app()
    app.run(debug=True, host="0.0.0.0", port=5000)
