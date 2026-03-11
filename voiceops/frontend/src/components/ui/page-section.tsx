import * as React from "react";

import { cn } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

interface PageHeaderProps {
  title: string;
  description: string;
  meta?: string;
  children?: React.ReactNode;
  className?: string;
}

interface SectionHeadingProps {
  title: string;
  description?: string;
  className?: string;
}

interface SurfaceCardProps {
  title?: string;
  description?: string;
  children: React.ReactNode;
  contentClassName?: string;
  className?: string;
}

interface EmptyStateProps {
  title: string;
  description: string;
  className?: string;
}

interface LoadingStateProps {
  title?: string;
  rows?: number;
  className?: string;
}

export function PageHeader({
  title,
  description,
  meta,
  children,
  className,
}: PageHeaderProps) {
  return (
    <div
      className={cn(
        "flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between",
        className,
      )}
    >
      <div className="space-y-1.5">
        <h1 className="font-display text-3xl font-bold text-foreground sm:text-4xl">{title}</h1>
        <p className="text-sm text-muted-foreground">{description}</p>
        {meta ? <p className="text-xs text-muted-foreground">{meta}</p> : null}
      </div>
      {children ? <div className="shrink-0">{children}</div> : null}
    </div>
  );
}

export function SectionHeading({
  title,
  description,
  className,
}: SectionHeadingProps) {
  return (
    <div className={cn("space-y-1", className)}>
      <p className="label-mono text-xs font-medium uppercase tracking-wider text-muted-foreground">{title}</p>
      {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
    </div>
  );
}

export function SurfaceCard({
  title,
  description,
  children,
  contentClassName,
  className,
}: SurfaceCardProps) {
  return (
    <Card className={cn("border-border bg-card shadow-none", className)}>
      {title || description ? (
        <CardHeader className="space-y-1 border-b border-border px-4 py-3 sm:px-5">
          {title ? <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">{title}</p> : null}
          {description ? <p className="text-sm text-muted-foreground">{description}</p> : null}
        </CardHeader>
      ) : null}
      <CardContent className={cn("px-4 py-4 sm:px-5", contentClassName)}>
        {children}
      </CardContent>
    </Card>
  );
}

export function EmptyState({
  title,
  description,
  className,
}: EmptyStateProps) {
  return (
    <div className={cn("flex min-h-[180px] items-center justify-center border border-dashed border-border bg-card/40 px-6 py-10 text-center", className)}>
      <div className="max-w-sm space-y-2">
        <p className="font-mono text-xs uppercase tracking-widest text-muted-foreground">{title}</p>
        <p className="text-sm leading-relaxed text-muted-foreground">{description}</p>
      </div>
    </div>
  );
}

export function LoadingState({
  title,
  rows = 3,
  className,
}: LoadingStateProps) {
  return (
    <SurfaceCard title={title} className={className} contentClassName="space-y-3">
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="space-y-2">
          <Skeleton className="h-3 w-28 bg-muted" />
          <Skeleton className="h-10 w-full bg-muted" />
        </div>
      ))}
    </SurfaceCard>
  );
}
