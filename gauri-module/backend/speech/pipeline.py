"""Dialect conversion pipeline: audio -> normalised text.

Strategy
  * Bhashini first for pure Indic languages (best regional coverage, free for Indian use).
  * Whisper for Hinglish / code-mixed speech or when Bhashini is unavailable.
  * Post-process: regional numerals -> ASCII digits, whitespace cleanup.
"""
from __future__ import annotations

import asyncio
import io
import logging
import subprocess
import wave
from dataclasses import dataclass

from .bhashini import BhashiniClient, BhashiniError
from .whisper import WhisperClient, WhisperError

log = logging.getLogger(__name__)

_DIGIT_MAP = str.maketrans(
    "०१२३४५६७८९੦੧੨੩੪੫੬੭੮੯௦௧௨௩௪௫௬௭௮௯",
    "0123456789" "0123456789" "0123456789",
)


@dataclass
class TranscriptResult:
    text: str
    language: str
    engine: str  # "bhashini" | "whisper"


def normalise_text(text: str) -> str:
    return " ".join(text.translate(_DIGIT_MAP).split())


def to_wav_16k(audio: bytes) -> bytes:
    """Convert browser webm/mp4 to 16 kHz mono 16-bit WAV (Bhashini requirement) using ffmpeg.

    ffmpeg writes WAV to a pipe with a placeholder length in the header (it cannot seek back), which
    some ASR servers reject. So ask for raw PCM and build a correct header ourselves.
    """
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", "pipe:0",
         "-vn", "-ac", "1", "-ar", "16000", "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1"],
        input=audio,
        capture_output=True,
        timeout=30,
    )
    if p.returncode != 0 or not p.stdout:
        raise RuntimeError("ffmpeg conversion failed")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes(p.stdout)
    return buf.getvalue()


class SpeechPipeline:
    def __init__(self, bhashini: BhashiniClient | None = None, whisper: WhisperClient | None = None):
        self.bhashini = bhashini or BhashiniClient()
        self.whisper = whisper or WhisperClient()

    async def transcribe(self, audio: bytes, filename: str, language: str = "hinglish") -> TranscriptResult:
        language = (language or "hinglish").lower()
        use_bhashini_first = language not in ("hinglish", "en") and self.bhashini.configured

        if use_bhashini_first:
            try:
                wav = await asyncio.to_thread(to_wav_16k, audio)  # keep the event loop free
                text = await self.bhashini.transcribe(wav, language)
                if text:
                    return TranscriptResult(normalise_text(text), language, "bhashini")
            except (BhashiniError, RuntimeError) as e:
                log.warning("Bhashini failed, falling back to Whisper: %s", e)

        try:
            text = await self.whisper.transcribe(audio, filename, None if language == "hinglish" else language)
            return TranscriptResult(normalise_text(text), language, "whisper")
        except WhisperError as e:
            raise RuntimeError(f"All ASR engines failed: {e}") from e

    async def transcribe_fast(self, audio: bytes, filename: str, language: str = "hinglish") -> str:
        """Low-latency pass for streaming partials: Whisper only (no ffmpeg hop); Bhashini if Whisper is unavailable."""
        language = (language or "hinglish").lower()
        if self.whisper.configured:
            try:
                text = await self.whisper.transcribe(audio, filename, None if language == "hinglish" else language)
                return normalise_text(text)
            except WhisperError as e:
                log.info("fast path: whisper failed (%s)", e)
        if self.bhashini.configured and language not in ("hinglish", "en"):
            wav = await asyncio.to_thread(to_wav_16k, audio)
            return normalise_text(await self.bhashini.transcribe(wav, language))
        raise RuntimeError("no ASR engine available for partials")
