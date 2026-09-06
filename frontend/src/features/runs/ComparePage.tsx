import { useSearchParams, useParams, Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { useCompare, useCourse, useRuns } from '@/lib/queries';
import { PageHeader, QueryBoundary, EmptyState, LoadingState, ErrorState } from '@/components/feedback/states';
import { FindingCard } from '@/components/domain/FindingList';
import { Stat } from '@/components/domain/trust';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/primitives';
import { Field } from '@/components/ui/input';
import { formatDate } from '@/lib/format';
import { GitCompare } from 'lucide-react';

export function ComparePage() {
  const { id = '' } = useParams();
  const [sp, setSp] = useSearchParams();
  const a = sp.get('a');
  const b = sp.get('b');
  const course = useCourse(id);
  const runs = useRuns(id, { module: 'exam_audit' });
  const cmp = useCompare(a, b);

  const completed = (runs.data?.items ?? []).filter((r) => r.status === 'completed' || r.status === 'partial');
  const set = (k: 'a' | 'b', v: string) => setSp((p) => { p.set(k, v); return p; }, { replace: true });
  const label = (rid: string) => { const r = completed.find((x) => x.id === rid); return r ? `${formatDate(r.created_at)} · ${r.id.slice(0, 8)}` : rid; };

  return (
    <QueryBoundary query={course} rows={6}>
      {(c) => (
        <>
          <PageHeader
            eyebrow={<Link to={`/courses/${id}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"><ArrowLeft className="h-4 w-4" aria-hidden /> <span className="font-mono">{c.code}</span> {c.title}</Link>}
            title="Compare exam audits"
            description="Which findings from the earlier audit were resolved in the later draft, which persist, and which are new."
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Field id="run-a" label="Earlier audit (A)">
              <Select value={a ?? ''} onValueChange={(v) => set('a', v)}><SelectTrigger id="run-a"><SelectValue placeholder="Choose a run" /></SelectTrigger>
                <SelectContent>{completed.map((r) => <SelectItem key={r.id} value={r.id}>{label(r.id)}</SelectItem>)}</SelectContent></Select>
            </Field>
            <Field id="run-b" label="Later audit (B)">
              <Select value={b ?? ''} onValueChange={(v) => set('b', v)}><SelectTrigger id="run-b"><SelectValue placeholder="Choose a run" /></SelectTrigger>
                <SelectContent>{completed.filter((r) => r.id !== a).map((r) => <SelectItem key={r.id} value={r.id}>{label(r.id)}</SelectItem>)}</SelectContent></Select>
            </Field>
          </div>

          {completed.length < 2 && !runs.isPending && (
            <div className="mt-6"><EmptyState icon={GitCompare} title="Need two completed audits" description="Run the exam audit on a revised draft, then come back here to see what changed." /></div>
          )}

          {a && b && (
            <div className="mt-8 flex flex-col gap-6">
              {cmp.isPending && <LoadingState rows={4} />}
              {cmp.isError && <ErrorState error={cmp.error} onRetry={() => cmp.refetch()} />}
              {cmp.data && (
                <>
                  <section aria-label="Summary" className="grid gap-3 sm:grid-cols-3">
                    <Stat label="Resolved" value={cmp.data.resolved.length} hint="In A, not in B" />
                    <Stat label="Persisting" value={cmp.data.persisting.length} hint="Same target in both" />
                    <Stat label="New" value={cmp.data.new.length} hint="In B, not in A" />
                  </section>
                  {(['resolved', 'new'] as const).map((k) => (
                    <section key={k} aria-labelledby={`${k}-h`} className="flex flex-col gap-3">
                      <h2 id={`${k}-h`} className="text-xl font-semibold capitalize">{k} <span className="tabular text-muted-foreground">({cmp.data![k].length})</span></h2>
                      {cmp.data![k].length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : cmp.data![k].map((f) => <FindingCard key={f.id} finding={f} readOnly />)}
                    </section>
                  ))}
                  <section aria-labelledby="persist-h" className="flex flex-col gap-3">
                    <h2 id="persist-h" className="text-xl font-semibold">Persisting <span className="tabular text-muted-foreground">({cmp.data.persisting.length})</span></h2>
                    {cmp.data.persisting.length === 0 ? <p className="text-sm text-muted-foreground">None.</p> : cmp.data.persisting.map((p) => (
                      <div key={p.b.id} className="grid gap-3 lg:grid-cols-2">
                        <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">In A</p><FindingCard finding={p.a} readOnly /></div>
                        <div><p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">In B</p><FindingCard finding={p.b} readOnly /></div>
                      </div>
                    ))}
                  </section>
                </>
              )}
            </div>
          )}
        </>
      )}
    </QueryBoundary>
  );
}
