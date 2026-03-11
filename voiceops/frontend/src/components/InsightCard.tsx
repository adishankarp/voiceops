import { cn } from "@/lib/utils";
import { SurfaceCard } from "@/components/ui/page-section";

interface InsightCardProps {
  label: string;
  count: number;
  className?: string;
}

const InsightCard = ({ label, count, className }: InsightCardProps) => {
  return (
    <SurfaceCard className={cn("", className)}>
      <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">{label}</p>
      <p className="mt-3 font-mono text-3xl font-bold text-foreground">{count}</p>
    </SurfaceCard>
  );
};

export default InsightCard;
