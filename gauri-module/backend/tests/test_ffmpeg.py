"""Real audio conversion check (skipped when ffmpeg is unavailable)."""
import shutil
import subprocess
import sys
import wave
import io
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech.pipeline import to_wav_16k  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")


def make_webm(seconds=1) -> bytes:
    p = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i", f"sine=frequency=440:duration={seconds}",
         "-ac", "2", "-ar", "48000", "-c:a", "libopus", "-f", "webm", "pipe:1"],
        capture_output=True,
    )
    if p.returncode != 0:
        pytest.skip("ffmpeg lacks libopus/webm support")
    return p.stdout


def test_webm_to_16k_mono_wav():
    wav = to_wav_16k(make_webm(1))
    with wave.open(io.BytesIO(wav)) as w:
        assert (w.getframerate(), w.getnchannels()) == (16000, 1)
        assert 0.9 < w.getnframes() / 16000 < 1.2


def test_truncated_stream_prefix_still_converts():
    """Streaming partials send a prefix of the recording; ffmpeg must cope with a cut-off file."""
    data = make_webm(2)
    wav = to_wav_16k(data[: int(len(data) * 0.6)])
    with wave.open(io.BytesIO(wav)) as w:
        assert w.getnframes() > 0


def test_garbage_raises():
    with pytest.raises(RuntimeError):
        to_wav_16k(b"this is not audio")
