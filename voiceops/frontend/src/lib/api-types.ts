export type ProcessingStatus = "uploaded" | "transcribing" | "extracting" | "complete" | "failed";

export interface ConversationSegment {
  id?: string;
  start: number;
  end: number;
  speaker?: string;
  timestamp?: string;
  text: string;
}

export interface InsightItem {
  text: string;
  timestamp: number | null;
}

export interface KeyMoment {
  timestamp: number;
  summary: string;
}

export interface ConversationInsights {
  pain_points: InsightItem[];
  objections: InsightItem[];
  buying_signals: InsightItem[];
  closing_attempts: InsightItem[];
  key_moments: KeyMoment[];
  sentiment_score: number | null;
}

export interface TimelineEvent {
  type: string;
  timestamp: number;
  label: string;
}

export interface ConversationError {
  stage: string;
  message: string;
}

export interface Conversation {
  id: string;
  filename: string;
  status: ProcessingStatus;
  title?: string;
  date?: string;
  duration?: string;
  participants?: string[];
  transcript: string;
  segments: ConversationSegment[];
  insights: Partial<ConversationInsights>;
  summary?: string | null;
  created_at: string | null;
  timeline?: TimelineEvent[];
  embedding?: number[];
  error?: ConversationError | null;
}

export interface SearchResult {
  conversation_id: string;
  filename: string;
  snippet: string;
  score: number;
}

export interface ChatSource {
  conversation_id: string;
  filename: string;
}

export interface ChatResponse {
  answer: string;
  sources: ChatSource[];
}

export interface UploadResponse {
  conversation_id: string;
  status: ProcessingStatus;
}

export interface BackendStatusResponse {
  status: string;
}

export interface Pattern {
  label: string;
  description?: string;
}
