import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Check, RotateCcw, X, Filter } from 'lucide-react';
import { toast } from 'sonner';
import type { Finding, FindingSeverity, FindingStatus, FindingType } from '@/lib/types/api';
import { usePatchFinding } from '@/lib/queries';
import { useShortcuts } from '@/hooks/useShortcuts';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Checkbox, Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/primitives';
import { Kbd } from '@/components/ui/table';
import { EmptyState } from '@/components/feedback/states';
import { AiLabel, ComputedLabel, Evidence } from './trust';
import { FINDING_TYPE_LABEL, SEVERITY_LABEL, SEVERITY_ORDER, cn } from '@/lib/format';
import { ApiError } from '@/lib/api';

const sevBorder: Record<FindingSeverity, string> = {
  high: 'border-l-sev-high-fg',
  medium: 'border-l-sev-medium-fg',
  low: 'border-l-sev-low-fg',
  info: 'border-l-sev-info-fg',
};

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function payloadNumbers(p: Record<string, unknown>) {
  // Internal identifiers are provenance, not evidence — keep them out of the faculty-facing chips.
  return Object.entries(p)
    .filter(([k, v]) => !/(^|_)ids?$/.test(k) && (typeof v === 'number' || (typeof v === 'string' && v.length < 40 && !UUID_RE.test(v))))
    .slice(0, 6) as [string, number | string][];
}

export function FindingCard({
  finding,
  focused,
  selected,
  onSelect,
  onDecide,
  readOnly,
  extra,
}: {
  finding: Finding;
  focused?: boolean;
  selected?: boolean;
  onSelect?: (v: boolean) => void;
  onDecide?: (status: FindingStatus) => void;
  readOnly?: boolean;
  extra?: React.ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    if (focused) ref.current?.scrollIntoView({ block: 'nearest' });
  }, [focused]);
  const nums = payloadNumbers(finding.payload);
  const lang = /[\u0980-\u09FF]/.test(finding.evidence_snippet ?? '') ? 'bn' : undefined;

  return (
    <article
      ref={ref}
      aria-current={focused || undefined}
      className={cn(
        'rounded-lg border border-l-4 bg-card p-4 transition-[box-shadow,border-color] duration-fast',
        sevBorder[finding.severity],
        focused && 'ring-2 ring-ring ring-offset-2 ring-offset-background',
        finding.status !== 'open' && 'opacity-80',
      )}
    >
      <header className="flex items-start gap-3">
        {onSelect && <Checkbox checked={!!selected} onCheckedChange={(v) => onSelect(v === true)} aria-label={`Select finding: ${finding.title}`} className="mt-1" />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge variant={finding.severity}>{SEVERITY_LABEL[finding.severity]}</Badge>
            <Badge variant="outline">{FINDING_TYPE_LABEL[finding.type]}</Badge>
            {finding.target_label && <span className="text-sm text-muted-foreground">{finding.target_label}</span>}
            {finding.status !== 'open' && (
              <Badge variant={finding.status === 'accepted' ? 'success' : 'secondary'} className="ml-auto">
                {finding.status === 'accepted' ? 'Accepted' : 'Dismissed'}
              </Badge>
            )}
          </div>
          <h3 className="mt-2 text-lg font-semibold leading-snug">{finding.title}</h3>
        </div>
      </header>

      {nums.length > 0 && (
        <dl className="mt-3 flex flex-wrap gap-x-5 gap-y-1 text-sm">
          <ComputedLabel className="w-full" />
          {nums.map(([k, v]) => (
            <div key={k} className="flex gap-1.5">
              <dt className="text-muted-foreground">{k.replace(/_/g, ' ')}</dt>
              <dd className="font-semibold tabular">{typeof v === 'number' ? (Number.isInteger(v) ? v : v.toFixed(2)) : v}</dd>
            </div>
          ))}
        </dl>
      )}

      <div className="mt-3">
        <AiLabel className="mb-1" />
        <p className="text-base leading-relaxed">{finding.rationale}</p>
      </div>

      {finding.evidence_snippet && (
        <div className="mt-3">
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Evidence</p>
          <Evidence lang={lang}>{finding.evidence_snippet}</Evidence>
        </div>
      )}

      {extra}

      {!readOnly && onDecide && (
        <footer className="mt-4 flex flex-wrap items-center gap-2 border-t pt-3">
          {finding.status === 'open' ? (
            <>
              <Button size="sm" onClick={() => onDecide('accepted')}>
                <Check aria-hidden /> Accept
              </Button>
              <Button size="sm" variant="outline" onClick={() => onDecide('dismissed')}>
                <X aria-hidden /> Dismiss
              </Button>
            </>
          ) : (
            <Button size="sm" variant="ghost" onClick={() => onDecide('open')}>
              <RotateCcw aria-hidden /> Reopen
            </Button>
          )}
          {focused && (
            <span className="ml-auto hidden items-center gap-1 text-xs text-muted-foreground md:flex">
              <Kbd>A</Kbd> accept <Kbd>D</Kbd> dismiss <Kbd>J</Kbd>/<Kbd>K</Kbd> move
            </span>
          )}
        </footer>
      )}
    </article>
  );
}

