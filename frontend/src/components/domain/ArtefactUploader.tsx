import { useState } from 'react';
import { Upload, FileText, Loader2, AlertTriangle, CheckCircle2, RefreshCw, Trash2, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import type { Artefact, ArtefactKind } from '@/lib/types/api';
import { useArtefacts, useDeleteArtefact, useReextract, useUploadArtefact } from '@/lib/queries';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Field, Input, Textarea } from '@/components/ui/input';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/primitives';
import { LoadingState, ErrorState } from '@/components/feedback/states';
import { KIND_LABEL, cn, relTime } from '@/lib/format';
import { ExtractionConfirm } from './ExtractionConfirm';

const ACCEPT: Record<ArtefactKind, string> = {
  syllabus: '.pdf,.docx,.txt',
  question_paper: '.pdf,.docx,.txt',
  marks_sheet: '.csv,.xlsx',
  rubric: '.pdf,.docx,.csv,.txt',
  answer_set: '.csv,.xlsx,.txt',
};

export function ExtractionBadge({ a }: { a: Artefact }) {
  if (a.status === 'done')
    return (
      <Badge variant="success">
        <CheckCircle2 className="h-3 w-3" aria-hidden /> Extracted
      </Badge>
    );
  if (a.status === 'failed')
    return (
      <Badge variant="destructive">
        <AlertTriangle className="h-3 w-3" aria-hidden /> Failed
      </Badge>
    );
  return (
    <Badge variant="secondary">
      <Loader2 className="h-3 w-3 animate-spin" aria-hidden /> {a.status === 'pending' ? 'Queued' : 'Extracting'}
    </Badge>
  );
}

