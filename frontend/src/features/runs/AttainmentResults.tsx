import type { AttainmentSummary, Finding, Run } from '@/lib/types/api';
import { useAttainment } from '@/lib/queries';
import { Stat } from '@/components/domain/trust';
import { BarWithTable } from '@/components/domain/charts';
import { FindingList } from '@/components/domain/FindingList';
import { LoadingState, ErrorState } from '@/components/feedback/states';
import { isTerminal } from '@/hooks/useRunEvents';

export function AttainmentResults({ run, findings, readOnly }: { run: Run; findings: Finding[]; readOnly?: boolean }) {
  const s = run.summary as AttainmentSummary | null;
  const att = useAttainment(run.id, isTerminal(run.status) && run.status !== 'failed');
  if (!s) return null;
  return (
    <div className="flex flex-col gap-6">
      <section aria-label="Summary" className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="COs attained" value={`${s.cos_met}/${s.cos_total}`} hint={`Threshold ${s.threshold}%`} />
        <Stat label="POs attained" value={`${s.pos_met}/${s.pos_total}`} hint="Weighted by CO→PO strength" />
        <Stat label="Students" value={att.data?.cos[0]?.students ?? '—'} hint="Anonymised marks sheet" />
        <Stat label="Open findings" value={findings.filter((f) => f.status === 'open').length} hint={`${findings.filter((f) => f.status === 'accepted').length} accepted`} />
      </section>

      {att.isPending && <LoadingState rows={3} />}
      {att.isError && <ErrorState error={att.error} onRetry={() => att.refetch()} />}
      {att.data && (
        <div className="grid gap-4 lg:grid-cols-2">
          <BarWithTable
            title="CO attainment (% of students at or above threshold)"
            valueLabel="Attained"
            secondaryLabel="Target"
            reference={att.data.threshold}
            data={att.data.cos.map((c) => ({ label: c.co_code, value: c.attained_pct, secondary: c.target_pct, tone: c.met ? 'ok' : c.attained_pct < c.target_pct - 20 ? 'bad' : 'warn' }))}
          />
          <BarWithTable
            title="PO attainment (weighted)"
            valueLabel="Attained"
            reference={att.data.threshold}
            data={att.data.pos.map((p) => ({ label: p.po_code, value: p.attained_pct, tone: p.met ? 'ok' : 'warn' }))}
          />
        </div>
      )}

      <section aria-labelledby="findings-h" className="flex flex-col gap-4">
        <h2 id="findings-h" className="text-xl font-semibold">Findings</h2>
        <FindingList runId={run.id} findings={findings} readOnly={readOnly} />
      </section>
    </div>
  );
}
