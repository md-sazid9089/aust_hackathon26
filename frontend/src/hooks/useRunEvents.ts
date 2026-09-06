import { useEffect, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useApi } from '@/lib/api';
import { qk } from '@/lib/queries';
import type { Run, RunProgressEvent, RunStatus } from '@/lib/types/api';

const TERMINAL: RunStatus[] = ['completed', 'partial', 'failed'];
export const isTerminal = (s: RunStatus | undefined) => !!s && TERMINAL.includes(s);

/** Subscribes to run progress while the run is active; invalidates run + findings on completion. */
export function useRunEvents(run: Run | undefined) {
  const api = useApi();
  const qc = useQueryClient();
  const [events, setEvents] = useState<RunProgressEvent[]>([]);
  const [streamError, setStreamError] = useState<unknown>(null);
  const lastSeq = useRef(0);
  const runId = run?.id;
  const active = !!run && !isTerminal(run.status);

  useEffect(() => {
    if (!runId || !active) return;
    setStreamError(null);
    const close = api.subscribeRunEvents(runId, lastSeq.current, {
      onProgress: (e) => {
        lastSeq.current = Math.max(lastSeq.current, e.seq);
        setEvents((prev) => (prev.some((p) => p.seq === e.seq) ? prev : [...prev, e]));
        qc.setQueryData<Run>(qk.run(runId), (old) => (old ? { ...old, progress_pct: e.pct ?? old.progress_pct, current_stage: e.stage, status: old.status === 'queued' ? 'analyzing' : old.status } : old));
      },
      onDone: () => {
        void qc.invalidateQueries({ queryKey: qk.run(runId) });
        void qc.invalidateQueries({ queryKey: qk.findings(runId) });
        void qc.invalidateQueries({ queryKey: qk.attainment(runId) });
        void qc.invalidateQueries({ queryKey: qk.prescores(runId) });
        void qc.invalidateQueries({ queryKey: ['runs'] });
        void qc.invalidateQueries({ queryKey: qk.dashboard });
      },
      onError: (err) => setStreamError(err),
    });
    return close;
  }, [api, qc, runId, active]);

  return { events, streamError, active };
}
