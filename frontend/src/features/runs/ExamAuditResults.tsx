import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { GitCompare, Lightbulb } from 'lucide-react';
import { toast } from 'sonner';
import type { ExamAuditSummary, Finding, Run } from '@/lib/types/api';
import { useSuggest } from '@/lib/queries';
import { Stat, ComputedLabel, AiBlock } from '@/components/domain/trust';
import { BarWithTable } from '@/components/domain/charts';
import { FindingList } from '@/components/domain/FindingList';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { BLOOM_LABEL, BLOOM_ORDER, cn } from '@/lib/format';

function CoverageHeatmap({ cells }: { cells: ExamAuditSummary['coverage'] }) {
  const cos = cells.filter((c) => c.target_kind === 'course_outcome');
  return (
    <section aria-labelledby="cov-h" className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 id="cov-h" className="font-semibold">CO coverage by marks</h3>
        <ComputedLabel />
      </div>
      <Table dense>
        <TableHeader>
          <TableRow>
            <TableHead>CO</TableHead>
            <TableHead className="text-right">Marks</TableHead>
            <TableHead className="text-right">Share</TableHead>
            <TableHead className="text-right">Expected</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {cos.map((c) => (
            <TableRow key={c.target_code} className={cn(c.status === 'uncovered' && 'bg-sev-high/60', c.status === 'overweight' && 'bg-sev-medium/60')}>
              <TableCell className="font-semibold">{c.target_code}</TableCell>
              <TableCell className="text-right tabular">{c.marks}</TableCell>
              <TableCell className="text-right tabular">{(c.share * 100).toFixed(0)}%</TableCell>
              <TableCell className="text-right tabular text-muted-foreground">{(c.expected_share * 100).toFixed(0)}%</TableCell>
              <TableCell>
                <Badge variant={c.status === 'covered' ? 'success' : c.status === 'uncovered' ? 'high' : 'medium'}>{c.status}</Badge>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </section>
  );
}

export function ExamAuditResults({ run, findings, courseId, readOnly }: { run: Run; findings: Finding[]; courseId: string; readOnly?: boolean }) {
  const s = run.summary as ExamAuditSummary | null;
  const suggest = useSuggest(run.id);
  const uncoveredCoIds = useMemo(() => findings.filter((f) => f.type === 'coverage_gap' && f.target_id).map((f) => f.target_id!), [findings]);
  const hasSuggestions = findings.some((f) => f.type === 'suggestion');

  if (!s) return null;
  const bloomData = BLOOM_ORDER.map((b) => ({ label: BLOOM_LABEL[b], value: s.bloom?.counts?.[b] ?? 0 }));
  const topics = s.coverage.filter((c) => c.target_kind === 'topic');

  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="CO coverage" value={`${Math.round(s.coverage_pct)}%`} hint={`${s.coverage.filter((c) => c.target_kind === 'course_outcome' && c.status !== 'uncovered').length} of ${s.coverage.filter((c) => c.target_kind === 'course_outcome').length} COs assessed`} />
        <Stat label="Repeated questions" value={s.duplicates.length} hint={s.duplicates[0] ? `Top similarity ${(s.duplicates[0].similarity * 100).toFixed(0)}%` : 'No matches ≥ 80%'} />
        <Stat label="Fairness deviation" value={s.fairness.deviation_score.toFixed(2)} hint={s.fairness.notes.join(' ') || 'Marks are evenly distributed.'} />
        <Stat label="Open findings" value={findings.filter((f) => f.status === 'open').length} hint={`${findings.filter((f) => f.status === 'accepted').length} accepted`} />
      </section>

      <div className="grid gap-4 lg:grid-cols-2">
        <CoverageHeatmap cells={s.coverage} />
        <BarWithTable title="Bloom distribution (questions per level)" data={bloomData} valueLabel="Questions" unit="" />
      </div>

      {topics.length > 0 && (
        <details className="rounded-lg border bg-card p-4">
          <summary className="cursor-pointer font-semibold">Topic coverage ({topics.filter((t) => t.status !== 'uncovered').length}/{topics.length} topics)</summary>
          <ul className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            {topics.map((t) => (
              <li key={t.target_code} className="flex items-center justify-between rounded-md border px-3 py-2 text-sm">
                <span>{t.target_code}</span>
                <span className="tabular text-muted-foreground">{t.marks} marks</span>
              </li>
            ))}
          </ul>
        </details>
      )}

      <section aria-labelledby="findings-h" className="flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="findings-h" className="text-xl font-semibold">Findings</h2>
          <div className="flex gap-2">
            <Button asChild variant="outline">
              <Link to={`/courses/${courseId}/exam-audit/compare?a=${run.id}`}><GitCompare aria-hidden /> Compare with another audit</Link>
            </Button>
            {!readOnly && uncoveredCoIds.length > 0 && !hasSuggestions && run.status === 'completed' && (
              <Button variant="accent" loading={suggest.isPending} onClick={() => suggest.mutate(uncoveredCoIds, { onSuccess: (r) => toast.success(`${r.length} questions suggested`), onError: (e) => toast.error(e.message) })}>
                <Lightbulb aria-hidden /> Suggest questions for uncovered COs
              </Button>
            )}
          </div>
        </div>
        <FindingList
          runId={run.id}
          findings={findings}
          readOnly={readOnly}
          renderExtra={(f) =>
            f.type === 'suggestion' && typeof f.payload.question_text === 'string' ? (
              <AiBlock className="mt-3" label={false}>
                <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-ai-foreground">Draft question · {String(f.payload.bloom_level)}</p>
                <p>{f.payload.question_text}</p>
              </AiBlock>
            ) : null
          }
        />
      </section>
    </div>
  );
}
