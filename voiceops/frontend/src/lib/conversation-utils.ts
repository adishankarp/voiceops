import type { Conversation, ConversationInsights, ConversationSegment, TimelineEvent } from "@/lib/api-types";

export type InsightType =
  | "pain_point"
  | "objection"
  | "buying_signal"
  | "closing_attempt"
  | "key_moment";

export interface InsightDisplayItem {
  id: string;
  type: InsightType;
  label: string;
  description: string;
  timestamp: string;
  transcriptRef: string;
}

export interface TranscriptSegmentView {
  id: string;
  speaker: string;
  timestamp: string;
  text: string;
  seconds: number;
  endSeconds?: number;
}

export interface InsightCounts {
  pain_point: number;
  objection: number;
  buying_signal: number;
  closing_attempt: number;
  key_moment: number;
}

const emptyInsightCounts: InsightCounts = {
  pain_point: 0,
  objection: 0,
  buying_signal: 0,
  closing_attempt: 0,
  key_moment: 0,
};

export const insightTypeLabels: Record<InsightType, string> = {
  pain_point: "PAIN POINTS",
  objection: "OBJECTIONS",
  buying_signal: "BUYING SIGNALS",
  closing_attempt: "CLOSING ATTEMPTS",
  key_moment: "KEY MOMENTS",
};

export const insightTypeColors: Record<InsightType, string> = {
  pain_point: "text-destructive",
  objection: "text-warning",
  buying_signal: "text-success",
  closing_attempt: "text-primary",
  key_moment: "text-foreground",
};

export function formatSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return "0:00";
  }

  const wholeSeconds = Math.floor(seconds);
  const minutes = Math.floor(wholeSeconds / 60);
  const remainder = wholeSeconds % 60;
  return `${minutes}:${remainder.toString().padStart(2, "0")}`;
}

export function formatInsightTimestamp(seconds: number | null | undefined): string {
  return typeof seconds === "number" ? `${seconds.toFixed(1)}s` : "";
}

export function findSegmentIdForTimestamp(
  segments: TranscriptSegmentView[],
  timestamp: number,
): string | null {
  if (!segments.length || !Number.isFinite(timestamp)) {
    return null;
  }

  // Prefer segment that contains the timestamp (start <= t < end)
  const containing = segments.find(
    (segment) =>
      segment.seconds <= timestamp &&
      (segment.endSeconds == null || timestamp < segment.endSeconds),
  );
  if (containing) return containing.id;

  // Fallback: first segment that starts at or after timestamp, or last segment
  return segments.find((segment) => segment.seconds >= timestamp)?.id ?? segments[segments.length - 1]?.id ?? null;
}

export function normalizeSentimentScore(score: number | undefined): number {
  if (typeof score !== "number") {
    return 0;
  }

  return Math.round(score <= 1 ? score * 100 : score);
}

export function getConversationTitle(conversation: Pick<Conversation, "id" | "filename"> & Partial<Conversation>): string {
  return conversation.title || conversation.filename || conversation.id;
}

export function getConversationDateLabel(conversation: Partial<Conversation>): string {
  if (conversation.date) {
    return conversation.date;
  }

  return conversation.created_at ? new Date(conversation.created_at).toLocaleString() : "";
}

export function getConversationListDateLabel(conversation: Partial<Conversation>): string {
  if (conversation.date) {
    return conversation.date;
  }

  return conversation.created_at ? new Date(conversation.created_at).toLocaleDateString() : "";
}

export function getInsightCounts(insights: Partial<ConversationInsights> | undefined): InsightCounts {
  if (!insights) {
    return emptyInsightCounts;
  }

  return {
    pain_point: insights.pain_points?.length ?? 0,
    objection: insights.objections?.length ?? 0,
    buying_signal: insights.buying_signals?.length ?? 0,
    closing_attempt: insights.closing_attempts?.length ?? 0,
    key_moment: insights.key_moments?.length ?? 0,
  };
}

export function getAggregateInsightCounts(conversations: Conversation[]): InsightCounts {
  return conversations.reduce<InsightCounts>((counts, conversation) => {
    const conversationCounts = getInsightCounts(conversation.insights);
    return {
      pain_point: counts.pain_point + conversationCounts.pain_point,
      objection: counts.objection + conversationCounts.objection,
      buying_signal: counts.buying_signal + conversationCounts.buying_signal,
      closing_attempt: counts.closing_attempt + conversationCounts.closing_attempt,
      key_moment: counts.key_moment + conversationCounts.key_moment,
    };
  }, emptyInsightCounts);
}

export function getTranscriptSegments(conversation: Conversation): TranscriptSegmentView[] {
  return conversation.segments.map((segment: ConversationSegment, index) => {
    const seconds = typeof segment.start === "number" ? segment.start : 0;
    const endSeconds = typeof segment.end === "number" ? segment.end : undefined;
    return {
      id: segment.id ?? `seg-${index}`,
      speaker: segment.speaker ?? "SPEAKER",
      timestamp: segment.timestamp ?? formatSeconds(seconds),
      text: segment.text ?? "",
      seconds,
      endSeconds,
    };
  });
}

export function getTimelineEvents(conversation: Conversation): TimelineEvent[] {
  return conversation.timeline ?? [];
}

export function getDisplayInsights(insights: Partial<ConversationInsights> | undefined): Record<InsightType, InsightDisplayItem[]> {
  return {
    pain_point: (insights?.pain_points ?? []).map((item, index) => ({
      id: `pain_point-${index}`,
      type: "pain_point",
      label: item.text,
      description: item.text,
      timestamp: formatInsightTimestamp(item.timestamp),
      transcriptRef: "",
    })),
    objection: (insights?.objections ?? []).map((item, index) => ({
      id: `objection-${index}`,
      type: "objection",
      label: item.text,
      description: item.text,
      timestamp: formatInsightTimestamp(item.timestamp),
      transcriptRef: "",
    })),
    buying_signal: (insights?.buying_signals ?? []).map((item, index) => ({
      id: `buying_signal-${index}`,
      type: "buying_signal",
      label: item.text,
      description: item.text,
      timestamp: formatInsightTimestamp(item.timestamp),
      transcriptRef: "",
    })),
    closing_attempt: (insights?.closing_attempts ?? []).map((item, index) => ({
      id: `closing_attempt-${index}`,
      type: "closing_attempt",
      label: item.text,
      description: item.text,
      timestamp: formatInsightTimestamp(item.timestamp),
      transcriptRef: "",
    })),
    key_moment: (insights?.key_moments ?? []).map((item, index) => ({
      id: `key_moment-${index}`,
      type: "key_moment",
      label: item.summary,
      description: item.summary,
      timestamp: formatInsightTimestamp(item.timestamp),
      transcriptRef: "",
    })),
  };
}
