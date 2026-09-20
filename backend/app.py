"""
Flask application entry point.

Run locally with:
    python app.py

Or with the Flask CLI:
    flask --app app run --debug
"""

import os

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from extensions import limiter
from routes.tts_routes import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)

    # --- CORS -------------------------------------------------------
    # Only allow the configured frontend origin(s) to call this API —
    # never use a wildcard "*" for an API that returns generated files.
    CORS(app, resources={r"/api/*": {"origins": Config.FRONTEND_ORIGINS},
                          r"/audio/*": {"origins": Config.FRONTEND_ORIGINS}})

    # --- Rate limiting ------------------------------------------------
    limiter.init_app(app)

    # --- Routes ---------------------------------------------------------
    app.register_blueprint(api_bp)

    @app.get("/audio/<path:filename>")
    def get_audio(filename):
        """Serve a generated audio file by name."""
        # send_from_directory safely rejects path traversal (e.g. "../../etc").
        return send_from_directory(
            Config.GENERATED_AUDIO_DIR, filename, mimetype="audio/mpeg"
        )

    @app.get("/")
    def index():
        return jsonify(
            {
                "service": "text-to-speech-backend",
                "status": "running",
                "endpoints": ["/api/health", "/api/voices", "/api/tts (POST)", "/audio/<filename>"],
            }
        )

    # --- Error handlers -------------------------------------------------
    @app.errorhandler(404)
    def not_found(_e):
        return jsonify({"success": False, "error": "Resource not found."}), 404

    @app.errorhandler(405)
    def method_not_allowed(_e):
        return jsonify({"success": False, "error": "Method not allowed."}), 405

    @app.errorhandler(429)
    def rate_limited(_e):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Too many requests. Please wait a moment and try again.",
                }
            ),
            429,
        )

    @app.errorhandler(500)
    def internal_error(_e):
        return jsonify({"success": False, "error": "Internal server error."}), 500

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=Config.PORT, debug=Config.DEBUG)
