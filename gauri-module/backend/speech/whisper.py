"""Whisper ASR client (OpenAI-hosted). Used as fallback / for Hinglish code-mixing.

Env: OPENAI_API_KEY
"""
from __future__ import annotations

import os

import httpx

OPENAI_URL = "https://api.openai.com/v1/audio/transcriptions"

# Priming prompt nudges Whisper toward ledger vocabulary + romanised Hinglish.
LEDGER_PROMPT = (
    "Dukaan ka hisaab: udhaar, baaki, khata, jama, kharcha, kiraya, bijli bill, "
    "paanch sau rupaye, hazaar, lakh, kilo, litre, darjan, UPI, cash."
)


class WhisperError(RuntimeError):
    pass


class WhisperClient:
    def __init__(self, api_key: str | None = None, model: str = "whisper-1", timeout: float = 30.0):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.timeout = timeout

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, audio: bytes, filename: str = "entry.webm", language: str | None = None) -> str:
        if not self.configured:
            raise WhisperError("OPENAI_API_KEY not configured")
        data = {"model": self.model, "prompt": LEDGER_PROMPT, "response_format": "json", "temperature": "0"}
        if language and language != "hinglish":
            data["language"] = language
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                OPENAI_URL,
                headers={"Authorization": f"Bearer {self.api_key}"},
                data=data,
                files={"file": (filename, audio)},
            )
        if r.status_code != 200:
            raise WhisperError(f"whisper failed: {r.status_code}")
        return r.json().get("text", "").strip()
