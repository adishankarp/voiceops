import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";

import InsightCard from "@/components/InsightCard";
import Layout from "@/components/Layout";
import DeleteConversationButton from "@/components/DeleteConversationButton";
import { EmptyState, LoadingState, PageHeader, SectionHeading, SurfaceCard } from "@/components/ui/page-section";
import { cn } from "@/lib/utils";
import { getConversations, getPatterns, type ConversationSummary } from "@/lib/api";
import type { Pattern } from "@/lib/api-types";
import {
  getAggregateInsightCounts,
  getConversationListDateLabel,
  getConversationTitle,
  getInsightCounts,
  normalizeSentimentScore,
} from "@/lib/conversation-utils";

function computeAverageSentiment(convs: ConversationSummary[]): number {
  const scored = convs
    .map((conversation) => {
      const rawScore = conversation.insights?.sentiment_score;
      if (typeof rawScore !== "number") {
        return null;
      }

      return normalizeSentimentScore(rawScore);
    })
    .filter((score): score is number => score !== null);

  if (!scored.length) return 0;
  return Math.round(scored.reduce((sum, score) => sum + score, 0) / scored.length);
}

const Dashboard = () => {
  const navigate = useNavigate();
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        const data = await getConversations();
        if (!cancelled) setConversations(data || []);
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError("Failed to load conversations.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getPatterns();
        if (!cancelled) setPatterns(Array.isArray(data) ? data : []);
      } catch {
        if (!cancelled) setPatterns([]);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const counts = useMemo(() => getAggregateInsightCounts(conversations), [conversations]);
  const avgSentiment = useMemo(() => computeAverageSentiment(conversations), [conversations]);

  return (
    <Layout>
      <PageHeader
        title="DASHBOARD"
        description="Conversation analysis overview"
        meta={loading ? "LOADING CONVERSATIONS..." : `${conversations.length} CONVERSATIONS ANALYZED`}
      >
        {error ? <p className="font-mono text-xs text-destructive">{error}</p> : null}
      </PageHeader>

      <div className="mt-6 grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* LEFT: Recent conversations */}
        <div className="space-y-3 lg:col-span-2">
          <SectionHeading title="RECENT CONVERSATIONS" />
          {loading ? (
            <LoadingState rows={4} />
          ) : conversations.length === 0 ? (
            <EmptyState
              title="NO CONVERSATIONS"
              description="Upload audio files to start building your dashboard view."
            />
          ) : (
            <div className="space-y-2">
              {conversations.map((conv) => {
                const insightCounts = getInsightCounts(conv.insights);
                const status = (conv.status || "").toString().toLowerCase();
                const statusLabel =
                  status === "complete" ? "COMPLETE" : status === "failed" ? "FAILED" : "PROCESSING";

                return (
                  <motion.div
                    key={conv.id}
                    onClick={() => navigate(`/conversation/${conv.id}`)}
                    whileHover={{ y: -2 }}
                    className="cursor-pointer border border-border bg-card px-4 py-3 text-left transition-colors hover:bg-secondary"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="truncate text-sm font-semibold text-foreground">
                          {getConversationTitle(conv)}
                        </p>
                        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
                          <span className="font-mono text-xs text-muted-foreground">
                            {getConversationListDateLabel(conv)}
                          </span>
                          {conv.duration ? (
                            <span className="font-mono text-xs text-muted-foreground">{conv.duration}</span>
                          ) : null}
                        </div>
                      </div>
                      <div className="flex items-center gap-3">
                        <div
                          className={cn(
                            "inline-block border px-2 py-0.5 font-mono text-xs",
                            status === "complete"
                              ? "border-primary/30 text-primary"
                              : status === "failed"
                              ? "border-destructive/40 text-destructive"
                              : "border-muted text-muted-foreground",
                          )}
                        >
                          {statusLabel}
                        </div>
                        <DeleteConversationButton
                          id={conv.id}
                          onDeleted={() =>
                            setConversations((prev) => prev.filter((c) => c.id !== conv.id))
                          }
                        />
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 font-mono text-xs text-muted-foreground">
                      <span>{insightCounts.objection} obj</span>
                      <span>{insightCounts.pain_point} pain</span>
                      <span>{insightCounts.buying_signal} sig</span>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          )}
        </div>

        {/* RIGHT: Patterns + Aggregate insights */}
        <div className="space-y-4 lg:col-span-1">
          <SectionHeading title="PATTERNS" />
          {patterns.length === 0 ? (
            <EmptyState
              title="NO PATTERNS DETECTED"
              description="Upload more conversations to detect cross-conversation patterns."
            />
          ) : (
            <SurfaceCard title="TOP PATTERNS">
              <ul className="space-y-3">
                {patterns.map((p, i) => (
                  <li key={i}>
                    <p className="font-mono text-xs font-medium uppercase tracking-wider text-primary">
                      {p.label}
                    </p>
                    {p.description ? (
                      <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{p.description}</p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </SurfaceCard>
          )}

          <SectionHeading title="AGGREGATE INSIGHTS" />
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <InsightCard label="Pain Points" count={counts.pain_point} />
            <InsightCard label="Objections" count={counts.objection} />
            <InsightCard label="Buying Signals" count={counts.buying_signal} />
            <InsightCard label="Closing Attempts" count={counts.closing_attempt} />
            <InsightCard label="Key Moments" count={counts.key_moment} />
            <SurfaceCard>
              <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">AVG SENTIMENT</p>
              <p className="mt-3 font-mono text-3xl font-bold text-foreground">
                {avgSentiment}
                <span className="text-lg text-muted-foreground">/100</span>
              </p>
              <div className="mt-3 h-1 w-full bg-muted">
                <div className="h-full bg-primary transition-all" style={{ width: `${avgSentiment}%` }} />
              </div>
            </SurfaceCard>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default Dashboard;