function UploadDialog({ courseId, kind, open, onOpenChange }: { courseId: string; kind: ArtefactKind; open: boolean; onOpenChange: (v: boolean) => void }) {
  const up = useUploadArtefact(courseId);
  const [label, setLabel] = useState('');
  const [year, setYear] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [text, setText] = useState('');
  const [graders, setGraders] = useState('A, B');
  const [err, setErr] = useState<string | null>(null);

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!label.trim()) return setErr('Give this artefact a label (e.g. "Final 2025 draft").');
    if (!file && !text.trim()) return setErr('Choose a file or paste text.');
    setErr(null);
    up.mutate(
      {
        kind,
        label: label.trim(),
        year: year ? Number(year) : undefined,
        file: file ?? undefined,
        text: text.trim() || undefined,
        grader_labels: kind === 'answer_set' ? graders.split(',').map((s) => s.trim()).filter(Boolean) : undefined,
      },
      {
        onSuccess: () => {
          toast.success('Uploaded — extraction started');
          onOpenChange(false);
          setLabel(''); setYear(''); setFile(null); setText('');
        },
        onError: (e) => setErr(e.message),
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Upload {KIND_LABEL[kind].toLowerCase()}</DialogTitle>
          <DialogDescription>Files stay private to your course. Text is extracted server-side; you confirm it before any analysis runs.</DialogDescription>
        </DialogHeader>
        <form onSubmit={submit} className="flex flex-col gap-4" noValidate>
          <Field id="up-label" label="Label" hint='e.g. "Final exam 2025 (draft)"'>
            <Input value={label} onChange={(e) => setLabel(e.target.value)} />
          </Field>
          <Field id="up-year" label="Year (optional)">
            <Input type="number" inputMode="numeric" value={year} onChange={(e) => setYear(e.target.value)} className="w-32 tabular" />
          </Field>
          {kind === 'answer_set' && (
            <Field id="up-graders" label="Grader labels" hint="Comma-separated; scores are anonymised.">
              <Input value={graders} onChange={(e) => setGraders(e.target.value)} />
            </Field>
          )}
          <Tabs defaultValue="file">
            <TabsList>
              <TabsTrigger value="file">File</TabsTrigger>
              <TabsTrigger value="text">Paste text</TabsTrigger>
            </TabsList>
            <TabsContent value="file">
              <label
                htmlFor="up-file"
                className={cn('flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors duration-fast hover:border-primary hover:bg-primary/5', file && 'border-primary')}
              >
                <Upload className="h-6 w-6 text-muted-foreground" aria-hidden />
                <span className="text-sm">{file ? file.name : `Choose a file (${ACCEPT[kind]})`}</span>
                <input id="up-file" type="file" accept={ACCEPT[kind]} className="sr-only" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
              </label>
            </TabsContent>
            <TabsContent value="text">
              <Textarea aria-label="Pasted text" value={text} onChange={(e) => setText(e.target.value)} rows={8} placeholder="Paste the document text here (Bangla or English)." />
            </TabsContent>
          </Tabs>
          {err && (
            <p role="alert" className="text-sm font-medium text-destructive">
              {err}
            </p>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
            <Button type="submit" loading={up.isPending}>
              Upload
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Lists artefacts of one kind, lets the user upload, re-extract, delete and — crucially —
 * confirm/edit extraction (F-012). Optional `selected`/`onSelect` turn rows into radio choices for run wizards.
 */
export function ArtefactUploader({
  courseId,
  kind,
  selected,
  onSelect,
  multi,
  title,
}: {
  courseId: string;
  kind: ArtefactKind;
  selected?: string[];
  onSelect?: (id: string) => void;
  multi?: boolean;
  title?: string;
}) {
  const q = useArtefacts(courseId, kind);
  const del = useDeleteArtefact(courseId);
  const re = useReextract(courseId);
  const [uploadOpen, setUploadOpen] = useState(false);
  const [editing, setEditing] = useState<Artefact | null>(null);

  return (
    <section aria-labelledby={`art-${kind}`} className="rounded-lg border bg-card">
      <header className="flex items-center justify-between gap-3 border-b px-4 py-3">
        <h2 id={`art-${kind}`} className="font-semibold">
          {title ?? KIND_LABEL[kind]}
        </h2>
        <Button size="sm" variant="outline" onClick={() => setUploadOpen(true)}>
          <Upload aria-hidden /> Upload
        </Button>
      </header>
      <div className="p-3">
        {q.isPending && <LoadingState rows={2} />}
        {q.isError && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
        {q.data && q.data.length === 0 && (
          <p className="px-1 py-6 text-center text-sm text-muted-foreground">No {KIND_LABEL[kind].toLowerCase()} uploaded yet.</p>
        )}
        {q.data && q.data.length > 0 && (
          <ul className="flex flex-col gap-2" role={onSelect ? (multi ? 'group' : 'radiogroup') : undefined}>
            {q.data.map((a) => {
              const isSel = selected?.includes(a.id);
              const selectable = !!onSelect && a.status === 'done';
              return (
                <li key={a.id} className={cn('flex flex-wrap items-center gap-3 rounded-md border p-3 transition-colors duration-fast', isSel && 'border-primary bg-primary/5')}>
                  {onSelect && (
                    <input
                      type={multi ? 'checkbox' : 'radio'}
                      name={`sel-${kind}`}
                      checked={!!isSel}
                      disabled={!selectable}
                      onChange={() => onSelect(a.id)}
                      aria-label={`Use ${a.label}`}
                      className="h-4 w-4 accent-primary cursor-pointer disabled:cursor-not-allowed"
                    />
                  )}
                  <FileText className="h-5 w-5 shrink-0 text-muted-foreground" aria-hidden />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium">{a.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {a.year ?? ''} {a.lang !== 'unknown' ? `· ${a.lang.toUpperCase()}` : ''} · {relTime(a.created_at)}
                      {a.counts && Object.entries(a.counts).map(([k, v]) => ` · ${v} ${k}`)}
                    </p>
                    {a.status === 'failed' && a.error && <p className="mt-1 text-xs text-destructive">{a.error}</p>}
                  </div>
                  <ExtractionBadge a={a} />
                  <div className="flex items-center gap-1">
                    {a.status === 'done' && (
                      <Button size="sm" variant="ghost" onClick={() => setEditing(a)}>
                        <Pencil aria-hidden /> Review
                      </Button>
                    )}
                    {a.status === 'failed' && (
                      <Button size="sm" variant="ghost" onClick={() => re.mutate(a.id)} loading={re.isPending}>
                        <RefreshCw aria-hidden /> Retry
                      </Button>
                    )}
                    <Button size="icon-sm" variant="ghost" aria-label={`Delete ${a.label}`} onClick={() => del.mutate(a.id, { onSuccess: () => toast.success('Deleted') })}>
                      <Trash2 aria-hidden />
                    </Button>
                  </div>
                </li>
              );
            })}
          </ul>
        )}
      </div>
      <UploadDialog courseId={courseId} kind={kind} open={uploadOpen} onOpenChange={setUploadOpen} />
      {editing && <ExtractionConfirm courseId={courseId} artefact={editing} open onOpenChange={(v) => !v && setEditing(null)} />}
    </section>
  );
}
