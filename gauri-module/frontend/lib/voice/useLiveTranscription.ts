"use client";
/**
 * Live (streaming) transcription on top of useVoiceRecorder.
 *
 *   mic chunks (250 ms) --WebSocket--> FastAPI /speech/stream --> {"type":"partial"|"final", text}
 *
 * Graceful degradation, in order:
 *   1. WebSocket live partials + final transcript
 *   2. if the socket cannot open / drops / times out  -> upload the whole clip to /api/transcribe
 *   3. if the device is offline                       -> hand the clip to onOffline (queue it in Dexie)
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { pickMimeType, useVoiceRecorder } from "./useVoiceRecorder";

export interface LiveTranscriptionOptions {
  language: string;
  onFinal: (text: string, meta: { engine: string; mode: "live" | "upload" }) => void;
  onError?: (message: string) => void;
  /** called instead of uploading when navigator.onLine is false */
  onOffline?: (clip: Blob, mime: string) => void;
  /** how long to wait for the server's final transcript before falling back to upload */
  finalTimeoutMs?: number;
}

export function useLiveTranscription(opts: LiveTranscriptionOptions) {
  const optsRef = useRef(opts);
  optsRef.current = opts;

  const [partial, setPartial] = useState("");
  const [busy, setBusy] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const queueRef = useRef<Blob[]>([]); // chunks captured before the socket finished opening
  const doneRef = useRef(false); // a final transcript (or fallback result) was delivered
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const sessionRef = useRef(0); // guards against late events from a previous recording

  const closeSocket = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = null;
    const ws = wsRef.current;
    wsRef.current = null;
    if (ws && ws.readyState <= WebSocket.OPEN) ws.close();
  }, []);

  const uploadFallback = useCallback(
    async (clip: Blob, mime: string, session: number) => {
      if (doneRef.current || session !== sessionRef.current) return;
      if (typeof navigator !== "undefined" && navigator.onLine === false && optsRef.current.onOffline) {
        doneRef.current = true;
        setBusy(false);
        optsRef.current.onOffline(clip, mime);
        return;
      }
      try {
        const fd = new FormData();
        fd.append("audio", clip, `entry.${mime.includes("mp4") ? "m4a" : "webm"}`);
        fd.append("language", optsRef.current.language);
        const res = await fetch("/api/transcribe", { method: "POST", body: fd });
        if (!res.ok) throw new Error("Could not understand the audio");
        const data = await res.json();
        if (session !== sessionRef.current || doneRef.current) return;
        doneRef.current = true;
        optsRef.current.onFinal(String(data.text ?? ""), { engine: data.engine ?? "unknown", mode: "upload" });
      } catch (e) {
        if (session === sessionRef.current && !doneRef.current) {
          optsRef.current.onError?.((e as Error).message || "Transcription failed");
        }
      } finally {
        if (session === sessionRef.current) setBusy(false);
      }
    },
    []
  );

  const openSocket = useCallback(
    async (session: number) => {
      try {
        const tokRes = await fetch("/api/speech-token", { method: "POST" });
        if (!tokRes.ok) return; // live mode not configured -> recorder still works, upload fallback
        const { token, wsUrl } = await tokRes.json();
        if (session !== sessionRef.current) return;

        const ws = new WebSocket(`${wsUrl}?token=${encodeURIComponent(token)}`);
        wsRef.current = ws;
        ws.onopen = () => {
          ws.send(JSON.stringify({ type: "start", language: optsRef.current.language, mime: pickMimeType() ?? "" }));
          for (const chunk of queueRef.current) ws.send(chunk); // keep order: flush backlog first
          queueRef.current = [];
        };
        ws.onmessage = (ev) => {
          if (session !== sessionRef.current || typeof ev.data !== "string") return;
          try {
            const msg = JSON.parse(ev.data);
            if (msg.type === "partial") setPartial(String(msg.text ?? ""));
            else if (msg.type === "final" && !doneRef.current) {
              doneRef.current = true;
              if (timerRef.current) clearTimeout(timerRef.current);
              setBusy(false);
              setPartial("");
              optsRef.current.onFinal(String(msg.text ?? ""), { engine: msg.engine ?? "unknown", mode: "live" });
              closeSocket();
            }
          } catch {
            /* ignore malformed frames */
          }
        };
        ws.onclose = () => {
          if (wsRef.current === ws) wsRef.current = null;
        };
        ws.onerror = () => {
          /* fallback happens in onComplete / timeout */
        };
      } catch {
        /* network error: recorder keeps going, upload fallback will handle it */
      }
    },
    [closeSocket]
  );

  const recorder = useVoiceRecorder({
    timesliceMs: 250,
    onChunk: (chunk) => {
      const ws = wsRef.current;
      if (ws && ws.readyState === WebSocket.OPEN) ws.send(chunk);
      else queueRef.current.push(chunk);
    },
    onComplete: (clip, mime) => {
      const session = sessionRef.current;
      const ws = wsRef.current;
      setBusy(true);
      if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "stop" }));
        timerRef.current = setTimeout(() => {
          closeSocket();
          void uploadFallback(clip, mime, session);
        }, optsRef.current.finalTimeoutMs ?? 10_000);
      } else {
        closeSocket();
        void uploadFallback(clip, mime, session);
      }
    },
  });

  const start = useCallback(async () => {
    sessionRef.current += 1;
    doneRef.current = false;
    queueRef.current = [];
    setPartial("");
    void openSocket(sessionRef.current); // do not block the mic on the socket
    await recorder.start();
  }, [openSocket, recorder]);

  useEffect(() => () => closeSocket(), [closeSocket]);

  return {
    start,
    stop: recorder.stop,
    isRecording: recorder.isRecording,
    level: recorder.level,
    error: recorder.error,
    partial,
    busy,
  };
}
