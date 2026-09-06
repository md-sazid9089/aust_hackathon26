import { AlertTriangle, Check, Copy, Info, X } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { cn } from '@/lib/utils';

// Values mirror the seeded CSE 2201 demo course (planted defects: CO6 uncovered, 58/60 marks, duplicates).
const COVERAGE = [
  { co: 'CO1', pct: 22 },
  { co: 'CO2', pct: 18 },
  { co: 'CO3', pct: 27 },
  { co: 'CO4', pct: 15 },
  { co: 'CO5', pct: 18 },
  { co: 'CO6', pct: 0 },
];

const FINDINGS = [
  {
    severity: 'high' as const,
    label: 'High',
    icon: AlertTriangle,
    title: 'CO6 has no question mapped to it',
    rationale: 'No question in the draft targets "evaluate normalisation trade-offs". CO6 carries 10% of the CO→PO map.',
    evidence: 'Q1–Q8 map to CO1–CO5 only.',
  },
  {
    severity: 'medium' as const,
    label: 'Medium',
    icon: Copy,
    title: 'Q4 is a near-duplicate of 2024 Q3',
    rationale: 'Cosine similarity 0.91; both ask students to draw an ER diagram for the same library scenario.',
    evidence: '"Draw an ER diagram for a library that lends books to members…"',
  },
  {
    severity: 'info' as const,
    label: 'Info',
    icon: Info,
    title: 'Declared total 60, questions sum to 58',
    rationale: 'Marks are computed from the extracted question list; two marks are unaccounted for.',
    evidence: '5 + 8 + 10 + 10 + 7 + 6 + 6 + 6 = 58',
  },
];

export function ProductPreview() {
  return (
    <div className="relative mx-auto max-w-5xl">
      <div
        aria-hidden
        className="pointer-events-none absolute -inset-x-6 -bottom-8 top-12 rounded-[28px] bg-gradient-to-b from-brand/10 to-transparent blur-2xl"
      />
      <Card
        role="img"
        aria-label="Preview of an Exam Paper Audit result: coverage per course outcome and three findings with rationale and evidence"
        className="relative overflow-hidden shadow-xl ring-1 ring-foreground/5 transition-transform duration-500 motion-safe:hover:-translate-y-0.5"
      >
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border bg-muted/40 px-4 py-3 sm:px-5">
          <div className="min-w-0">
            <p className="text-xs text-muted-foreground">CSE 2201 · Database Systems</p>
            <p className="truncate font-heading text-base font-semibold">Exam Paper Audit — Final draft v2</p>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="tabular">8 questions · 58 / 60 marks</Badge>
            <Badge variant="secondary">Completed</Badge>
          </div>
        </div>

        <div className="grid gap-0 md:grid-cols-[minmax(0,5fr)_minmax(0,7fr)]">
          <div className="border-b border-border p-4 sm:p-5 md:border-b-0 md:border-r">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold font-sans tracking-normal">Coverage by outcome</h3>
              <span className="text-xs text-muted-foreground">% of marks</span>
            </div>
            <ul className="space-y-2.5">
              {COVERAGE.map((row) => (
                <li key={row.co} className="grid grid-cols-[3rem_1fr_2.5rem] items-center gap-3 text-sm">
                  <span className="font-medium">{row.co}</span>
                  <span className="h-2.5 overflow-hidden rounded-full bg-muted">
                    <span
                      className={cn('block h-full rounded-full', row.pct === 0 ? 'bg-sev-high-fg' : 'bg-brand')}
                      style={{ width: `${Math.max(row.pct, row.pct === 0 ? 2 : 0)}%` }}
                    />
                  </span>
                  <span className={cn('tabular text-right text-xs', row.pct === 0 ? 'text-sev-high-fg font-semibold' : 'text-muted-foreground')}>
                    {row.pct}%
                  </span>
                </li>
              ))}
            </ul>
            <p className="mt-4 rounded-md border border-dashed border-border px-3 py-2 text-xs text-muted-foreground">
              Computed from confirmed question→CO map. No model involved.
            </p>
          </div>

          <div className="p-4 sm:p-5">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold font-sans tracking-normal">Findings</h3>
              <span className="text-xs text-muted-foreground">3 open</span>
            </div>
            <ul className="space-y-3">
              {FINDINGS.map((f) => (
                <li key={f.title} className="rounded-md border border-border bg-background p-3">
                  <div className="flex flex-wrap items-center gap-2">
                    <Badge variant={f.severity}>
                      <f.icon aria-hidden />
                      {f.label}
                    </Badge>
                    <span className="text-sm font-medium">{f.title}</span>
                  </div>
                  <p className="mt-2 text-xs leading-relaxed text-muted-foreground">{f.rationale}</p>
                  <blockquote className="mt-2 border-l-2 border-ai-border/60 bg-ai px-2.5 py-1.5 text-xs italic text-ai-foreground">
                    {f.evidence}
                  </blockquote>
                  <div className="mt-2.5 flex gap-2">
                    <Button size="sm" variant="outline" className="h-8 px-2.5 text-xs" tabIndex={-1} aria-hidden>
                      <Check aria-hidden />
                      Accept
                    </Button>
                    <Button size="sm" variant="ghost" className="h-8 px-2.5 text-xs" tabIndex={-1} aria-hidden>
                      <X aria-hidden />
                      Dismiss
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
}
