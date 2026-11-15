import { createHmac } from "node:crypto";
import { NextResponse } from "next/server";

export const runtime = "nodejs";

/**
 * Issues a short-lived token for the live-transcription WebSocket (browsers cannot set headers on
 * WebSockets, so the token travels as ?token=). Format: "<expiryUnix>.<hmacSHA256(expiry)>", verified
 * by backend/speech/tokens.py with the same SPEECH_WS_SECRET.
 *
 * TODO(Aditi): call your session/auth check here first; only logged-in merchants should get a token.
 */
export async function POST() {
  const secret = process.env.SPEECH_WS_SECRET;
  const wsUrl = process.env.NEXT_PUBLIC_SPEECH_WS_URL;
  if (!secret || !wsUrl) {
    return NextResponse.json({ error: "Live transcription is not configured" }, { status: 503 });
  }
  const exp = String(Math.floor(Date.now() / 1000) + 120);
  const sig = createHmac("sha256", secret).update(exp).digest("hex");
  return NextResponse.json({ token: `${exp}.${sig}`, wsUrl });
}
