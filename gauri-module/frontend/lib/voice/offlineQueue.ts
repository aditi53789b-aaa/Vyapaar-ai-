"use client";
/**
 * Offline voice queue. When the device has no network, recorded clips are stored in IndexedDB (Dexie)
 * and transcribed automatically on reconnect. Uses its own database ("vs_voice_queue") so it never
 * collides with Arshpreet's ledger schema.
 */
import Dexie, { type Table } from "dexie";

export interface QueuedClip {
  id?: number;
  blob: Blob;
  mime: string;
  language: string;
  createdAt: number;
}

class VoiceQueueDB extends Dexie {
  clips!: Table<QueuedClip, number>;
  constructor() {
    super("vs_voice_queue");
    this.version(1).stores({ clips: "++id, createdAt" });
  }
}

let db: VoiceQueueDB | null = null;
const getDb = () => (db ??= new VoiceQueueDB());

const MAX_CLIPS = 50; // storage guard: drop oldest beyond this

export async function enqueueClip(blob: Blob, mime: string, language: string): Promise<void> {
  const d = getDb();
  await d.clips.add({ blob, mime, language, createdAt: Date.now() });
  const count = await d.clips.count();
  if (count > MAX_CLIPS) {
    const oldest = await d.clips.orderBy("createdAt").limit(count - MAX_CLIPS).primaryKeys();
    await d.clips.bulkDelete(oldest);
  }
}

export const queuedCount = () => getDb().clips.count();

let draining = false;

/** Process clips oldest-first. A clip is removed only when `handler` resolves true; stops on first failure. */
export async function drainQueue(handler: (clip: QueuedClip) => Promise<boolean>): Promise<number> {
  if (draining) return 0;
  draining = true;
  let done = 0;
  try {
    const clips = await getDb().clips.orderBy("createdAt").toArray();
    for (const clip of clips) {
      let ok = false;
      try {
        ok = await handler(clip);
      } catch {
        ok = false;
      }
      if (!ok) break;
      await getDb().clips.delete(clip.id!);
      done++;
    }
  } finally {
    draining = false;
  }
  return done;
}

/** Drain now (if online) and again whenever the browser reports it is back online. Returns an unsubscribe fn. */
export function autoDrainOnReconnect(handler: (clip: QueuedClip) => Promise<boolean>): () => void {
  const run = () => {
    if (navigator.onLine) void drainQueue(handler);
  };
  window.addEventListener("online", run);
  run();
  return () => window.removeEventListener("online", run);
}
