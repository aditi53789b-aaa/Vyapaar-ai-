"""Short-lived tokens for the live-transcription WebSocket.

Browsers cannot set headers on WebSockets, so the Next.js app issues a token
("<expiryUnix>.<hmacSHA256(expiry)>", see frontend/app/api/speech-token/route.ts) and the browser
passes it as ?token=. Both sides share SPEECH_WS_SECRET.
"""
from __future__ import annotations

import hashlib
import hmac
import time

MAX_TTL_SECONDS = 3600  # reject tokens claiming to live longer than this


def _mac(secret: str, payload: str) -> str:
    return hmac.new(secret.encode(), payload.encode(), hashlib.sha256).hexdigest()


def issue_token(secret: str, ttl: int = 120, now: float | None = None) -> str:
    exp = str(int((time.time() if now is None else now) + ttl))
    return f"{exp}.{_mac(secret, exp)}"


def verify_token(token: str | None, secret: str | None, now: float | None = None) -> bool:
    if not token or not secret:
        return False
    try:
        exp_s, sig = token.split(".", 1)
        exp = int(exp_s)
    except ValueError:
        return False
    now = time.time() if now is None else now
    if exp < now or exp > now + MAX_TTL_SECONDS:
        return False
    return hmac.compare_digest(_mac(secret, exp_s), sig)
