import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from speech.tokens import issue_token, verify_token  # noqa: E402
from speech.webhooks import (  # noqa: E402
    JobStore,
    deliver_callback,
    run_job,
    sign,
    validate_callback_url,
    verify,
)

SECRET = "s3cret"
BODY = b'{"job_id":"abc","text":"hello"}'


# ---- signatures ----
def test_sign_verify_roundtrip():
    h = sign(SECRET, BODY, timestamp=1000)
    assert verify(SECRET, h, BODY, now=1000)
    assert verify(SECRET, h, BODY, now=1299)


def test_verify_rejects_tamper_wrong_secret_replay_and_garbage():
    h = sign(SECRET, BODY, timestamp=1000)
    assert not verify(SECRET, h, BODY + b" ", now=1000)          # body changed
    assert not verify("other", h, BODY, now=1000)                # wrong secret
    assert not verify(SECRET, h, BODY, now=1000 + 301)           # too old (replay)
    assert not verify(SECRET, h, BODY, now=1000 - 301)           # from the future
    assert not verify(SECRET, None, BODY)
    assert not verify(None, h, BODY, now=1000)
    assert not verify(SECRET, "garbage", BODY)
    assert not verify(SECRET, "t=abc,v1=00", BODY)


# ---- SSRF guard ----
def test_callback_url_validation():
    ok = {"api.vyapaarsathi.in"}
    assert validate_callback_url("https://api.vyapaarsathi.in/hook", ok)
    for bad in (
        "http://api.vyapaarsathi.in/hook",                    # not https
        "https://evil.com/hook",                              # not allowlisted
        "https://api.vyapaarsathi.in.evil.com/hook",          # look-alike suffix
        "https://api.vyapaarsathi.in@evil.com/hook",          # userinfo trick (real host = evil.com)
        "https://user:pw@api.vyapaarsathi.in/hook",           # credentials
        "https://169.254.169.254/latest/meta-data",           # cloud metadata
        "ftp://api.vyapaarsathi.in/x",
        "not a url",
    ):
        with pytest.raises(ValueError):
            validate_callback_url(bad, ok)
    with pytest.raises(ValueError):
        validate_callback_url("https://api.vyapaarsathi.in/hook", set())  # empty allowlist denies all


# ---- job store ----
def test_job_store_ttl_and_cap():
    now = {"t": 0.0}
    store = JobStore(ttl=100, max_jobs=3, clock=lambda: now["t"])
    a = store.create()
    assert store.get(a)["status"] == "pending"
    store.update(a, status="done", text="x")
    assert store.get(a)["text"] == "x"
    now["t"] = 101
    assert store.get(a) is None                                  # expired
    ids = []
    for i in range(5):
        now["t"] += 1
        ids.append(store.create())
    assert store.get(ids[0]) is None and store.get(ids[-1]) is not None   # oldest evicted at cap


# ---- outbound delivery ----
class FakeClient:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.calls = []

    async def post(self, url, content, headers):
        self.calls.append((url, content, headers))
        s = self.statuses.pop(0)
        if isinstance(s, Exception):
            raise s
        return SimpleNamespace(status_code=s)


async def no_sleep(_):
    return None


def test_delivery_signs_and_retries_server_errors():
    async def run():
        c = FakeClient([500, ConnectionError("x"), 200])
        ok = await deliver_callback(c, "https://h/x", {"a": 1}, SECRET, sleep=no_sleep)
        assert ok and len(c.calls) == 3
        _, body, headers = c.calls[-1]
        assert json.loads(body) == {"a": 1}
        assert verify(SECRET, headers["X-VS-Signature"], body)

    asyncio.run(run())


def test_delivery_does_not_retry_client_errors_and_gives_up():
    async def run():
        c = FakeClient([400])
        assert not await deliver_callback(c, "https://h/x", {}, SECRET, sleep=no_sleep)
        assert len(c.calls) == 1
        c2 = FakeClient([503, 503, 503])
        assert not await deliver_callback(c2, "https://h/x", {}, SECRET, retries=3, sleep=no_sleep)
        assert len(c2.calls) == 3

    asyncio.run(run())


# ---- job runner ----
def test_run_job_success_and_failure_paths():
    async def run():
        store = JobStore()

        async def ok(audio, fn, lang):
            return SimpleNamespace(text="Ramesh ko 500 udhaar", engine="whisper")

        async def bad(audio, fn, lang):
            raise RuntimeError("nope")

        client = FakeClient([200, 200])
        j1 = store.create()
        await run_job(j1, store, ok, b"a", "a.webm", "hi", "https://h/cb", SECRET, lambda: client)
        assert store.get(j1)["status"] == "done" and store.get(j1)["text"] == "Ramesh ko 500 udhaar"
        assert json.loads(client.calls[0][1])["status"] == "done"

        j2 = store.create()
        await run_job(j2, store, bad, b"a", "a.webm", "hi", "https://h/cb", SECRET, lambda: client)
        assert store.get(j2)["status"] == "failed"
        assert "nope" not in json.dumps(store.get(j2))            # internal error text is not leaked
        assert json.loads(client.calls[1][1]) == {"job_id": j2, "status": "failed"}

        j3 = store.create()                                       # no callback: still records the result
        await run_job(j3, store, ok, b"a", "a.webm", "hi")
        assert store.get(j3)["status"] == "done"

    asyncio.run(run())


# ---- websocket tokens ----
def test_ws_tokens():
    t = issue_token("k", ttl=60, now=1000)
    assert verify_token(t, "k", now=1000)
    assert not verify_token(t, "k", now=1061)                    # expired
    assert not verify_token(t, "other", now=1000)                # wrong secret
    assert not verify_token(t + "0", "k", now=1000)              # tampered
    assert not verify_token(None, "k") and not verify_token(t, None) and not verify_token("junk", "k")
    far = issue_token("k", ttl=999_999, now=1000)
    assert not verify_token(far, "k", now=1000)                  # absurd lifetime rejected
