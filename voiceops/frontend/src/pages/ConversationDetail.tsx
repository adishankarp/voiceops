import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import Layout from "@/components/Layout";
import PipelineSteps from "@/components/PipelineSteps";
import Timeline from "@/components/Timeline";
import TranscriptViewer from "@/components/TranscriptViewer";
import { EmptyState, LoadingState, PageHeader, SectionHeading, SurfaceCard } from "@/components/ui/page-section";
import { getConversation } from "@/lib/api";
import type { Conversation } from "@/lib/api-types";
import {
  findSegmentIdForTimestamp,
  getConversationDateLabel,
  getConversationTitle,
  getDisplayInsights,
  getTimelineEvents,
  getTranscriptSegments,
  insightTypeColors,
  insightTypeLabels,
  normalizeSentimentScore,
} from "@/lib/conversation-utils";
import { cn } from "@/lib/utils";

const ConversationDetail = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [highlightedSegment, setHighlightedSegment] = useState<string | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;

    (async () => {
      try {
        setLoading(true);
        const data = await getConversation(id);
        if (!cancelled) {
          setConversation(data);
        }
      } catch (err) {
        if (!cancelled) {
          console.error(err);
          setError("Failed to load conversation.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [id]);

  const conversationDetails = conversation;
  const groupedInsights = useMemo(
    () => (conversationDetails ? getDisplayInsights(conversationDetails.insights) : {}),
    [conversationDetails],
  );
  const segments = useMemo(
    () => (conversationDetails ? getTranscriptSegments(conversationDetails) : []),
    [conversationDetails],
  );
  const timelineEvents = useMemo(
    () => (conversationDetails ? getTimelineEvents(conversationDetails) : []),
    [conversationDetails],
  );
  const sentimentScore = useMemo(
    () => normalizeSentimentScore(conversationDetails?.insights?.sentiment_score),
    [conversationDetails],
  );
  const highlightSegmentAtTimestamp = (timestamp: number) => {
    const segmentId = findSegmentIdForTimestamp(segments, timestamp);
    if (segmentId) {
      setHighlightedSegment(segmentId);
    }
  };

  if (loading) {
    return (
      <Layout>
        <PageHeader title="CONVERSATION" description="Detailed transcript and insight review" />
        <div className="grid gap-6 xl:grid-cols-[minmax(300px,380px)_minmax(0,1fr)]">
          <LoadingState rows={4} />
          <LoadingState title="TRANSCRIPT" rows={6} />
        </div>
      </Layout>
    );
  }

  if (!conversationDetails || error) {
    return (
      <Layout>
        <PageHeader title="CONVERSATION" description="Detailed transcript and insight review" />
        <EmptyState
          title="CONVERSATION NOT FOUND"
          description="The requested conversation could not be loaded."
        />
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="space-y-4">
        <button
          onClick={() => navigate("/")}
          className="font-mono text-xs text-muted-foreground transition-colors hover:text-foreground"
        >
          ← DASHBOARD
        </button>

        <PageHeader
          title={getConversationTitle(conversationDetails)}
          description="Detailed transcript and insight review"
          meta={getConversationDateLabel(conversationDetails) || undefined}
        />
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(300px,380px)_minmax(0,1fr)]">
        <div className="space-y-4">
          <SurfaceCard title="AI SUMMARY">
            {conversationDetails.summary?.trim() ? (
              <p className="text-sm leading-relaxed text-foreground">
                {conversationDetails.summary}
              </p>
            ) : (
              <p className="text-sm text-muted-foreground">No summary available.</p>
            )}
          </SurfaceCard>

          <SurfaceCard title="CONVERSATION DETAILS">
            <div className="space-y-2 font-mono text-xs">
              <p>
                <span className="text-muted-foreground">FILE: </span>
                {conversationDetails.filename}
              </p>
              <p>
                <span className="text-muted-foreground">STATUS: </span>
                {conversationDetails.status.toUpperCase()}
              </p>
              {getConversationDateLabel(conversationDetails) ? (
                <p>
                  <span className="text-muted-foreground">DATE: </span>
                  {getConversationDateLabel(conversationDetails)}
                </p>
              ) : null}
              {(conversationDetails.participants ?? []).map((participant, index) => (
                <p key={`${participant}-${index}`}>
                  <span className="text-muted-foreground">PARTICIPANT: </span>
                  {participant}
                </p>
              ))}
            </div>
          </SurfaceCard>

          <SurfaceCard title="PROCESSING STATUS" contentClassName="space-y-4">
            <PipelineSteps
              status={conversationDetails.status}
              variant="vertical"
              failedStage={conversationDetails.error?.stage}
            />
          </SurfaceCard>

          <SurfaceCard title="SENTIMENT SCORE">
            <p className="font-mono text-3xl font-bold text-foreground">
              {sentimentScore}
              <span className="text-sm text-muted-foreground">/100</span>
            </p>
            <div className="mt-3 h-1.5 w-full bg-muted">
              <div
                className={cn(
                  "h-full transition-all",
                  sentimentScore >= 60 ? "bg-success" : sentimentScore >= 40 ? "bg-warning" : "bg-destructive",
                )}
                style={{ width: `${sentimentScore}%` }}
              />
            </div>
          </SurfaceCard>

          <div className="space-y-3">
            <SectionHeading title="INSIGHTS" />
            {Object.entries(groupedInsights).every(([, insights]) => insights.length === 0) ? (
              <EmptyState
                title="NO INSIGHTS"
                description="Insight extraction results will appear here when available."
              />
            ) : (
              Object.entries(groupedInsights).map(([type, insights]) => (
                <SurfaceCard key={type}>
                  <p
                    className={cn(
                      "font-mono text-xs uppercase tracking-widest",
                      insightTypeColors[type] || "text-muted-foreground",
                    )}
                  >
                    {insightTypeLabels[type] || type}
                  </p>
                  <div className="mt-3 space-y-2">
                    {insights.map((insight) => (
                      <button
                        key={insight.id}
                        onClick={() => {
                          if (!insight.timestamp) return;
                          const timestampSeconds = Number.parseFloat(insight.timestamp);
                          highlightSegmentAtTimestamp(timestampSeconds);
                        }}
                        className={cn(
                          "block w-full border border-transparent px-3 py-2 text-left transition-colors hover:bg-secondary",
                        )}
                      >
                        <p className="font-mono text-xs font-medium text-foreground">{insight.label}</p>
                        <p className="mt-1 text-sm leading-relaxed text-muted-foreground">{insight.description}</p>
                        <p className="mt-1 font-mono text-xs text-primary">{insight.timestamp}</p>
                      </button>
                    ))}
                  </div>
                </SurfaceCard>
              ))
            )}
          </div>
        </div>

        <div className="space-y-4">
          <Timeline
            events={timelineEvents}
            onJump={highlightSegmentAtTimestamp}
          />
          <SurfaceCard title="TRANSCRIPT" contentClassName="p-0">
            <TranscriptViewer segments={segments} highlightedId={highlightedSegment} />
          </SurfaceCard>
        </div>
      </div>
    </Layout>
  );
};

export default ConversationDetail;
