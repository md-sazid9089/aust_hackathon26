import type { Finding, Run, SyllabusCheckSummary } from '@/lib/types/api';
import { Stat, ComputedLabel } from '@/components/domain/trust';
import { FindingList } from '@/components/domain/FindingList';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';

export function SyllabusCheckResults({ run, findings, readOnly }: { run: Run; findings: Finding[]; readOnly?: boolean }) {
  const s = run.summary as SyllabusCheckSummary | null;
  if (!s) return null;
  const courses = [...new Set(s.matrix.map((m) => m.course_code))];
  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Overlapping topics" value={`${Math.round(s.overlap_pct)}%`} hint="Share of this syllabus's topics judged to overlap another course" />
        <Stat label="Matched pairs" value={s.matrix.length} hint={`Across ${courses.length} course${courses.length === 1 ? '' : 's'}`} />
        <Stat label="Prerequisite links" value={s.matrix.filter((m) => m.relation === 'prerequisite').length} hint="Not counted as overlap" />
        <Stat label="Open findings" value={findings.filter((f) => f.status === 'open').length} hint={`${findings.filter((f) => f.status === 'accepted').length} accepted`} />
      </section>

      <section aria-labelledby="overlap-h" className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <h3 id="overlap-h" className="font-semibold">Topic overlap matrix</h3>
          <ComputedLabel />
        </div>
        <Table dense>
          <TableHeader>
            <TableRow>
              <TableHead>This course</TableHead>
              <TableHead>Other course</TableHead>
              <TableHead>Topic there</TableHead>
              <TableHead className="text-right">Similarity</TableHead>
              <TableHead>Relation</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {s.matrix.map((m, i) => (
              <TableRow key={i}>
                <TableCell className="max-w-xs">{m.topic_a}</TableCell>
                <TableCell className="font-mono">{m.course_code}</TableCell>
                <TableCell className="max-w-xs">{m.topic_b}</TableCell>
                <TableCell className="text-right tabular">{m.similarity.toFixed(2)}</TableCell>
                <TableCell><Badge variant={m.relation === 'overlap' ? 'medium' : m.relation === 'prerequisite' ? 'info' : 'outline'}>{m.relation}</Badge></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </section>

      <section aria-labelledby="findings-h" className="flex flex-col gap-4">
        <h2 id="findings-h" className="text-xl font-semibold">Findings</h2>
        <FindingList runId={run.id} findings={findings} readOnly={readOnly} />
      </section>
    </div>
  );
}
