import { cn } from "@/lib/utils";
import type { ProcessingStatus as ProcessingStatusType } from "@/lib/api-types";

const STEPS: { key: "uploaded" | "transcribing" | "extracting" | "complete"; label: string }[] = [
  { key: "uploaded", label: "UPLOADED" },
  { key: "transcribing", label: "TRANSCRIBING" },
  { key: "extracting", label: "EXTRACTING INSIGHTS" },
  { key: "complete", label: "COMPLETE" },
];

function statusToCurrentIndex(status: ProcessingStatusType, failedStage?: string | null): number {
  if (status === "failed") {
    if (failedStage === "transcription") return 1;
    return 2; // insights, summary, or embedding
  }
  switch (status) {
    case "uploaded":
      return 0;
    case "transcribing":
      return 1;
    case "extracting":
      return 2;
    case "complete":
      return 3;
    default:
      return 0;
  }
}

interface PipelineStepsProps {
  status: ProcessingStatusType;
  variant?: "horizontal" | "vertical";
  /** When status is "failed", which stage failed (e.g. from conversation.error.stage) */
  failedStage?: string | null;
}

const PipelineSteps = ({ status, variant = "vertical", failedStage }: PipelineStepsProps) => {
  const currentIndex = statusToCurrentIndex(status, failedStage);
  const isFailed = status === "failed";

  return (
    <div
      className={cn(
        "flex gap-1",
        variant === "vertical" ? "flex-col gap-3" : "flex-wrap items-center gap-2",
      )}
    >
      {STEPS.map((step, index) => {
        const isCompleted = index < currentIndex || (index === 3 && status === "complete");
        const isCurrent = index === currentIndex;
        const isStepFailed = isFailed && isCurrent;

        let icon: string;
        let iconClass: string;
        if (isStepFailed) {
          icon = "✕";
          iconClass = "text-destructive";
        } else if (isCompleted) {
          icon = "✓";
          iconClass = "text-primary";
        } else if (isCurrent) {
          icon = "⚡";
          iconClass = "text-primary";
        } else {
          icon = "•";
          iconClass = "text-muted-foreground";
        }

        return (
          <div
            key={step.key}
            className={cn(
              "flex items-center gap-2 transition-colors",
              variant === "vertical" && "flex-row",
            )}
          >
            <span
              className={cn(
                "flex h-5 w-5 shrink-0 items-center justify-center font-mono text-sm",
                iconClass,
                isCurrent && !isStepFailed && "animate-pulse",
              )}
              aria-hidden
            >
              {icon}
            </span>
            <span
              className={cn(
                "font-mono text-xs tracking-wider",
                isCompleted && !isStepFailed && "text-foreground",
                isCurrent && !isStepFailed && "text-primary",
                isStepFailed && "text-destructive",
                !isCompleted && !isCurrent && "text-muted-foreground",
              )}
            >
              {step.label}
            </span>
            {variant === "horizontal" && index < STEPS.length - 1 && (
              <span className="font-mono text-xs text-muted-foreground">→</span>
            )}
          </div>
        );
      })}
    </div>
  );
};

export default PipelineSteps;
