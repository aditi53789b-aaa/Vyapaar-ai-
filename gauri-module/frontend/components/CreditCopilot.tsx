"use client";
import { useState } from "react";
import type { MerchantProfile } from "@/lib/ai/readiness";
import type { LedgerTxn } from "@/lib/ai/ledgerStats";

interface Props {
  /** Pass EITHER explicit metrics ... */
  profile?: MerchantProfile;
  /** ... OR the ledger rows (metrics are derived for you), plus the merchant's self-declared flags. */
  transactions?: LedgerTxn[];
  flags?: { businessType?: string; isStreetVendor?: boolean; hasUdyam?: boolean; hasBankAccount?: boolean; isNewBusiness?: boolean };
  language?: string;
}

interface Msg { role: "user" | "assistant"; content: string }
interface Source { name: string; url: string | null }

/** Streaming, multi-turn RAG chat for the Credit Readiness Copilot. */
export default function CreditCopilot({ profile, transactions, flags, language = "hinglish" }: Props) {
  const [question, setQuestion] = useState("Mujhe kaun si sarkari loan scheme mil sakti hai?");
  const [messages, setMessages] = useState<Msg[]>([]);
  const [score, setScore] = useState<{ score: string; band: string } | null>(null);
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function ask() {
    const q = question.trim();
    if (!q || loading) return;
    setLoading(true);
    setError(null);
    const history = messages.slice(-6);
    setMessages((m) => [...m, { role: "user", content: q }, { role: "assistant", content: "" }]);
    setQuestion("");
    try {
      const res = await fetch("/api/copilot", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, language, profile, transactions, flags, history }),
      });
      if (!res.ok || !res.body) throw new Error("Copilot unavailable. Please try again.");
      setScore({ score: res.headers.get("x-readiness-score") ?? "", band: res.headers.get("x-readiness-band") ?? "" });
      try {
        setSources(JSON.parse(decodeURIComponent(res.headers.get("x-sources") ?? "[]")));
      } catch {
        setSources([]);
      }
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = dec.decode(value, { stream: true });
        setMessages((m) => {
          const copy = m.slice();
          copy[copy.length - 1] = { role: "assistant", content: copy[copy.length - 1].content + chunk };
          return copy;
        });
      }
    } catch (e) {
      setError((e as Error).message);
      setMessages((m) => m.slice(0, -1)); // drop the empty assistant bubble
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border p-4">
      {score && (
        <div className="text-sm">
          Credit readiness: <b>{score.score}/100</b> ({score.band})
        </div>
      )}
      <div className="space-y-2">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`whitespace-pre-wrap rounded-md p-2 text-sm leading-relaxed ${m.role === "user" ? "bg-muted" : ""}`}
          >
            {m.content || (loading && i === messages.length - 1 ? "..." : "")}
          </div>
        ))}
      </div>
      {sources.length > 0 && (
        <div className="text-xs">
          Sources:{" "}
          {sources.map((s, i) => (
            <span key={i}>
              {i > 0 && " · "}
              {s.url ? <a className="underline" href={s.url} target="_blank" rel="noreferrer">{s.name}</a> : s.name}
            </span>
          ))}
        </div>
      )}
      {error && <p className="text-sm text-red-600">{error}</p>}
      <div className="flex gap-2">
        <input
          className="flex-1 rounded-md border px-3 py-2 text-sm"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && ask()}
          placeholder="Apna sawaal poochhein"
        />
        <button className="rounded-md bg-emerald-600 px-4 py-2 text-white disabled:opacity-50" onClick={ask} disabled={loading}>
          {loading ? "..." : "Poochho"}
        </button>
      </div>
      <p className="text-xs text-muted-foreground">
        Guidance only, not a loan offer. Confirm eligibility and terms with the bank or the official scheme site.
      </p>
    </div>
  );
}
