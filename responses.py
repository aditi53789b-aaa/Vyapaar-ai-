
from typing import Any

from fastapi import HTTPException

# Internal marker key used to pass structured errors through HTTPException.
ERROR_MARKER = "app_error"


def ok(data: Any) -> dict:
    """Success envelope used by every endpoint."""
    return {"success": True, "data": data}


def fail(status_code: int, code: str, message: str, details: Any = None) -> HTTPException:
    """Raise a predictable-JSON error. The handler in main.py renders it as:
    {"success": false, "error": {"code": ..., "message": ..., "details": ...}}"""
    raise HTTPException(
        status_code=status_code,
        detail={ERROR_MARKER: [code, message, details]},
    )