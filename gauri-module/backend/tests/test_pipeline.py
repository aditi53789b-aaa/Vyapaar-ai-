import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech.pipeline import SpeechPipeline, normalise_text  # noqa: E402


class FakeBhashini:
    configured = True

    def __init__(self, fail=False):
        self.fail = fail

    async def transcribe(self, audio, lang):
        from speech.bhashini import BhashiniError
        if self.fail:
            raise BhashiniError("down")
        return "रमेश को ५०० रुपये उधार"


class FakeWhisper:
    configured = True

    async def transcribe(self, audio, filename, language):
        return "Ramesh ko 500 udhaar diya"


def test_normalise_digits_and_space():
    assert normalise_text("  ५०० ੫੦  ௫ ") == "500 50 5"


def test_hinglish_uses_whisper():
    p = SpeechPipeline(FakeBhashini(), FakeWhisper())
    r = asyncio.run(p.transcribe(b"x", "a.webm", "hinglish"))
    assert r.engine == "whisper" and "500" in r.text


def test_indic_falls_back_to_whisper_when_bhashini_fails(monkeypatch):
    import speech.pipeline as pl
    monkeypatch.setattr(pl, "to_wav_16k", lambda b: b)
    p = SpeechPipeline(FakeBhashini(fail=True), FakeWhisper())
    r = asyncio.run(p.transcribe(b"x", "a.webm", "hi"))
    assert r.engine == "whisper"


def test_indic_uses_bhashini(monkeypatch):
    import speech.pipeline as pl
    monkeypatch.setattr(pl, "to_wav_16k", lambda b: b)
    p = SpeechPipeline(FakeBhashini(), FakeWhisper())
    r = asyncio.run(p.transcribe(b"x", "a.webm", "hi"))
    assert r.engine == "bhashini" and "500" in r.text
