import { NextResponse } from "next/server";

export const runtime = "nodejs";

/**
 * Thin proxy to the FastAPI speech service (backend/speech). Keeps Bhashini /
 * Whisper credentials server-side and lets the browser post a single audio blob.
 */
const SPEECH_URL = process.env.SPEECH_SERVICE_URL ?? "http://localhost:8000";

export async function POST(req: Request) {
  const form = await req.formData();
  const audio = form.get("audio");
  if (!(audio instanceof Blob) || audio.size === 0) {
    return NextResponse.json({ error: "No audio provided" }, { status: 400 });
  }
  if (audio.size > 10 * 1024 * 1024) {
    return NextResponse.json({ error: "Audio too large" }, { status: 413 });
  }
  const upstream = new FormData();
  upstream.append("audio", audio, (audio as File).name || "entry.webm");
  const lang = form.get("language");
  if (typeof lang === "string") upstream.append("language", lang);

  const res = await fetch(`${SPEECH_URL}/speech/transcribe`, {
    method: "POST",
    body: upstream,
    headers: process.env.SPEECH_API_KEY ? { "X-Internal-Key": process.env.SPEECH_API_KEY } : undefined,
  });
  const data = await res.json().catch(() => ({}));
  return NextResponse.json(data, { status: res.status });
}
