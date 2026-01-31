import { apiFetch } from "./client";

export type AiRole = "system" | "user" | "assistant";

export interface AiMessage {
  role: AiRole;
  content: string;
}

export interface AiConfig {
  provider: "ollama" | "backend";
  baseUrl: string;
  model: string;
}

export function getAiConfig(): AiConfig {
  const providerRaw = (import.meta.env.VITE_LLM_PROVIDER || "backend").toLowerCase();
  const provider: AiConfig["provider"] =
    providerRaw === "backend" ? "backend" : "ollama";

  if (provider === "backend") {
    return {
      provider,
      baseUrl: import.meta.env.VITE_LLM_BASE_URL || "/api/ai/chat/",
      model: import.meta.env.VITE_LLM_MODEL || "default",
    };
  }

  return {
    provider,
    baseUrl: import.meta.env.VITE_OLLAMA_URL || "http://localhost:11434",
    model: import.meta.env.VITE_OLLAMA_MODEL || "llama3.1",
  };
}

export async function sendAiChat(messages: AiMessage[]) {
  const config = getAiConfig();

  if (config.provider === "ollama") {
    const response = await fetch(`${config.baseUrl}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: config.model,
        messages,
        stream: false,
      }),
    });

    if (!response.ok) {
      throw new Error("Unable to reach Ollama. Is it running?");
    }

    const data = (await response.json()) as {
      message?: { content?: string };
      response?: string;
    };
    return data.message?.content || data.response || "";
  }

  const data = await apiFetch<{ message?: string; content?: string; output?: string }>(
    config.baseUrl,
    {
      method: "POST",
      body: JSON.stringify({ messages }),
    }
  );

  return data?.message || data?.content || data?.output || "";
}
