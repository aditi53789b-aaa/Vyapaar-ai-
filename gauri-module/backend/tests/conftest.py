"""Lets unit tests run where httpx isn't installed (tests use fake ASR clients)."""
import sys
import types

try:
    import httpx  # noqa: F401
except ModuleNotFoundError:
    sys.modules["httpx"] = types.SimpleNamespace(AsyncClient=object)
