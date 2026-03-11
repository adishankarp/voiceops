import type {
  BackendStatusResponse,
  ChatResponse,
  Conversation,
  Pattern,
  SearchResult,
  UploadResponse,
} from "@/lib/api-types";

const BASE_URL = (import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Request failed with status ${res.status}`);
  }

  return (await res.json()) as T;
}

export type ConversationSummary = Conversation;
export type { ChatResponse, Conversation, Pattern, SearchResult, UploadResponse } from "@/lib/api-types";

export async function getConversations(): Promise<ConversationSummary[]> {
  return request<ConversationSummary[]>("/conversations");
}

export async function getPatterns(): Promise<Pattern[]> {
  return request<Pattern[]>("/patterns");
}

export async function getBackendStatus(): Promise<BackendStatusResponse> {
  return request<BackendStatusResponse>("/");
}

export async function getConversation(id: string): Promise<Conversation> {
  return request<Conversation>(`/conversations/${encodeURIComponent(id)}`);
}

export async function uploadConversation(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${BASE_URL}/conversations/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Upload failed with status ${res.status}`);
  }

  return (await res.json()) as UploadResponse;
}

export async function searchConversations(query: string): Promise<SearchResult[]> {
  const q = encodeURIComponent(query);
  return request<SearchResult[]>(`/search?query=${q}`);
}

export async function chat(question: string, conversationId?: string): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      question,
      conversation_id: conversationId ?? null,
    }),
  });
}

export async function deleteConversation(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/conversations/${encodeURIComponent(id)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `Delete failed with status ${res.status}`);
  }
}
