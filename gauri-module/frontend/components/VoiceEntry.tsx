"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useLiveTranscription } from "@/lib/voice/useLiveTranscription";
import { autoDrainOnReconnect, enqueueClip, queuedCount } from "@/lib/voice/offlineQueue";
import { emptyContext, nextQuestion, pushTurn, resolveTurn, type ConversationContext } from "@/lib/ai/context";
import { ruleParse } from "@/lib/ai/ruleParser";
import { sanityCheck } from "@/lib/ai/sanity";
import { todayISO } from "@/lib/ai/dates";
import type { TransactionIntent } from "@/lib/ai/types";

const LANGS = [
  { code: "hinglish", label: "Hinglish" },
  { code: "hi", label: "हिन्दी" },
  { code: "pa", label: "ਪੰਜਾਬੀ" },
  { code: "mr", label: "मराठी" },
  { code: "ta", label: "தமிழ்" },
  { code: "en", label: "English" },
];

interface Props {
  /** Called with the parsed entry once the merchant confirms it (Arshpreet saves to Dexie; Aditi's API syncs). */
  onConfirm: (intent: TransactionIntent, transcript: string) => void;
}

/**
 * Voice-first ledger entry: live partial transcript, multi-turn clarification, offline fallbacks.
 * Works with no network: typed entries are parsed on-device by the rule parser.
 */
