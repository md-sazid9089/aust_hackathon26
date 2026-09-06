import { Link, useParams } from 'react-router-dom';
import { ArrowLeft, RotateCcw } from 'lucide-react';
import type { RunModule } from '@/lib/types/api';
import { useCourse, useFindings, useRun } from '@/lib/queries';
import { useRunEvents, isTerminal } from '@/hooks/useRunEvents';
import { useAuth } from '@/auth/AuthProvider';
import { PageHeader, QueryBoundary, ErrorState, LoadingState } from '@/components/feedback/states';
import { RunProgress, StatusBadge } from '@/components/domain/RunProgress';
import { ExportButton } from '@/components/domain/ExportButton';
import { Button } from '@/components/ui/button';
import { MODULE_LABEL, MODULE_PATH, formatDate } from '@/lib/format';
import { ExamAuditResults } from './ExamAuditResults';
import { AttainmentResults } from './AttainmentResults';
import { SyllabusCheckResults } from './SyllabusCheckResults';
import { CalibrationResults } from './CalibrationResults';

export function RunPage({ module }: { module: RunModule }) {
  const { id = '', runId = '' } = useParams();
  const { profile } = useAuth();
  const readOnly = profile?.role === 'admin';
  const course = useCourse(id);
  const run = useRun(runId);
  const { events, streamError, active } = useRunEvents(run.data);
  const done = isTerminal(run.data?.status);
  const findings = useFindings(runId, done);

  return (
    <QueryBoundary query={run} rows={6}>
      {(r) => {
        const accepted = (findings.data ?? []).filter((f) => f.status === 'accepted').length;
        const code = course.data?.code ?? '';
        return (
          <>
            <PageHeader
              eyebrow={
                <Link to={`/courses/${id}`} className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
                  <ArrowLeft className="h-4 w-4" aria-hidden /> <span className="font-mono">{code}</span> {course.data?.title}
                </Link>
              }
              title={
                <span className="flex flex-wrap items-center gap-3">
                  {MODULE_LABEL[module]} <StatusBadge status={r.status} />
                </span>
              }
              description={<>Run started {formatDate(r.started_at ?? r.created_at)}{r.finished_at ? ` · finished ${formatDate(r.finished_at)}` : ''}</>}
              actions={
                <>
                  {!readOnly && (
                    <Button asChild variant="outline">
                      <Link to={`/courses/${id}/${MODULE_PATH[module]}/new`}><RotateCcw aria-hidden /> New run</Link>
                    </Button>
                  )}
                  {done && r.status !== 'failed' && <ExportButton runId={r.id} filename={`${code || 'course'}-${MODULE_PATH[module]}-${r.id.slice(0, 8)}`} acceptedCount={accepted} />}
                </>
              }
            />

            {(active || r.status === 'partial' || r.status === 'failed') && <RunProgress run={r} events={events} streamError={streamError} />}

            {done && r.status !== 'failed' && (
              <div className="mt-6">
                {findings.isPending && <LoadingState rows={4} />}
                {findings.isError && <ErrorState error={findings.error} onRetry={() => findings.refetch()} />}
                {findings.data && (
                  <>
                    {module === 'exam_audit' && <ExamAuditResults run={r} findings={findings.data} courseId={id} readOnly={readOnly} />}
                    {module === 'attainment' && <AttainmentResults run={r} findings={findings.data} readOnly={readOnly} />}
                    {module === 'syllabus_check' && <SyllabusCheckResults run={r} findings={findings.data} readOnly={readOnly} />}
                    {module === 'calibration' && <CalibrationResults run={r} findings={findings.data} readOnly={readOnly} />}
                  </>
                )}
              </div>
            )}
          </>
        );
      }}
    </QueryBoundary>
  );
}
