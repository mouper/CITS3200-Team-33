"""Security helpers for local-only service.

Add token-check middleware later to protect /api/* routes via the
X-LOCAL-TOKEN header.
"""

from typing import Any


def require_local_token(app: Any) -> None:
    """Register request guard for /api/* endpoints.

    Implementation is intentionally left empty in the skeleton.
    """
    # TODO: implement header check for X-LOCAL-TOKEN
    return None

