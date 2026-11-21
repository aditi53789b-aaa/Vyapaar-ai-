"use client";
/**
 * Cross-browser mic capture using the HTML5 MediaRecorder API.
 * - Picks the best supported mime type (Chrome/Firefox: webm/opus, Safari: mp4).
 * - Emits small chunks (timeslice) so audio can be streamed with low latency.
 * - Exposes a live input level (0..1) for a waveform / "listening" indicator.
 */
import { useCallback, useEffect, useRef, useState } from "react";

const MIME_CANDIDATES = [
  "audio/webm;codecs=opus",
  "audio/webm",
  "audio/mp4", // Safari / iOS
  "audio/ogg;codecs=opus",
];

export function pickMimeType(): string | undefined {
  if (typeof MediaRecorder === "undefined") return undefined;
  return MIME_CANDIDATES.find((m) => MediaRecorder.isTypeSupported(m));
}

export type RecorderState = "idle" | "requesting" | "recording" | "error";

export interface UseVoiceRecorderOptions {
  /** ms between ondataavailable events; smaller = lower latency */
  timesliceMs?: number;
  /** auto-stop after this many ms of silence (0 disables) */
  silenceStopMs?: number;
  /** auto-stop hard limit */
  maxDurationMs?: number;
  /** called for every audio chunk (for streaming upload) */
  onChunk?: (chunk: Blob) => void;
  /** called once with the full recording when stopped */
  onComplete?: (audio: Blob, mimeType: string) => void;
}

export function useVoiceRecorder(opts: UseVoiceRecorderOptions = {}) {
  const {
    timesliceMs = 250,
    silenceStopMs = 2500,
    maxDurationMs = 30_000,
    onChunk,
    onComplete,
  } = opts;

  const [state, setState] = useState<RecorderState>("idle");
  const [level, setLevel] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const rafRef = useRef<number | null>(null);
  const maxTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastVoiceRef = useRef<number>(0);

  const cleanup = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current);
    if (maxTimerRef.current) clearTimeout(maxTimerRef.current);
    streamRef.current?.getTracks().forEach((t) => t.stop());
    audioCtxRef.current?.close().catch(() => {});
    rafRef.current = null;
    maxTimerRef.current = null;
    streamRef.current = null;
    audioCtxRef.current = null;
    setLevel(0);
  }, []);

  const stop = useCallback(() => {
    const rec = recorderRef.current;
    if (rec && rec.state !== "inactive") rec.stop();
  }, []);

  const start = useCallback(async () => {
    setError(null);
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === "undefined") {
      setState("error");
      setError("Voice recording is not supported in this browser.");
      return;
    }
    setState("requesting");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          echoCancellation: true,
          noiseSuppression: true, // helps in noisy shops / markets
          autoGainControl: true,
        },
      });
      streamRef.current = stream;

      const mimeType = pickMimeType();
      const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      recorderRef.current = recorder;
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          chunksRef.current.push(e.data);
          onChunk?.(e.data);
        }
      };
      recorder.onstop = () => {
        const type = recorder.mimeType || mimeType || "audio/webm";
        const blob = new Blob(chunksRef.current, { type });
        cleanup();
        setState("idle");
        if (blob.size > 0) onComplete?.(blob, type);
      };
      recorder.onerror = () => {
        cleanup();
        setState("error");
        setError("Recording failed. Please try again.");
      };

      // Level meter + silence detection
      const Ctx = window.AudioContext || (window as any).webkitAudioContext;
      const ctx = new Ctx();
      audioCtxRef.current = ctx;
      const analyser = ctx.createAnalyser();
      analyser.fftSize = 512;
      ctx.createMediaStreamSource(stream).connect(analyser);
      const buf = new Uint8Array(analyser.fftSize);
      lastVoiceRef.current = performance.now();

      const tick = () => {
        analyser.getByteTimeDomainData(buf);
        let sum = 0;
        for (let i = 0; i < buf.length; i++) {
          const v = (buf[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / buf.length);
        setLevel(Math.min(1, rms * 4));
        if (rms > 0.02) lastVoiceRef.current = performance.now();
        if (silenceStopMs > 0 && performance.now() - lastVoiceRef.current > silenceStopMs) {
          stop();
          return;
        }
        rafRef.current = requestAnimationFrame(tick);
      };
      rafRef.current = requestAnimationFrame(tick);

      maxTimerRef.current = setTimeout(stop, maxDurationMs);
      recorder.start(timesliceMs);
      setState("recording");
    } catch (err: any) {
      cleanup();
      setState("error");
      setError(
        err?.name === "NotAllowedError"
          ? "Microphone permission denied. Please allow mic access."
          : "Could not access the microphone."
      );
    }
  }, [cleanup, maxDurationMs, onChunk, onComplete, silenceStopMs, stop, timesliceMs]);

  useEffect(() => cleanup, [cleanup]);

  return { state, level, error, start, stop, isRecording: state === "recording" };
}
