import { createOpenAI, openai } from "@ai-sdk/openai";

/**
 * Chat model switch, per the blueprint ("Llama 3.3 / GPT-4o-mini"):
 *   LLM_PROVIDER=openai (default)  -> gpt-4o-mini       (needs OPENAI_API_KEY)
 *   LLM_PROVIDER=llama             -> llama-3.3-70b via any OpenAI-compatible host (Groq by default)
 *                                     LLM_API_KEY, optional LLM_BASE_URL / LLM_MODEL
 * Embeddings always use OpenAI (see rag.ts) so the pgvector dimension (1536) stays fixed.
 */
export function hasLLM(): boolean {
  return process.env.LLM_PROVIDER === "llama"
    ? !!(process.env.LLM_API_KEY ?? process.env.GROQ_API_KEY)
    : !!process.env.OPENAI_API_KEY;
}

export function getChatModel() {
  if (process.env.LLM_PROVIDER === "llama") {
    const provider = createOpenAI({
      baseURL: process.env.LLM_BASE_URL ?? "https://api.groq.com/openai/v1",
      apiKey: process.env.LLM_API_KEY ?? process.env.GROQ_API_KEY,
    });
    return provider(process.env.LLM_MODEL ?? "llama-3.3-70b-versatile");
  }
  return openai(process.env.LLM_MODEL ?? "gpt-4o-mini");
}
