"""ASGI compatibility entry point. Run from the backend directory with: uvicorn main:app."""
from app.main import app

__all__ = ["app"]
