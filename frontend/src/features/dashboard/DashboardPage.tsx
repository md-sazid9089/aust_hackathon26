import { Link } from 'react-router-dom';
import { ArrowRight, LayoutDashboard } from 'lucide-react';
import { useDashboard } from '@/lib/queries';
import { PageHeader, QueryBoundary, EmptyState } from '@/components/feedback/states';
import { Stat } from '@/components/domain/trust';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export function DashboardPage() {
  const q = useDashboard();
  return (
    <>
      <PageHeader title="Dashboard" description="Latest audit and attainment result per course, and what you have decided so far." />
      <QueryBoundary
        query={q}
        isEmpty={(d) => d.courses.length === 0}
        empty={<EmptyState icon={LayoutDashboard} title="Nothing to show yet" description="Run an exam audit or attainment analysis and the results will appear here." action={<Button asChild><Link to="/">Go to courses</Link></Button>} />}
      >
        {(d) => (
          <div className="flex flex-col gap-6">
            <section aria-label="Totals" className="grid gap-3 sm:grid-cols-3">
              <Stat label="Runs" value={d.totals.runs} />
              <Stat label="Findings accepted" value={d.totals.accepted_findings} hint="Included in exports" />
              <Stat label="Findings dismissed" value={d.totals.dismissed_findings} />
            </section>
            <section aria-labelledby="courses-h" className="rounded-lg border bg-card">
              <h2 id="courses-h" className="sr-only">Per course</h2>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Course</TableHead>
                    <TableHead>Last exam audit</TableHead>
                    <TableHead className="text-right">Open findings</TableHead>
                    <TableHead>Last attainment</TableHead>
                    <TableHead><span className="sr-only">Open</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {d.courses.map((c) => (
                    <TableRow key={c.course_id}>
                      <TableCell><span className="font-mono font-semibold">{c.code}</span> <span className="text-muted-foreground">{c.title}</span></TableCell>
                      <TableCell>
                        {c.last_exam_audit ? (
                          <Link to={`/courses/${c.course_id}/exam-audit/${c.last_exam_audit.run_id}`} className="underline-offset-4 hover:underline">
                            <Badge variant={c.last_exam_audit.coverage_pct >= 80 ? 'success' : c.last_exam_audit.coverage_pct >= 60 ? 'medium' : 'high'}>{Math.round(c.last_exam_audit.coverage_pct)}% coverage</Badge>
                          </Link>
                        ) : <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell className="text-right tabular">{c.last_exam_audit?.open_findings ?? '—'}</TableCell>
                      <TableCell>
                        {c.last_attainment ? (
                          <Link to={`/courses/${c.course_id}/attainment/${c.last_attainment.run_id}`} className="underline-offset-4 hover:underline">
                            <Badge variant={c.last_attainment.cos_met === c.last_attainment.cos_total ? 'success' : 'medium'}>{c.last_attainment.cos_met}/{c.last_attainment.cos_total} COs</Badge>
                          </Link>
                        ) : <span className="text-muted-foreground">—</span>}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button asChild variant="ghost" size="sm"><Link to={`/courses/${c.course_id}`}>Open <ArrowRight aria-hidden /></Link></Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </section>
          </div>
        )}
      </QueryBoundary>
    </>
  );
}
