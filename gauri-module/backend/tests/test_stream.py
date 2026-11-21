import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech.stream import StreamingSession, StreamLimitExceeded  # noqa: E402


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def make(**kw):
    events: list[dict] = []
    calls = {"partial": 0, "final": 0, "sizes": []}
    clock = kw.pop("clock", FakeClock())

    async def emit(m):
        events.append(m)

    async def partial(audio, fn, lang):
        calls["partial"] += 1
        calls["sizes"].append(len(audio))
        await asyncio.sleep(0)
        return f"partial{calls['partial']}"

    async def final(audio, fn, lang):
        calls["final"] += 1
        return "final text", "whisper"

    s = StreamingSession(
        transcribe_partial=kw.pop("partial", partial),
        transcribe_final=kw.pop("final", final),
        emit=emit,
        clock=clock,
        min_bytes=100,
        partial_interval=1.5,
        **kw,
    )
    return s, events, calls, clock


async def settle():
    for _ in range(5):
        await asyncio.sleep(0)


def test_partials_are_throttled_and_final_is_emitted():
    async def run():
        s, events, calls, clock = make()
        await s.feed(b"x" * 50)          # below min_bytes: nothing
        await settle()
        assert calls["partial"] == 0
        await s.feed(b"x" * 100)         # first partial fires immediately
        await settle()
        assert calls["partial"] == 1
        clock.t = 0.5
        await s.feed(b"x" * 100)         # within interval: throttled
        await settle()
        assert calls["partial"] == 1
        clock.t = 2.0
        await s.feed(b"x" * 100)         # interval passed: second partial sees all audio so far
        await settle()
        assert calls["partial"] == 2 and calls["sizes"][-1] == 350
        text = await s.finish()
        assert text == "final text"
        kinds = [e["type"] for e in events]
        assert kinds == ["partial", "partial", "final"]
        assert events[-1]["engine"] == "whisper"

    asyncio.run(run())


def test_only_one_partial_in_flight():
    async def run():
        gate = asyncio.Event()
        started = {"n": 0}

        async def slow_partial(audio, fn, lang):
            started["n"] += 1
            await gate.wait()
            return "slow"

        s, events, _, clock = make(partial=slow_partial)
        await s.feed(b"x" * 200)
        await settle()
        clock.t = 10
        await s.feed(b"x" * 200)         # first still running -> must not start another
        await settle()
        assert started["n"] == 1
        gate.set()
        await settle()
        await s.finish()

    asyncio.run(run())


def test_no_partial_emitted_after_finish():
    async def run():
        gate = asyncio.Event()

        async def slow_partial(audio, fn, lang):
            await gate.wait()
            return "late partial"

        s, events, _, _ = make(partial=slow_partial)
        await s.feed(b"x" * 200)
        await settle()
        await s.finish()                 # cancels the in-flight partial
        gate.set()
        await settle()
        assert [e["type"] for e in events] == ["final"]

    asyncio.run(run())


def test_duplicate_partial_text_not_resent():
    async def run():
        async def same(audio, fn, lang):
            return "same"

        s, events, _, clock = make(partial=same)
        await s.feed(b"x" * 200)
        await settle()
        clock.t = 5
        await s.feed(b"x" * 10)
        await settle()
        assert [e for e in events if e["type"] == "partial"] == [{"type": "partial", "text": "same"}]
        await s.close()

    asyncio.run(run())


def test_partial_failure_is_swallowed_final_failure_is_reported():
    async def run():
        async def boom(audio, fn, lang):
            raise RuntimeError("asr down")

        s, events, _, _ = make(partial=boom, final=boom)
        await s.feed(b"x" * 200)
        await settle()
        assert events == []              # partial error is silent
        assert await s.finish() == ""
        assert events == [{"type": "error", "message": "transcription failed"}]

    asyncio.run(run())


def test_limits_and_empty_stream():
    async def run():
        s, events, _, _ = make(max_bytes=500)
        with pytest.raises(StreamLimitExceeded):
            await s.feed(b"x" * 600)
        await s.close()

        s2, ev2, _, clock = make(max_seconds=10)
        await s2.feed(b"x")
        clock.t = 11
        with pytest.raises(StreamLimitExceeded):
            await s2.feed(b"x")
        await s2.close()

        s3, ev3, calls, _ = make()
        assert await s3.finish() == ""
        assert ev3 == [{"type": "final", "text": "", "engine": "none"}] and calls["final"] == 0

    asyncio.run(run())


def test_mp4_mime_picks_m4a_filename():
    s, *_ = make(mime="audio/mp4")
    assert s.filename == "stream.m4a"
