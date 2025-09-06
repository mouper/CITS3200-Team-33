from flask import Flask
from flask_cors import CORS

from .config import load_config


def create_app() -> Flask:
    """Application factory for the local Flask service.

    Routes are not registered yet; implement blueprints in app/routes and
    register them here when ready.
    """

    app = Flask(__name__)

    # Load configuration from environment / .env
    app.config.update(load_config())

    # CORS: allow configured origins for /api/* (relaxed during dev)
    allowed_origins = app.config.get("ALLOWED_ORIGINS", ["*"])
    CORS(app, resources={r"/api/*": {"origins": allowed_origins}})

    # Security middleware and blueprint registration will be added later
    # from .security import require_local_token
    # require_local_token(app)

    # from .routes import metadata, classifier, watched, allostasis, stats
    # app.register_blueprint(metadata.bp)
    # app.register_blueprint(classifier.bp)
    # app.register_blueprint(watched.bp)
    # app.register_blueprint(allostasis.bp)
    # app.register_blueprint(stats.bp)

    return app

