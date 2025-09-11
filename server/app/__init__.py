import sys
import os

# Add project root to sys.path so Python can find the databases package
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from flask import Flask
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
        r"/api/*": {"origins": allowed_origins},
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
    # from .routes import metadata, watched, allostasis
    # app.register_blueprint(metadata.bp)
    app.register_blueprint(classifier.bp)
    app.register_blueprint(settings.bp)
    # app.register_blueprint(watched.bp)
    # app.register_blueprint(allostasis.bp)
    app.register_blueprint(stats.bp)

    # Start background autorun (if enabled via env)
    start_background(app)

    return app

