import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EmptyState } from "@/components/ui/page-section";
import type { TranscriptSegmentView } from "@/lib/conversation-utils";

interface TranscriptViewerProps {
  segments: TranscriptSegmentView[];
  highlightedId?: string | null;
}

const TranscriptViewer = ({ segments, highlightedId }: TranscriptViewerProps) => {
  const refs = useRef<Record<string, HTMLDivElement | null>>({});

  useEffect(() => {
    if (!highlightedId) return;
    // Defer scroll so refs are attached and ScrollArea viewport is ready
    const id = requestAnimationFrame(() => {
      const el = refs.current[highlightedId];
      if (el) {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    });
    return () => cancelAnimationFrame(id);
  }, [highlightedId]);

  return (
    <ScrollArea className="h-[calc(100vh-260px)] min-h-[360px]">
      {segments.length === 0 ? (
        <EmptyState
          title="NO TRANSCRIPT"
          description="Transcript segments will appear here once transcription data is available."
          className="m-4 min-h-[260px]"
        />
      ) : (
        <div className="space-y-3 p-4 sm:p-5">
          {segments.map((segment) => {
            const isHighlighted = segment.id === highlightedId;
            return (
              <div
                key={segment.id}
                ref={(el) => { refs.current[segment.id] = el; }}
                className={cn(
                  "border-l-2 px-4 py-3 transition-colors",
                  isHighlighted
                    ? "border-l-primary bg-primary/10"
                    : "border-l-transparent hover:border-l-muted-foreground/30 hover:bg-secondary/40",
                )}
              >
                <div className="mb-2 flex flex-wrap items-center gap-x-3 gap-y-1">
                  <span className="font-mono text-xs font-medium text-primary">{segment.timestamp}</span>
                  <span className="font-mono text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    {segment.speaker}
                  </span>
                </div>
                <p className={cn("text-sm leading-relaxed", isHighlighted ? "text-primary" : "text-foreground")}>
                  {segment.text}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </ScrollArea>
  );
};

export default TranscriptViewer;
