"""Vercel serverless entry: exposes the FastAPI ASGI app."""

import os
import sys

_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _root not in sys.path:
    sys.path.insert(0, _root)

from app.main import app  # noqa: E402

__all__ = ["app"]
