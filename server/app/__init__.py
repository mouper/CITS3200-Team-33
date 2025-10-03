import sys
import os

# Add project root to sys.path so Python can find the databases package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from flask import Flask, request, jsonify
from flask_cors import CORS

from .config import load_config
from .background import start_background
from databases import main


def create_app() -> Flask:
    """Application factory for the local Flask service.

    Routes are not registered yet; implement blueprints in app/routes and
    register them here when ready.
    """

    app = Flask(__name__)

    # Load configuration from environment / .env
    app.config.update(load_config())

    # CORS: allow configured origins for /api/* and health/version (relaxed during dev)
    allowed_origins = app.config.get("ALLOWED_ORIGINS", ["*"])
    CORS(app, resources={
        r"/api/*": {
            "origins": ["*", "chrome-extension://*", "moz-extension://*"],
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "supports_credentials": False
        },
        r"/health": {"origins": allowed_origins},
        r"/version": {"origins": allowed_origins},
    })

    # Initialize databases automatically
    main.database.init_all()  # <- creates DBs and tables if missing

    # Start the cleanup/background scheduler
    main.start_scheduler(3600)

    # Security middleware and blueprint registration will be added later
    # from .security import require_local_token
    # require_local_token(app)

    from .routes import stats
    from .routes import classifier
    from .routes import settings
    from .routes import metadata
    from .routes import blocked_videos
    from .routes import filter
    from .routes import categorised
    from .routes import watched
    # from .routes import allostasis
    app.register_blueprint(metadata.bp)
    app.register_blueprint(classifier.bp)
    app.register_blueprint(settings.bp)
    app.register_blueprint(blocked_videos.bp)
    app.register_blueprint(filter.bp)
    app.register_blueprint(categorised.bp)
    app.register_blueprint(watched.bp)
    app.register_blueprint(stats.bp)

    # Start background autorun (if enabled via env)
    start_background(app)

    # Add manual CORS handler for Chrome extensions
    @app.after_request
    def after_request(response):
        origin = request.headers.get('Origin')
        print(f"DEBUG: Request origin: {origin}")
        print(f"DEBUG: Request method: {request.method}")
        print(f"DEBUG: Request path: {request.path}")
        
        # Always add CORS headers for API routes
        if request.path.startswith('/api/'):
            response.headers['Access-Control-Allow-Origin'] = origin or '*'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
            response.headers['Access-Control-Allow-Credentials'] = 'false'
            print(f"DEBUG: Added CORS headers for {request.path}")
        
        return response

    return app

