"""Vercel entrypoint — FastAPI ASGI app (zero-config / rewrites)."""

from app.main import app

__all__ = ["app"]