export default function VoiceEntry({ onConfirm }: Props) {
  const [language, setLanguage] = useState("hinglish");
  const [ctx, setCtx] = useState<ConversationContext>(emptyContext());
  const ctxRef = useRef(ctx);
  ctxRef.current = ctx;

  const [text, setText] = useState("");
  const [intent, setIntent] = useState<TransactionIntent | null>(null);
  const [question, setQuestion] = useState<string | null>(null);
  const [engine, setEngine] = useState<string>("");
  const [err, setErr] = useState<string | null>(null);
  const [parsing, setParsing] = useState(false);
  const [offlineClips, setOfflineClips] = useState(0);
  const [inbox, setInbox] = useState<string[]>([]); // transcripts of clips recorded offline

  const languageRef = useRef(language);
  languageRef.current = language;

  const handleText = useCallback(async (raw: string) => {
    const t = raw.trim();
    if (!t) return;
    setErr(null);
    setParsing(true);
    const today = todayISO();
    const history = ctxRef.current.turns;
    let result: { intent: TransactionIntent; question: string | null; engine: string };
    try {
      if (!navigator.onLine) throw new Error("offline");
      const r = await fetch("/api/parse-intent", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: t, language: languageRef.current, today, history }),
      });
      if (!r.ok) throw new Error("server");
      result = await r.json();
    } catch {
      // offline or server down: parse on-device so the merchant is never blocked
      const parsed = sanityCheck(ruleParse(t, { today }));
      const { intent: resolved } = resolveTurn(t, parsed, ctxRef.current);
      result = { intent: resolved, question: nextQuestion(resolved, languageRef.current), engine: "on-device" };
    }
    setIntent(result.intent);
    setQuestion(result.question);
    setEngine(result.engine);
    setCtx((c) => pushTurn(c, t, result.intent));
    setText(t);
    setParsing(false);
  }, []);

  const live = useLiveTranscription({
    language,
    onFinal: (t) => void handleText(t),
    onError: (m) => setErr(m),
    onOffline: async (clip, mime) => {
      await enqueueClip(clip, mime, languageRef.current);
      setOfflineClips(await queuedCount());
    },
  });

  // transcribe queued clips when the connection returns
  useEffect(() => {
    void queuedCount().then(setOfflineClips).catch(() => {});
    return autoDrainOnReconnect(async (clip) => {
      const fd = new FormData();
      fd.append("audio", clip.blob, `queued.${clip.mime.includes("mp4") ? "m4a" : "webm"}`);
      fd.append("language", clip.language);
      const res = await fetch("/api/transcribe", { method: "POST", body: fd });
      if (!res.ok) return false;
      const { text: t } = await res.json();
      if (t) setInbox((x) => [...x, String(t)]);
      setOfflineClips(await queuedCount().catch(() => 0));
      return true;
    });
  }, []);

  const reset = () => {
    setCtx(emptyContext());
    setIntent(null);
    setQuestion(null);
    setText("");
    setErr(null);
  };

  const recording = live.isRecording;
  const level = live.level;

  return (
    <div className="space-y-4 rounded-xl border p-4">
      <div className="flex items-center gap-3">
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="rounded-md border px-2 py-1 text-sm"
          aria-label="Language"
          disabled={recording || live.busy}
        >
          {LANGS.map((l) => (
            <option key={l.code} value={l.code}>{l.label}</option>
          ))}
        </select>
        {typeof navigator !== "undefined" && !navigator.onLine && (
          <span className="text-xs text-amber-700">Offline: type your entry, or record and we will transcribe later</span>
        )}
      </div>

      <button
        onClick={recording ? live.stop : live.start}
        disabled={live.busy}
        aria-pressed={recording}
        className={`flex h-20 w-20 items-center justify-center rounded-full text-white transition ${
          recording ? "bg-red-600" : "bg-emerald-600"
        } disabled:opacity-50`}
        style={recording ? { boxShadow: `0 0 0 ${4 + level * 18}px rgba(220,38,38,0.25)` } : undefined}
      >
        {live.busy ? "..." : recording ? "Stop" : "Bolo"}
      </button>

      {recording && live.partial && <p className="text-sm italic text-muted-foreground">{live.partial}…</p>}
      {(live.error || err) && <p className="text-sm text-red-600">{live.error || err}</p>}
      {offlineClips > 0 && (
        <p className="text-xs text-amber-700">{offlineClips} voice note(s) saved offline; they will be transcribed when you are back online.</p>
      )}
      {inbox.length > 0 && (
        <div className="space-y-1 text-sm">
          <div className="font-medium">Offline voice notes ready:</div>
          {inbox.map((t, i) => (
            <button
              key={i}
              className="block w-full rounded-md border px-2 py-1 text-left"
              onClick={() => {
                setInbox((x) => x.filter((_, j) => j !== i));
                void handleText(t);
              }}
            >
              {t}
            </button>
          ))}
        </div>
      )}

      <form
        className="flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void handleText(text);
        }}
      >
        <input
          className="flex-1 rounded-md border px-3 py-2 text-sm"
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="ya yahan likhein: Ramesh ko 500 udhaar diya"
          aria-label="Entry text (editable)"
        />
        <button className="rounded-md border px-3 py-2 text-sm" disabled={parsing || !text.trim()}>
          {parsing ? "..." : "Samjho"}
        </button>
      </form>

      {intent && (
        <div className="space-y-2 rounded-md bg-muted p-3 text-sm">
          <div className="flex items-center justify-between">
            <div className="font-medium capitalize">{intent.intent.replace("_", " ")}</div>
            <div className="text-xs text-muted-foreground">{engine}</div>
          </div>
          <div>Amount: {intent.amount != null ? `₹${intent.amount}` : "—"}</div>
          {intent.party && <div>Party: {intent.party}</div>}
          {intent.date && <div>Date: {intent.date}</div>}
          {intent.items.map((i, k) => (
            <div key={k}>{i.name} {i.quantity ?? ""} {i.unit ?? ""}</div>
          ))}
          {question ? (
            <p className="font-medium text-amber-700">{question} (bolkar ya likhkar bataiye)</p>
          ) : intent.needs_confirmation ? (
            <p className="text-amber-700">Please check the details above before saving.</p>
          ) : null}
          <div className="flex gap-2">
            <button
              className="rounded-md bg-emerald-600 px-3 py-1 text-white disabled:opacity-50"
              disabled={!!question || intent.intent === "query" || intent.intent === "unknown"}
              onClick={() => {
                onConfirm(intent, text);
                setIntent(null);
                setQuestion(null);
                setText("");
              }}
            >
              Save entry
            </button>
            <button className="rounded-md border px-3 py-1" onClick={reset}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}
