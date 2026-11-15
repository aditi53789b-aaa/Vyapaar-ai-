
"""Thread-safe in-memory store for voice-confirmation drafts (Gauri -> backend handoff).

Drafts live for a short TTL and are only turned into real ledger rows after
explicit user confirmation, satisfying the "save only after confirmation" rule.
"""

import threading
import time
import uuid


class DraftStore:
    def __init__(self, ttl_seconds: int = 900):
        self._lock = threading.Lock()
        self._drafts: dict[str, tuple[float, dict]] = {}
        self._ttl = ttl_seconds

    def put(self, payload: dict) -> str:
        draft_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._drafts[draft_id] = (time.time() + self._ttl, payload)
        return draft_id

    def get(self, draft_id: str) -> dict | None:
        with self._lock:
            entry = self._drafts.get(draft_id)
            if not entry:
                return None
            expires_at, payload = entry
            if time.time() > expires_at:
                del self._drafts[draft_id]
                return None
            return payload

    def set_result(self, draft_id: str, result: dict) -> None:
        with self._lock:
            entry = self._drafts.get(draft_id)
            if entry:
                expires_at, payload = entry
                payload["result"] = result
                self._drafts[draft_id] = (expires_at, payload)


voice_drafts = DraftStore(ttl_seconds=900)