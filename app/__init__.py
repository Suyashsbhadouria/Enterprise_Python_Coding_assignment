"""Application factory for the cricket analytics dashboard.

Usage:
    from app import create_app
    app = create_app()
"""
import os
from flask import Flask, render_template, request, session, g, redirect, url_for, jsonify
from dotenv import load_dotenv

from config.settings import get_settings
from app.extensions import db, oauth
from core.logging_config import configure_logging

# Import blueprints
from app.api.overview import bp as overview_bp
from app.api.matches import bp as matches_bp
from app.api.batters import bp as batters_bp
from app.api.teams import bp as teams_bp
from app.api.chat import bp as chat_bp
from app.api.logs import bp as logs_bp


def create_app(config_name: str = None) -> Flask:
    """Create and configure the Flask application.
    
    Args:
        config_name: Configuration environment (dev, prod, test)
        
    Returns:
        Configured Flask application instance
    """
    # Load environment variables
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    load_dotenv(os.path.join(base_dir, ".env"))
    
    # Get settings
    settings = get_settings()
    
    # Create Flask app
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, "templates"),
        static_folder=os.path.join(base_dir, "static")
    )
    
    # Configure app
    app.secret_key = settings.flask_secret_key
    app.config["SQLALCHEMY_DATABASE_URI"] = settings.sqlalchemy_database_uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SETTINGS"] = settings
    
    # Initialize extensions
    db.init_app(app)
    oauth.init_app(app)
    
    # Register OAuth providers
    oauth.register(
        name="google",
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        client_kwargs={"scope": "openid email profile"}
    )
    
    # Configure logging
    logger = configure_logging(__name__)
    
    # Register existing auth blueprint
    from Auth.auth import auth_bp
    from Auth.models import User
    app.register_blueprint(auth_bp)
    
    # Register API blueprints
    app.register_blueprint(overview_bp)
    app.register_blueprint(matches_bp)
    app.register_blueprint(batters_bp)
    app.register_blueprint(teams_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(logs_bp)
    
    # Template context processor
    @app.context_processor
    def inject_globals():
        return {"APP_NAME": settings.app_name}
    
    # Global authentication middleware
    @app.before_request
    def global_auth_lockdown():
        """Ensure all routes are protected unless explicitly exempted."""
        allowed_endpoints = [
            "auth.login", "auth.auth_callback", 
            "public_login_page", "static"
        ]
        
        # Allow health check without auth
        if request.path == "/health":
            return None
            
        if request.endpoint not in allowed_endpoints:
            if "user_id" not in session:
                # For API routes, return 401
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Authentication required."}), 401
                return redirect(url_for("public_login_page"))
        
        # Load user into g for templates
        if "user_id" in session:
            g.user = db.session.get(User, session["user_id"])
        else:
            g.user = None
    
    # Request logging
    @app.before_request
    def log_request_start():
        import time
        g.request_start = time.perf_counter()
        logger.info("Request started %s %s", request.method, request.path)
    
    @app.after_request
    def log_request_end(response):
        import time
        start_time = getattr(g, "request_start", None)
        if start_time is not None:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Request completed %s %s -> %s in %.1fms",
                request.method, request.path, response.status_code, elapsed_ms
            )
        return response
    
    # Error handlers
    @app.errorhandler(404)
    def handle_not_found(error):
        logger.warning("Not found: %s %s", request.method, request.path)
        return render_template(
            "info.html",
            title="Not Found",
            subtitle="The requested page does not exist.",
            message="Check the URL and try again.",
            active_page=""
        ), 404
    
    @app.errorhandler(500)
    def handle_server_error(error):
        logger.exception("Unhandled error on %s %s", request.method, request.path)
        return render_template(
            "info.html",
            title="Server Error",
            subtitle="An unexpected error occurred.",
            message="Please try again or check the application logs.",
            active_page=""
        ), 500
    
    # Template filter
    @app.template_filter("team_abbr")
    def team_abbr(name):
        """Return short 3-letter abbreviation for a team label."""
        if not name:
            return "---"
        words = [w for w in name.split() if w]
        if len(words) == 1:
            return words[0][:3].upper()
        return "".join(w[0].upper() for w in words)[:3]
    
    # Page routes (non-API)
    @app.route("/login-page")
    def public_login_page():
        if "user_id" in session:
            return redirect(url_for("overview_page"))
        return render_template("login.html")
    
    @app.route("/")
    def overview_page():
        from app.services.transform_service import TransformService
        data = TransformService.get_overview()
        return render_template("overview.html", data=data, active_page="overview")
    
    @app.route("/matches")
    def matches_page():
        from app.services.transform_service import TransformService
        city_filter = request.args.get("city", "All Cities")
        team_filter = request.args.get("team", "All Teams")
        data = TransformService.get_matches(city_filter, team_filter)
        return render_template(
            "matches.html", 
            data=data, 
            active_page="matches",
            selected_city=city_filter, 
            selected_team=team_filter
        )
    
    @app.route("/batters")
    def batters_page():
        from app.services.transform_service import TransformService
        data = TransformService.get_batters()
        return render_template("batters.html", data=data, active_page="batters")
    
    @app.route("/teams")
    def teams_page():
        from app.services.transform_service import TransformService
        data = TransformService.get_teams()
        return render_template("teams.html", data=data, active_page="teams")
    
    @app.route("/live")
    def live_match_center():
        return matches_page()
    
    @app.route("/settings")
    def settings_page():
        from Auth.auth import admin_required
        return render_template(
            "info.html",
            title="Settings",
            subtitle="Configure your analytics workspace preferences.",
            message="Settings are available for presentation mode, default filters, and export behavior.",
            active_page="settings",
        )
    
    @app.route("/support")
    def support_page():
        from Auth.auth import admin_required
        return render_template(
            "info.html",
            title="Support",
            subtitle="Need help with this analytics suite?",
            message="Use the API endpoints or Appwrite collections for debugging and integrations.",
            active_page="support",
        )
    
    @app.route("/health")
    def health_check():
        """Health check endpoint for monitoring."""
        return jsonify({
            "status": "healthy",
            "service": settings.app_name
        })
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    logger.info("Application created successfully")
    return app
