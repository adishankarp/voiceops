import { useEffect, useMemo, useState } from "react";
import Layout from "@/components/Layout";
import { getBackendStatus, getConversations, type ConversationSummary } from "@/lib/api";
import { cn } from "@/lib/utils";

const TRANSCRIPTION_MODEL = "whisper-base";
const INSIGHTS_MODEL = "gpt-4o-mini";
const EMBEDDING_MODEL = "text-embedding-3-small";

type PipelineHealth = "healthy" | "degraded" | "offline";

function getSentimentScore(conversation: ConversationSummary): number | null {
  const topLevel = (conversation as ConversationSummary & { sentiment_score?: number }).sentiment_score;
  const nested = conversation.insights?.sentiment_score;
  const raw = typeof topLevel === "number" ? topLevel : nested;

  if (typeof raw !== "number" || Number.isNaN(raw)) return null;
  return raw <= 1 ? raw * 100 : raw;
}

function computeAverageSentiment(conversations: ConversationSummary[]): number {
  const scores = conversations
    .map(getSentimentScore)
    .filter((score): score is number => score !== null);

  if (!scores.length) return 0;
  return Math.round(scores.reduce((sum, score) => sum + score, 0) / scores.length);
}

function getConversationStatus(conversation: ConversationSummary): string {
  return conversation.status || "complete";
}

function getPipelineHealth(
  backendOnline: boolean,
  conversations: ConversationSummary[],
): { status: PipelineHealth; detail: string } {
  if (!backendOnline) {
    return { status: "offline", detail: "Backend root endpoint is unreachable." };
  }

  const activeCount = conversations.filter((conversation) => getConversationStatus(conversation) !== "complete").length;

  if (activeCount > 0) {
    return {
      status: "degraded",
      detail: `${activeCount} conversation${activeCount === 1 ? "" : "s"} still processing.`,
    };
  }

  return {
    status: "healthy",
    detail: conversations.length
      ? "Backend reachable and all tracked conversations are complete."
      : "Backend reachable. No conversations have been analyzed yet.",
  };
}

function MetricCard({
  label,
  value,
  subtext,
}: {
  label: string;
  value: string;
  subtext?: string;
}) {
  return (
    <div className="border border-border bg-card p-4">
      <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-3 font-mono text-3xl font-bold text-foreground">{value}</p>
      {subtext ? <p className="mt-2 font-mono text-xs text-muted-foreground">{subtext}</p> : null}
    </div>
  );
}

const System = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [backendStatus, setBackendStatus] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        const [statusResponse, conversationsResponse] = await Promise.all([
          getBackendStatus(),
          getConversations(),
        ]);

        if (cancelled) return;

        setBackendStatus(statusResponse.status || null);
        setConversations(conversationsResponse || []);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError("Failed to load system status.");
          setBackendStatus(null);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const averageSentiment = useMemo(() => computeAverageSentiment(conversations), [conversations]);
  const pipelineHealth = useMemo(
    () => getPipelineHealth(Boolean(backendStatus), conversations),
    [backendStatus, conversations],
  );
  const completedCount = useMemo(
    () => conversations.filter((conversation) => getConversationStatus(conversation) === "complete").length,
    [conversations],
  );
  const inProgressCount = useMemo(
    () => conversations.filter((conversation) => getConversationStatus(conversation) !== "complete").length,
    [conversations],
  );

  return (
    <Layout>
      <div className="mb-6">
        <h1 className="font-mono text-2xl font-bold tracking-wider">SYSTEM</h1>
        <p className="mt-1 font-mono text-xs text-muted-foreground">
          {loading ? "LOADING SYSTEM STATUS..." : "BACKEND AND PIPELINE OVERVIEW"}
        </p>
        {error ? <p className="mt-1 font-mono text-xs text-destructive">{error}</p> : null}
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricCard
          label="Total Conversations"
          value={loading ? "..." : conversations.length.toString()}
          subtext="Records returned by /conversations"
        />
        <MetricCard
          label="Average Sentiment"
          value={loading ? "..." : `${averageSentiment}/100`}
          subtext="Derived from stored sentiment scores"
        />
        <div className="border border-border bg-card p-4">
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Pipeline Health</p>
          <div className="mt-3 flex items-center gap-3">
            <div
              className={cn(
                "h-3 w-3 rounded-full",
                pipelineHealth.status === "healthy" && "bg-[hsl(var(--success))]",
                pipelineHealth.status === "degraded" && "bg-[hsl(var(--warning))]",
                pipelineHealth.status === "offline" && "bg-destructive",
              )}
            />
            <p className="font-mono text-2xl font-bold uppercase text-foreground">
              {loading ? "..." : pipelineHealth.status}
            </p>
          </div>
          <p className="mt-2 font-mono text-xs text-muted-foreground">
            {loading ? "Checking backend and conversation state..." : pipelineHealth.detail}
          </p>
        </div>
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <div className="border border-border bg-card p-4">
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Configured Models</p>
          <div className="mt-4 space-y-3">
            <div className="flex items-center justify-between gap-4 border border-border bg-background/40 px-3 py-3">
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Transcription</span>
              <span className="font-mono text-sm text-foreground">{TRANSCRIPTION_MODEL}</span>
            </div>
            <div className="flex items-center justify-between gap-4 border border-border bg-background/40 px-3 py-3">
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Insights</span>
              <span className="font-mono text-sm text-foreground">{INSIGHTS_MODEL}</span>
            </div>
            <div className="flex items-center justify-between gap-4 border border-border bg-background/40 px-3 py-3">
              <span className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Embeddings</span>
              <span className="font-mono text-sm text-foreground">{EMBEDDING_MODEL}</span>
            </div>
          </div>
        </div>

        <div className="border border-border bg-card p-4">
          <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">Backend Status</p>
          <p className="mt-3 font-mono text-lg text-foreground">
            {loading ? "..." : backendStatus || "Unavailable"}
          </p>
          <p className="mt-4 font-mono text-xs uppercase tracking-widest text-muted-foreground">
            Conversation Status Mix
          </p>
          <div className="mt-3 space-y-2 font-mono text-xs text-foreground">
            <div className="flex items-center justify-between border border-border px-3 py-2">
              <span>complete</span>
              <span>{loading ? "..." : completedCount}</span>
            </div>
            <div className="flex items-center justify-between border border-border px-3 py-2">
              <span>in_progress</span>
              <span>{loading ? "..." : inProgressCount}</span>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default System;
