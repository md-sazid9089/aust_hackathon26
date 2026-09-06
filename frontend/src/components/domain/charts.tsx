import { useState } from 'react';
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip as RTooltip, XAxis, YAxis, ReferenceLine } from 'recharts';
import { BarChart3, TableProperties } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { ComputedLabel } from './trust';

export type BarDatum = { label: string; value: number; secondary?: number; tone?: 'ok' | 'warn' | 'bad' | 'neutral' };

const TONE: Record<NonNullable<BarDatum['tone']>, string> = {
  ok: 'hsl(var(--success))',
  warn: 'hsl(var(--sev-medium-fg))',
  bad: 'hsl(var(--sev-high-fg))',
  neutral: 'hsl(var(--primary))',
};

/**
 * Bar chart with a table toggle. Values are always printed (labels + table), so the chart
 * never carries information on its own (MASTER.md rationale: charts with printed values).
 */
export function BarWithTable({
  title,
  data,
  valueLabel,
  secondaryLabel,
  unit = '%',
  reference,
  height = 240,
}: {
  title: string;
  data: BarDatum[];
  valueLabel: string;
  secondaryLabel?: string;
  unit?: string;
  reference?: number;
  height?: number;
}) {
  const [view, setView] = useState<'chart' | 'table'>('chart');
  const fmt = (n: number) => `${Number.isInteger(n) ? n : n.toFixed(1)}${unit}`;
  return (
    <section aria-labelledby={`chart-${title}`} className="rounded-lg border bg-card p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 id={`chart-${title}`} className="font-semibold">{title}</h3>
        <div className="flex items-center gap-2">
          <ComputedLabel />
          <div role="group" aria-label="View as" className="flex rounded-md border">
            <Button size="icon-sm" variant={view === 'chart' ? 'secondary' : 'ghost'} aria-pressed={view === 'chart'} onClick={() => setView('chart')} aria-label="Chart view"><BarChart3 aria-hidden /></Button>
            <Button size="icon-sm" variant={view === 'table' ? 'secondary' : 'ghost'} aria-pressed={view === 'table'} onClick={() => setView('table')} aria-label="Table view"><TableProperties aria-hidden /></Button>
          </div>
        </div>
      </div>
      {view === 'chart' ? (
        <div style={{ height }} role="img" aria-label={`${title}: ${data.map((d) => `${d.label} ${fmt(d.value)}`).join(', ')}`}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data} margin={{ top: 20, right: 16, left: 0, bottom: 0 }}>
              <CartesianGrid vertical={false} stroke="hsl(var(--border))" />
              <XAxis dataKey="label" tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 13 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 13 }} axisLine={false} tickLine={false} width={36} tickFormatter={(v: number) => `${v}${unit}`} />
              <RTooltip cursor={{ fill: 'hsl(var(--muted))' }} contentStyle={{ background: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: 8, color: 'hsl(var(--popover-foreground))', fontSize: 14 }} formatter={(v: number) => fmt(v)} />
              {reference !== undefined && <ReferenceLine y={reference} stroke="hsl(var(--foreground))" strokeDasharray="4 4" label={{ value: `target ${reference}${unit}`, position: 'insideBottomLeft', fill: 'hsl(var(--foreground))', fontSize: 12, fontWeight: 600 }} />}
              <Bar dataKey="value" name={valueLabel} radius={[4, 4, 0, 0]} label={{ position: 'top', fill: 'hsl(var(--foreground))', fontSize: 13, formatter: (v: number) => fmt(v) }} isAnimationActive={false}>
                {data.map((d, i) => <Cell key={i} fill={TONE[d.tone ?? 'neutral']} />)}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <Table dense>
          <TableHeader>
            <TableRow>
              <TableHead>Item</TableHead>
              <TableHead className="text-right">{valueLabel}</TableHead>
              {secondaryLabel && <TableHead className="text-right">{secondaryLabel}</TableHead>}
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((d) => (
              <TableRow key={d.label}>
                <TableCell className="font-medium">{d.label}</TableCell>
                <TableCell className="text-right tabular">{fmt(d.value)}</TableCell>
                {secondaryLabel && <TableCell className="text-right tabular">{d.secondary !== undefined ? fmt(d.secondary) : '—'}</TableCell>}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </section>
  );
}
