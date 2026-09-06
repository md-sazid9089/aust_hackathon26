import { Plus, Trash2 } from 'lucide-react';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input, Textarea } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/primitives';
import { cn } from '@/lib/format';

export type Column<R> = {
  key: keyof R & string;
  label: string;
  type?: 'text' | 'number' | 'textarea' | 'select' | 'readonly';
  options?: { value: string; label: string }[];
  width?: string;
  lang?: (row: R) => string | undefined;
  render?: (row: R, i: number) => React.ReactNode;
};

/**
 * Generic inline-editable table (architecture §15). Every cell is a real form control
 * so Tab/Shift-Tab navigate; row add/delete are explicit buttons.
 */
export function EditableTable<R extends Record<string, unknown>>({
  rows,
  columns,
  onChange,
  newRow,
  readOnly,
  rowLabel = 'row',
  caption,
}: {
  rows: R[];
  columns: Column<R>[];
  onChange: (rows: R[]) => void;
  newRow?: () => R;
  readOnly?: boolean;
  rowLabel?: string;
  caption?: string;
}) {
  const update = (i: number, key: keyof R, value: unknown) => onChange(rows.map((r, idx) => (idx === i ? { ...r, [key]: value } : r)));
  const remove = (i: number) => onChange(rows.filter((_, idx) => idx !== i));

  return (
    <div className="flex flex-col gap-3">
      <Table dense>
        {caption && <caption className="sr-only">{caption}</caption>}
        <TableHeader>
          <TableRow>
            <TableHead className="w-10">#</TableHead>
            {columns.map((c) => (
              <TableHead key={c.key} style={c.width ? { width: c.width } : undefined}>
                {c.label}
              </TableHead>
            ))}
            {!readOnly && <TableHead className="w-12"><span className="sr-only">Actions</span></TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row, i) => (
            <TableRow key={(row.id as string | undefined) ?? i}>
              <TableCell className="tabular text-muted-foreground">{i + 1}</TableCell>
              {columns.map((c) => {
                const v = row[c.key];
                const id = `${c.key}-${i}`;
                const label = `${c.label}, ${rowLabel} ${i + 1}`;
                if (c.render) return <TableCell key={c.key}>{c.render(row, i)}</TableCell>;
                if (readOnly || c.type === 'readonly')
                  return (
                    <TableCell key={c.key} lang={c.lang?.(row)} className={cn(c.type === 'number' && 'tabular')}>
                      {String(v ?? '')}
                    </TableCell>
                  );
                if (c.type === 'select')
                  return (
                    <TableCell key={c.key}>
                      <Select value={String(v ?? '')} onValueChange={(val) => update(i, c.key, val || null)}>
                        <SelectTrigger id={id} aria-label={label} className="h-9 text-sm">
                          <SelectValue placeholder="—" />
                        </SelectTrigger>
                        <SelectContent>
                          {c.options?.map((o) => (
                            <SelectItem key={o.value} value={o.value}>
                              {o.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </TableCell>
                  );
                if (c.type === 'textarea')
                  return (
                    <TableCell key={c.key}>
                      <Textarea
                        id={id}
                        aria-label={label}
                        lang={c.lang?.(row)}
                        value={String(v ?? '')}
                        onChange={(e) => update(i, c.key, e.target.value)}
                        className="min-h-[60px] resize-none overflow-hidden text-sm leading-relaxed field-sizing-content"
                        rows={2}
                        ref={(el) => {
                          // Fallback auto-grow for browsers without CSS field-sizing.
                          if (!el) return;
                          el.style.height = 'auto';
                          el.style.height = `${el.scrollHeight}px`;
                        }}
                      />
                    </TableCell>
                  );
                if (c.type === 'number')
                  return (
                    <TableCell key={c.key}>
                      <Input id={id} aria-label={label} type="number" inputMode="decimal" step="any" value={v as number} onChange={(e) => update(i, c.key, e.target.value === '' ? 0 : Number(e.target.value))} className="h-9 w-24 text-sm tabular" />
                    </TableCell>
                  );
                return (
                  <TableCell key={c.key}>
                    <Input id={id} aria-label={label} lang={c.lang?.(row)} value={String(v ?? '')} onChange={(e) => update(i, c.key, e.target.value)} className="h-9 text-sm" />
                  </TableCell>
                );
              })}
              {!readOnly && (
                <TableCell>
                  <Button variant="ghost" size="icon-sm" onClick={() => remove(i)} aria-label={`Delete ${rowLabel} ${i + 1}`}>
                    <Trash2 aria-hidden />
                  </Button>
                </TableCell>
              )}
            </TableRow>
          ))}
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={columns.length + 2} className="py-8 text-center text-muted-foreground">
                No {rowLabel}s yet.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
      {!readOnly && newRow && (
        <Button variant="outline" size="sm" className="self-start" onClick={() => onChange([...rows, newRow()])}>
          <Plus aria-hidden /> Add {rowLabel}
        </Button>
      )}
    </div>
  );
}
