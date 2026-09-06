import type { ReactNode } from 'react';
import { AlertTriangle, Inbox, RefreshCw, type LucideIcon } from 'lucide-react';
import { ApiError } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/table';
import { cn } from '@/lib/format';

export function PageHeader({ title, description, actions, eyebrow, className }: { title: ReactNode; description?: ReactNode; actions?: ReactNode; eyebrow?: ReactNode; className?: string }) {
  return (
    <header className={cn('mb-6 flex flex-wrap items-end justify-between gap-4', className)}>
      <div className="min-w-0">
        {eyebrow && <p className="mb-1 text-sm font-semibold uppercase tracking-wide text-muted-foreground">{eyebrow}</p>}
        <h1 className="font-heading text-3xl font-semibold leading-tight text-foreground md:text-4xl">{title}</h1>
        {description && <p className="mt-2 max-w-prose text-base text-muted-foreground">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className,
}: {
  icon?: LucideIcon;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn('flex flex-col items-center justify-center rounded-lg border border-dashed px-6 py-14 text-center', className)}>
      <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Icon className="h-6 w-6" aria-hidden />
      </div>
      <h2 className="text-lg font-semibold">{title}</h2>
      {description && <p className="mt-1 max-w-md text-sm text-muted-foreground">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry, title = 'Something went wrong', className }: { error: unknown; onRetry?: () => void; title?: string; className?: string }) {
  const apiErr = error instanceof ApiError ? error : null;
  const message = apiErr ? apiErr.message : error instanceof Error ? error.message : 'Unexpected error.';
  return (
    <div role="alert" className={cn('rounded-lg border border-destructive/40 bg-destructive/5 p-5', className)}>
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-destructive" aria-hidden />
        <div className="min-w-0 flex-1">
          <h2 className="font-semibold text-foreground">{title}</h2>
          <p className="mt-1 text-sm text-foreground">{message}</p>
          {apiErr && (
            <p className="mt-2 font-mono text-xs text-muted-foreground">
              {apiErr.code}
              {apiErr.requestId ? ` · request ${apiErr.requestId}` : ''}
            </p>
          )}
        </div>
        {onRetry && (
          <Button variant="outline" size="sm" onClick={onRetry}>
            <RefreshCw aria-hidden /> Retry
          </Button>
        )}
      </div>
    </div>
  );
}

export function LoadingState({ rows = 4, label = 'Loading', className }: { rows?: number; label?: string; className?: string }) {
  return (
    <div className={cn('flex flex-col gap-3 animate-fade-in', className)} role="status" aria-live="polite" aria-label={label}>
      <span className="sr-only">{label}…</span>
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className={cn('h-10 w-full rounded-lg', i === 0 && 'h-8 w-1/3')} />
      ))}
    </div>
  );
}

/** Generic async section: picks the right state for a TanStack query. */
export function QueryBoundary<T>({
  query,
  children,
  empty,
  isEmpty,
  rows,
}: {
  query: { data: T | undefined; isPending: boolean; isError: boolean; error: unknown; refetch: () => unknown };
  children: (data: T) => ReactNode;
  empty?: ReactNode;
  isEmpty?: (data: T) => boolean;
  rows?: number;
}) {
  if (query.isPending) return <LoadingState rows={rows} />;
  if (query.isError) return <ErrorState error={query.error} onRetry={() => query.refetch()} />;
  const data = query.data as T;
  if (isEmpty ? isEmpty(data) : Array.isArray(data) && data.length === 0) return <>{empty ?? <EmptyState title="Nothing here yet" />}</>;
  return <>{children(data)}</>;
}
