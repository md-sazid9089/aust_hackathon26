import { AlertTriangle, CheckCircle2, Loader2 } from 'lucide-react';
import type { Run, RunProgressEvent } from '@/lib/types/api';
import { Progress } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { STATUS_LABEL, cn, formatDate } from '@/lib/format';
import { isTerminal } from '@/hooks/useRunEvents';

export function StatusBadge({ status }: { status: Run['status'] }) {
  const variant = status === 'completed' ? 'success' : status === 'failed' ? 'destructive' : status === 'partial' ? 'medium' : 'secondary';
  return (
    <Badge variant={variant}>
      {(status === 'queued' || status === 'analyzing') && <Loader2 className="h-3 w-3 animate-spin" aria-hidden />}
      {STATUS_LABEL[status]}
    </Badge>
  );
}

/** Live pipeline view (architecture §15 RunProgress). Stage list is derived from received events. */
export function RunProgress({ run, events, streamError }: { run: Run; events: RunProgressEvent[]; streamError: unknown }) {
  const done = isTerminal(run.status);
  return (
    <section aria-live="polite" aria-labelledby="run-progress-title" className="rounded-lg border bg-card p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 id="run-progress-title" className="text-lg font-semibold">
            {done ? 'Analysis finished' : 'Analysing…'}
          </h2>
          <p className="text-sm text-muted-foreground">
            Started {formatDate(run.started_at ?? run.created_at)}
            {run.finished_at ? ` · finished ${formatDate(run.finished_at)}` : ''}
          </p>
        </div>
        <StatusBadge status={run.status} />
      </div>
      <div className="mt-4 flex items-center gap-3">
        <Progress value={run.progress_pct} label="Run progress" className="flex-1" />
        <span className="w-12 text-right text-sm font-semibold tabular">{Math.round(run.progress_pct)}%</span>
      </div>
      <ol className="mt-4 flex flex-col gap-2 text-sm">
        {events.length === 0 && !done && (
          <li className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden /> Waiting for the first stage…
          </li>
        )}
        {events.map((e, i) => {
          const last = i === events.length - 1;
          return (
            <li key={e.seq} className={cn('flex items-start gap-2', last && !done ? 'text-foreground' : 'text-muted-foreground')}>
              {last && !done ? <Loader2 className="mt-0.5 h-4 w-4 shrink-0 animate-spin text-primary" aria-hidden /> : <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" aria-hidden />}
              <span>
                <span className="font-medium">{e.stage}</span> — {e.message}
              </span>
              <span className="ml-auto shrink-0 tabular text-xs">{e.pct}%</span>
            </li>
          );
        })}
      </ol>
      {run.status === 'failed' && run.error && (
        <p role="alert" className="mt-4 flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 p-3 text-sm">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-destructive" aria-hidden /> {run.error}
        </p>
      )}
      {run.status === 'partial' && (
        <p className="mt-4 flex items-start gap-2 rounded-md border border-sev-medium-fg/30 bg-sev-medium p-3 text-sm text-sev-medium-fg">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> Some stages did not finish. Computed results below are complete; AI explanations may be missing. You can re-run later.
        </p>
      )}
      {!!streamError && !done && (
        <p className="mt-3 text-sm text-muted-foreground">Live updates paused — reconnecting… (results will still appear when the run finishes).</p>
      )}
    </section>
  );
}
