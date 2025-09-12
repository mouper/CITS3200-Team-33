import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def load_config() -> dict:
    """Load application configuration from environment variables.

    This function intentionally keeps a minimal surface; the service
    reads env directly where needed. The returned mapping is merged
    into Flask app.config in app/__init__.py.
    """

    allowed_origins = os.getenv("ALLOWED_ORIGINS", "*")
    origins = [o.strip() for o in allowed_origins.split(",") if o.strip()] if allowed_origins else ["*"]

    return {
        "ALLOWED_ORIGINS": origins,
    }

