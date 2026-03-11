import { cn } from "@/lib/utils";
import { EmptyState, SurfaceCard } from "@/components/ui/page-section";
import type { TimelineEvent } from "@/lib/api-types";
import { formatSeconds } from "@/lib/conversation-utils";

interface TimelineProps {
  events: TimelineEvent[];
  onJump: (timestamp: number) => void;
}

const Timeline = ({ events, onJump }: TimelineProps) => {
  if (events.length === 0) {
    return (
      <SurfaceCard title="TIMELINE" contentClassName="pt-0">
        <EmptyState
          title="NO TIMELINE EVENTS"
          description="Key moments will appear here when the conversation includes timeline annotations."
          className="min-h-[160px] border-0 bg-transparent px-0 pb-0"
        />
      </SurfaceCard>
    );
  }

  const sorted = [...events].sort((a, b) => a.timestamp - b.timestamp);

  return (
    <SurfaceCard title="TIMELINE" contentClassName="space-y-1">
      {sorted.map((event, idx) => (
        <button
          key={`${event.type}-${idx}-${event.timestamp}`}
          onClick={() => onJump(event.timestamp)}
          className={cn(
            "w-full border border-transparent px-3 py-2 text-left transition-colors",
            "hover:border-primary/40 hover:bg-secondary",
          )}
        >
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span className="font-mono text-xs font-medium text-primary">
              [{formatSeconds(event.timestamp)}]
            </span>
            <span className="font-mono text-[10px] uppercase tracking-widest text-muted-foreground">
              {event.type.replace("_", " ")}
            </span>
          </div>
          <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-foreground">
            {event.label}
          </p>
        </button>
      ))}
    </SurfaceCard>
  );
};

export default Timeline;
