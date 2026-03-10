

"""Entrypoint helper for running the backend API.

UI is now implemented in React under `frontend/`.
"""

from app.backend.api import app

__all__ = ["app"]
