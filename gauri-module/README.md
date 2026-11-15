# Vyapaar Sathi: Gauri's workstream (Intelligent Systems & Speech)

**Try it now, no setup:** open `demo/vyapaar_sathi_demo.html` in Chrome or Edge. It runs the real parser, conversation
context, insights and credit-readiness code in the browser (mic capture included).

## What the blueprint assigns, and where it lives

| Blueprint item | Files |
|---|---|
| **Browser Mic Streaming Matrix** (MediaRecorder, low-latency) | `frontend/lib/voice/useVoiceRecorder.ts` (capture, level meter, silence stop), `useLiveTranscription.ts` (WebSocket streaming + fallbacks) |
| **Dialect Conversion Pipeline** (Bhashini + Whisper, webhooks) | `backend/speech/`: `bhashini.py`, `whisper.py`, `pipeline.py`, `stream.py` (live partials), `webhooks.py` (signed in/out webhooks, async jobs), `tokens.py`, `router.py` |
| **Structured Intent Parsing** (JSON blocks) | `frontend/lib/ai/schemas.ts`, `intent.ts` (LLM), `ruleParser.ts` + `numbers.ts` (offline Hinglish/Devanagari parser) |
| **Conversational context parsing** | `frontend/lib/ai/context.ts`: pronouns, "aur 200", follow-up questions ("Kitne rupaye?"), answers |
| **Generative business insight loops** | `ledgerStats.ts` (numbers), `insightRules.ts` (rules + "what changed since last time"), `insights.ts` + `app/api/insights` (LLM narration), `components/InsightsPanel.tsx` |
| **Credit Readiness Copilot** (RAG, pgvector) | `backend/rag/schema.sql`, `schemes.json`, `scripts/ingest-schemes.ts`, `lib/ai/rag.ts`, `readiness.ts`, `app/api/copilot`, `components/CreditCopilot.tsx` |
| Llama 3.3 / GPT-4o-mini switch | `lib/ai/model.ts` |
| Offline voice | `lib/voice/offlineQueue.ts` (Dexie queue) + on-device parsing in `VoiceEntry.tsx` |

## Flow

```
mic --250ms chunks--> WebSocket /speech/stream --partials--> live text on screen
                          |  (fallback: upload clip -> /api/transcribe; offline: queue in Dexie)
                          v
         Bhashini (Indic) / Whisper (Hinglish)  --> text
                          v
  /api/parse-intent: LLM (if configured) -> rule parser fallback -> context resolver -> sanity checks
                          v
   confirmation card (asks ONE follow-up question if amount/party/type is missing) --> onConfirm(intent)
```

Insights and the Copilot never let the AI invent numbers: `ledgerStats.ts` / `readiness.ts` compute them
deterministically; the model only explains them.

## Setup

1. **Env**: copy `.env.example`. The speech endpoints refuse requests without `SPEECH_API_KEY` / a signed token unless `SPEECH_ENV=dev`.
2. **DB** (with Aditi): `psql $DATABASE_URL -f backend/rag/schema.sql`, then `npx tsx frontend/scripts/ingest-schemes.ts`
3. **Backend**: `pip install -r backend/requirements.txt`; install `ffmpeg`; in the main FastAPI app: `app.include_router(speech.router.router)`
4. **Frontend**: `npm i ai @ai-sdk/openai zod pg dexie` and `npm i -D tsx @types/pg`; copy `frontend/{lib,components,app/api,scripts}` into the Next.js project
5. **Tests**: `cd backend && pytest tests`  ·  `cd frontend && node --experimental-strip-types --no-warnings --import ./tests/register.mjs --test tests/*.test.ts`
6. **Rebuild the demo** after changing parser code: `node frontend/scripts/build-demo.mjs`

## Integration contracts

- `VoiceEntry onConfirm(intent, transcript)`: Arshpreet persists to Dexie. `LedgerTxn` in `ledgerStats.ts` is the row shape the insights/Copilot read.
- `CreditCopilot` / `InsightsPanel` accept ledger rows directly; credit metrics are derived (`deriveProfile`), so no extra backend endpoint is required.
- `app/api/speech-token`: add Aditi's auth check (marked TODO) before it issues tokens.
- Async jobs: `POST /speech/jobs` (+ optional `callback_url`), `GET /speech/jobs/{id}`, signed `POST /speech/webhooks/{provider}`.

## What was verified, and what was not

Verified here (automated):
- 22 Python tests: streaming session logic, webhook signing/replay/SSRF checks, tokens, job runner, ffmpeg conversion (including truncated streams), fallback pipeline.
- 23 TypeScript tests: spoken-number parsing, Hinglish/Devanagari entries, context resolution, ledger maths (FIFO udhaar, overdue), insights, readiness score.
- Strict `tsc` type-check with stand-in typings for third-party packages.
- Browser run of the demo (Chromium, fake mic): multi-turn entry, insights, scoring, mic capture, XSS check, phone layout.

**Not** verified (needs your environment and keys):
- Real Bhashini calls. Endpoint URLs/payload shape were written from memory of their pipeline API; confirm against current docs.
- Real Whisper/OpenAI/Llama calls, and Vercel AI SDK version differences (`generateObject`, `streamText` signatures change between majors).
- FastAPI routes and the WebSocket handler (compiled and logic-tested through `StreamingSession`, but FastAPI was not installed here).
- pgvector retrieval (no Postgres server here), the Dexie offline queue, and the React components inside a real Next.js build.

## Known limits

- `backend/rag/schemes.json` is a **draft**: verify every scheme against its `source_url`, then set `verified: true`.
- The rule parser covers common Hinglish/Hindi; rarer phrasing and Devanagari numbers above 20 fall to the LLM.
- Streaming partials re-transcribe the audio so far every ~1.5 s (Whisper has no true incremental API), which costs more API calls than one final pass.
- Bhashini's public pipeline is request/response; the inbound webhook exists for async-capable providers or other Vyapaar services.
- Job store is in-memory (single process); use Redis/Postgres for multiple workers.
- Not built: Punjabi/Marathi/Tamil number words in the rule parser, LangChain.js (the Vercel AI SDK covers the same paths).