/** Filterable, bulk-actionable list with URL-persisted filters and J/K/A/D shortcuts. */
export function FindingList({ runId, findings, readOnly, renderExtra }: { runId: string; findings: Finding[]; readOnly?: boolean; renderExtra?: (f: Finding) => React.ReactNode }) {
  const [sp, setSp] = useSearchParams();
  const status = (sp.get('status') ?? 'open') as FindingStatus | 'all';
  const sev = (sp.get('severity') ?? 'all') as FindingSeverity | 'all';
  const type = (sp.get('type') ?? 'all') as FindingType | 'all';
  const setParam = (k: string, v: string) => {
    const n = new URLSearchParams(sp);
    if (v === 'all' || (k === 'status' && v === 'open')) n.delete(k);
    else n.set(k, v);
    setSp(n, { replace: true });
  };

  const types = useMemo(() => Array.from(new Set(findings.map((f) => f.type))), [findings]);
  const filtered = useMemo(
    () =>
      findings
        .filter((f) => (status === 'all' ? true : f.status === status))
        .filter((f) => (sev === 'all' ? true : f.severity === sev))
        .filter((f) => (type === 'all' ? true : f.type === type))
        .sort((a, b) => SEVERITY_ORDER.indexOf(a.severity) - SEVERITY_ORDER.indexOf(b.severity)),
    [findings, status, sev, type],
  );

  const [focus, setFocus] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  useEffect(() => setFocus((f) => Math.min(f, Math.max(0, filtered.length - 1))), [filtered.length]);

  const patch = usePatchFinding(runId);
  const decide = useCallback(
    (ids: string[], s: FindingStatus) => {
      ids.forEach((id) =>
        patch.mutate(
          { id, status: s },
          {
            onError: (e) => toast.error(e instanceof ApiError && e.status === 403 ? 'Admins cannot change findings.' : 'Could not save decision.'),
          },
        ),
      );
      if (ids.length > 1) toast.success(`${ids.length} findings ${s}`);
      setSelected(new Set());
    },
    [patch],
  );

  const shortcuts = useMemo(
    () => ({
      j: () => setFocus((f) => Math.min(filtered.length - 1, f + 1)),
      k: () => setFocus((f) => Math.max(0, f - 1)),
      a: () => !readOnly && filtered[focus] && decide([filtered[focus].id], 'accepted'),
      d: () => !readOnly && filtered[focus] && decide([filtered[focus].id], 'dismissed'),
    }),
    [filtered, focus, decide, readOnly],
  );
  useShortcuts(shortcuts, filtered.length > 0);

  const counts = {
    open: findings.filter((f) => f.status === 'open').length,
    accepted: findings.filter((f) => f.status === 'accepted').length,
    dismissed: findings.filter((f) => f.status === 'dismissed').length,
  };

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Finding filters">
        <Filter className="h-4 w-4 text-muted-foreground" aria-hidden />
        {(['open', 'accepted', 'dismissed', 'all'] as const).map((s) => (
          <Button key={s} size="sm" variant={status === s ? 'secondary' : 'ghost'} aria-pressed={status === s} onClick={() => setParam('status', s)}>
            {s[0].toUpperCase() + s.slice(1)}
            <span className="tabular text-muted-foreground">{s === 'all' ? findings.length : counts[s]}</span>
          </Button>
        ))}
        <div className="ml-auto flex flex-wrap gap-2">
          <Select value={sev} onValueChange={(v) => setParam('severity', v)}>
            <SelectTrigger className="h-9 w-40 text-sm" aria-label="Severity">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              {SEVERITY_ORDER.map((s) => (
                <SelectItem key={s} value={s}>
                  {SEVERITY_LABEL[s]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={type} onValueChange={(v) => setParam('type', v)}>
            <SelectTrigger className="h-9 w-48 text-sm" aria-label="Finding type">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All types</SelectItem>
              {types.map((t) => (
                <SelectItem key={t} value={t}>
                  {FINDING_TYPE_LABEL[t]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {!readOnly && filtered.length > 0 && (
        <div className="flex flex-wrap items-center gap-2 rounded-md border bg-muted/40 px-3 py-2 text-sm">
          <Checkbox
            checked={selected.size === filtered.length ? true : selected.size > 0 ? 'indeterminate' : false}
            onCheckedChange={(v) => setSelected(v === true ? new Set(filtered.map((f) => f.id)) : new Set())}
            aria-label="Select all visible findings"
          />
          <span className="tabular">{selected.size} selected</span>
          <Button size="sm" variant="outline" disabled={selected.size === 0} onClick={() => decide([...selected], 'accepted')}>
            <Check aria-hidden /> Accept selected
          </Button>
          <Button size="sm" variant="outline" disabled={selected.size === 0} onClick={() => decide([...selected], 'dismissed')}>
            <X aria-hidden /> Dismiss selected
          </Button>
        </div>
      )}

      {filtered.length === 0 ? (
        <EmptyState
          title={findings.length === 0 ? 'No findings' : `No ${status === 'all' ? '' : status} findings match`}
          description={findings.length === 0 ? 'The analysis produced no findings for this run.' : 'Try another status or clear the filters.'}
          action={findings.length > 0 ? <Button variant="outline" onClick={() => setSp(new URLSearchParams(), { replace: true })}>Clear filters</Button> : undefined}
        />
      ) : (
        <div className="flex flex-col gap-3">
          {filtered.map((f, i) => (
            <FindingCard
              key={f.id}
              finding={f}
              focused={i === focus}
              selected={selected.has(f.id)}
              onSelect={readOnly ? undefined : (v) => setSelected((s) => { const n = new Set(s); v ? n.add(f.id) : n.delete(f.id); return n; })}
              onDecide={readOnly ? undefined : (s) => decide([f.id], s)}
              readOnly={readOnly}
              extra={renderExtra?.(f)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
