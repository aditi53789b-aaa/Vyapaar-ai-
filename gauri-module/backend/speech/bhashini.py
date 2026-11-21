"""Bhashini (ULCA / Dhruva) ASR client.

Flow (per Bhashini's pipeline API):
  1. POST pipeline-search with userID + ulcaApiKey -> get callback URL, auth token, serviceId
  2. POST callback URL with base64 audio -> transcript

Env: BHASHINI_USER_ID, BHASHINI_ULCA_API_KEY
NOTE: verify endpoint URLs / payload shape against the current Bhashini docs
(https://bhashini.gitbook.io) before production; they have changed between releases.
"""
from __future__ import annotations

import base64
import os

import httpx

PIPELINE_SEARCH_URL = "https://meity-auth.ulcacontrib.org/ulca/apis/v0/model/getModelsPipeline"
PIPELINE_ID = "64392f96daac500b55c543cd"  # public ASR/Translation/TTS pipeline id

# Bhashini language codes for supported merchant languages
SUPPORTED = {"hi", "en", "pa", "mr", "ta", "te", "bn", "gu", "kn", "ml", "or", "ur", "as"}


class BhashiniError(RuntimeError):
    pass


class BhashiniClient:
    def __init__(self, user_id: str | None = None, api_key: str | None = None, timeout: float = 20.0):
        self.user_id = user_id or os.getenv("BHASHINI_USER_ID")
        self.api_key = api_key or os.getenv("BHASHINI_ULCA_API_KEY")
        self.timeout = timeout
        self._cache: dict[str, dict] = {}

    @property
    def configured(self) -> bool:
        return bool(self.user_id and self.api_key)

    async def _get_pipeline(self, client: httpx.AsyncClient, lang: str) -> dict:
        if lang in self._cache:
            return self._cache[lang]
        payload = {
            "pipelineTasks": [{"taskType": "asr", "config": {"language": {"sourceLanguage": lang}}}],
            "pipelineRequestConfig": {"pipelineId": PIPELINE_ID},
        }
        headers = {"userID": self.user_id, "ulcaApiKey": self.api_key}
        r = await client.post(PIPELINE_SEARCH_URL, json=payload, headers=headers)
        if r.status_code != 200:
            raise BhashiniError(f"pipeline search failed: {r.status_code}")
        d = r.json()
        info = {
            "url": d["pipelineInferenceAPIEndPoint"]["callbackUrl"],
            "auth_name": d["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["name"],
            "auth_value": d["pipelineInferenceAPIEndPoint"]["inferenceApiKey"]["value"],
            "service_id": d["pipelineResponseConfig"][0]["config"][0]["serviceId"],
        }
        self._cache[lang] = info
        return info

    async def transcribe(self, audio: bytes, language: str = "hi") -> str:
        if not self.configured:
            raise BhashiniError("Bhashini credentials not configured")
        if language not in SUPPORTED:
            raise BhashiniError(f"unsupported language {language}")
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            info = await self._get_pipeline(client, language)
            body = {
                "pipelineTasks": [
                    {
                        "taskType": "asr",
                        "config": {
                            "language": {"sourceLanguage": language},
                            "serviceId": info["service_id"],
                            "audioFormat": "wav",
                            "samplingRate": 16000,
                        },
                    }
                ],
                "inputData": {"audio": [{"audioContent": base64.b64encode(audio).decode()}]},
            }
            r = await client.post(info["url"], json=body, headers={info["auth_name"]: info["auth_value"]})
            if r.status_code != 200:
                self._cache.pop(language, None)  # token may have expired
                raise BhashiniError(f"asr failed: {r.status_code}")
            try:
                return r.json()["pipelineResponse"][0]["output"][0]["source"].strip()
            except (KeyError, IndexError) as e:
                raise BhashiniError("unexpected ASR response shape") from e
