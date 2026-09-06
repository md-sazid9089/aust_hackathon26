import { useState } from 'react';
import type { CalibrationSummary, Finding, Run, RubricCriterion } from '@/lib/types/api';
import { usePrescores } from '@/lib/queries';
import { Stat, ComputedLabel, AiLabel, AiBlock } from '@/components/domain/trust';
import { FindingList } from '@/components/domain/FindingList';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Checkbox } from '@/components/ui/primitives';
import { LoadingState, ErrorState } from '@/components/feedback/states';
import { isTerminal } from '@/hooks/useRunEvents';
import { cn } from '@/lib/format';

function isCriterion(v: unknown): v is RubricCriterion {
  return !!v && typeof v === 'object' && Array.isArray((v as RubricCriterion).levels);
}

/** Side-by-side current vs proposed descriptor per level. Proposed text is LLM-authored → AI surface. */
export function RubricDiff({ proposed, current }: { proposed: RubricCriterion; current?: RubricCriterion }) {
  return (
    <div className="mt-3 grid gap-2 md:grid-cols-2">
      <div className="rounded-md border p-3">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Current</p>
        <ul className="flex flex-col gap-1 text-sm">
          {(current?.levels ?? proposed.levels).map((l) => (
            <li key={l.label}><span className="font-medium">{l.label}</span> <span className="tabular text-muted-foreground">({l.score})</span> — {current?.levels.find((c) => c.label === l.label)?.descriptor ?? '—'}</li>
          ))}
        </ul>
      </div>
      <AiBlock label={false}>
        <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-ai-foreground">Proposed</p>
        <ul className="flex flex-col gap-1 text-sm">
          {proposed.levels.map((l) => {
            const changed = current?.levels.find((c) => c.label === l.label)?.descriptor !== l.descriptor;
            return (
              <li key={l.label} className={cn(changed && 'font-medium')}>
                <span>{l.label}</span> <span className="tabular opacity-70">({l.score})</span> — {l.descriptor}
                {changed && <span className="sr-only"> (changed)</span>}
              </li>
            );
          })}
        </ul>
      </AiBlock>
    </div>
  );
}

export function CalibrationResults({ run, findings, readOnly }: { run: Run; findings: Finding[]; readOnly?: boolean }) {
  const s = run.summary as CalibrationSummary | null;
  const pre = usePrescores(run.id, isTerminal(run.status) && run.status !== 'failed');
  const [onlyDivergent, setOnlyDivergent] = useState(true);
  if (!s) return null;

  const rows = (pre.data ?? []).filter((p) => {
    if (!onlyDivergent) return true;
    const v = Object.values(p.grader_scores);
    return Math.max(...v) - Math.min(...v) > 0;
  });

  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Graders" value={s.graders.length} hint={s.graders.join(', ')} />
        <Stat label="Divergent answers" value={s.divergent_answers} hint="≥ 25% of criterion max apart" />
        <Stat label="Mean score gap" value={s.mean_abs_dev.toFixed(2)} hint="Average max − min per criterion" />
        <Stat label="Criteria flagged" value={s.criteria_flagged.length} hint={s.criteria_flagged.join(', ') || 'None'} />
      </section>

      <section aria-labelledby="div-h" className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
          <h3 id="div-h" className="font-semibold">Grader scores and AI pre-score</h3>
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm"><Checkbox checked={onlyDivergent} onCheckedChange={(v) => setOnlyDivergent(v === true)} /> Only where graders differ</label>
            <ComputedLabel />
            <AiLabel />
          </div>
        </div>
        {pre.isPending && <LoadingState rows={4} />}
        {pre.isError && <ErrorState error={pre.error} onRetry={() => pre.refetch()} />}
        {pre.data && (
          <Table dense>
            <TableHeader>
              <TableRow>
                <TableHead>Student</TableHead>
                <TableHead>Criterion</TableHead>
                {s.graders.map((g) => <TableHead key={g} className="text-right">{g}</TableHead>)}
                <TableHead className="text-right"><span className="text-ai-foreground">AI pre-score</span></TableHead>
                <TableHead>AI rationale</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.length === 0 && <TableRow><TableCell colSpan={4 + s.graders.length} className="text-center text-muted-foreground">No divergent scores.</TableCell></TableRow>}
              {rows.map((p) => {
                const v = Object.values(p.grader_scores);
                const gap = Math.max(...v) - Math.min(...v);
                return (
                  <TableRow key={`${p.answer_id}-${p.criterion_code}`} className={cn(gap >= 2 && 'bg-sev-high/50', gap === 1 && 'bg-sev-medium/50')}>
                    <TableCell className="font-mono">{p.student_anon_id}</TableCell>
                    <TableCell className="font-semibold">{p.criterion_code}</TableCell>
                    {s.graders.map((g) => <TableCell key={g} className="text-right tabular">{p.grader_scores[g] ?? '—'}</TableCell>)}
                    <TableCell className="text-right tabular bg-ai-surface text-ai-foreground">{p.ai_score}</TableCell>
                    <TableCell className="max-w-md text-sm text-ai-foreground">{p.rationale}</TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </section>

      <section aria-labelledby="findings-h" className="flex flex-col gap-4">
        <h2 id="findings-h" className="text-xl font-semibold">Findings</h2>
        <FindingList
          runId={run.id}
          findings={findings}
          readOnly={readOnly}
          renderExtra={(f) => (f.type === 'rubric_clarification' && isCriterion(f.payload.proposed) ? <RubricDiff proposed={f.payload.proposed} current={isCriterion(f.payload.current) ? f.payload.current : undefined} /> : null)}
        />
      </section>
    </div>
  );
}
