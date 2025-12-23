"""
Flask Application Factory

Creates and configures the Flask web application.
"""

import logging
import threading

from flask import Flask
from flask_cors import CORS

logger = logging.getLogger(__name__)

# Global references to core managers (set by main.py)
_audio_manager = None
_loopback_manager = None
_session_manager = None
_manager_lock = threading.Lock()


def set_managers(audio_manager, loopback_manager, session_manager):
    """
    Set global manager instances for web interface access.

    Args:
        audio_manager: AudioManager instance
        loopback_manager: LoopbackManager instance
        session_manager: SessionManager instance
    """
    global _audio_manager, _loopback_manager, _session_manager
    with _manager_lock:
        _audio_manager = audio_manager
        _loopback_manager = loopback_manager
        _session_manager = session_manager
    logger.info("Web interface managers configured")


def get_managers():
    """
    Get global manager instances.

    Returns:
        tuple: (audio_manager, loopback_manager, session_manager)
    """
    with _manager_lock:
        return (_audio_manager, _loopback_manager, _session_manager)


def create_app(config=None):
    """
    Create and configure Flask application.

    Args:
        config: Optional configuration dictionary

    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)

    # Basic Flask configuration
    app.config["SECRET_KEY"] = "midi-deck-secret-key-change-in-production"
    app.config["JSON_SORT_KEYS"] = False

    # Apply any custom configuration
    if config:
        app.config.update(config)

    # Enable CORS for local development
    CORS(app, resources={r"/api/*": {"origins": "*"}})

    # Register blueprints
    from .routes import api_bp, web_bp

    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(web_bp)

    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {error}")
        return {"error": "Internal server error"}, 500

    logger.info("Flask application created successfully")
    return app


def run_web_server(app, host=None, port=None):
    """
    Run Flask development server.

    Args:
        app: Flask application instance
        host: Host to bind to (default: 127.0.0.1)
        port: Port to bind to (default: 5000)
    """
    # Get configuration from database
    from app.database.db import get_config_value

    host = host or get_config_value("web_host", "127.0.0.1")
    port = port or int(get_config_value("web_port", "5000"))

    logger.info(f"Starting web server on {host}:{port}")

    # Run with threading enabled, debug disabled for production
    app.run(host=host, port=port, debug=False, threaded=True)
