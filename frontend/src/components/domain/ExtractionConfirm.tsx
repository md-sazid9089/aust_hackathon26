import { useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import type { Answer, Artefact, Question, QuestionIn, RubricCriterion } from '@/lib/types/api';
import { useAnswers, useMarks, useOutcomes, usePutAnswers, usePutQuestions, usePutRubric, useQuestions, useRubric, useTopics } from '@/lib/queries';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { LoadingState, ErrorState } from '@/components/feedback/states';
import { EditableTable, type Column } from '@/components/data/EditableTable';
import { ComputedLabel } from './trust';
import { KIND_LABEL, cn } from '@/lib/format';

const bn = (s: string) => (/[\u0980-\u09FF]/.test(s) ? 'bn' : undefined);

/* ---------- question paper ---------- */
type QRow = Question & Record<string, unknown>;
function QuestionsEditor({ courseId, artefactId, onClose }: { courseId: string; artefactId: string; onClose: () => void }) {
  const q = useQuestions(artefactId);
  const cos = useOutcomes(courseId);
  const save = usePutQuestions(artefactId);
  const [rows, setRows] = useState<QRow[]>([]);
  useEffect(() => { if (q.data) setRows(q.data as QRow[]); }, [q.data]);

  const total = useMemo(() => rows.reduce((s, r) => s + (Number(r.marks) || 0), 0), [rows]);
  const cols: Column<QRow>[] = [
    { key: 'number', label: 'No.', width: '72px' },
    { key: 'text', label: 'Question text', type: 'textarea', lang: (r) => bn(r.text) },
    { key: 'marks', label: 'Marks', type: 'number', width: '110px' },
    {
      key: 'co_ids',
      label: 'Mapped COs',
      render: (r, i) => (
        <div className="flex flex-wrap gap-1" role="group" aria-label={`COs for question ${r.number}`}>
          {(cos.data ?? []).map((co) => {
            const on = r.co_ids.includes(co.id);
            return (
              <button
                key={co.id}
                type="button"
                aria-pressed={on}
                onClick={() => setRows(rows.map((x, idx) => (idx === i ? { ...x, co_ids: on ? x.co_ids.filter((c) => c !== co.id) : [...x.co_ids, co.id] } : x)))}
                className={cn('rounded-sm border px-2 py-0.5 text-xs font-semibold transition-colors duration-fast cursor-pointer', on ? 'border-primary bg-primary text-primary-foreground' : 'bg-card text-muted-foreground hover:bg-muted')}
              >
                {co.code}
              </button>
            );
          })}
        </div>
      ),
    },
  ];

  if (q.isPending) return <LoadingState />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  return (
    <>
      <EditableTable
        rows={rows}
        columns={cols}
        onChange={setRows}
        rowLabel="question"
        caption="Extracted questions; edit any cell before confirming."
        newRow={() => ({ id: `new-${Date.now()}`, number: String(rows.length + 1), text: '', marks: 0, bloom_level: null, co_ids: [], topic_ids: [] })}
      />
      <div className="flex items-center justify-between text-sm">
        <span className="flex items-center gap-2">
          <ComputedLabel /> {rows.length} questions · total <strong className="tabular">{total}</strong> marks
        </span>
        <span className="text-muted-foreground">{rows.filter((r) => r.co_ids.length === 0).length} unmapped</span>
      </div>
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button
          loading={save.isPending}
          onClick={() =>
            save.mutate(
              {
                rows: rows.map<QuestionIn>((r) => ({ id: r.id.startsWith('new-') ? undefined : r.id, number: r.number, text: r.text, marks: Number(r.marks) })),
                coMap: rows.filter((r) => !r.id.startsWith('new-')).map((r) => ({ question_id: r.id, co_ids: r.co_ids })),
              },
              { onSuccess: () => { toast.success('Questions confirmed'); onClose(); } },
            )
          }
        >
          Confirm extraction
        </Button>
      </DialogFooter>
    </>
  );
}

/* ---------- marks sheet (read-only preview) ---------- */
function MarksPreview({ artefactId, onClose }: { artefactId: string; onClose: () => void }) {
  const m = useMarks(artefactId);
  if (m.isPending) return <LoadingState />;
  if (m.isError) return <ErrorState error={m.error} onRetry={() => m.refetch()} />;
  const d = m.data;
  const preview = d.rows.slice(0, 8);
  return (
    <>
      <p className="flex items-center gap-2 text-sm">
        <ComputedLabel /> {d.students} students · {d.questions.length} questions · max {d.questions.reduce((s, q) => s + q.max, 0)}
      </p>
      <Table dense>
        <TableHeader>
          <TableRow>
            <TableHead>Student</TableHead>
            {d.questions.map((q) => (
              <TableHead key={q.number} className="text-right">
                Q{q.number} <span className="font-normal">/{q.max}</span>
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {preview.map((r) => (
            <TableRow key={r.student_anon_id}>
              <TableCell className="font-mono text-xs">{r.student_anon_id}</TableCell>
              {d.questions.map((q) => (
                <TableCell key={q.number} className="text-right tabular">{r.scores[q.number] ?? '—'}</TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {d.rows.length > preview.length && <p className="text-xs text-muted-foreground">Showing {preview.length} of {d.rows.length} anonymised rows.</p>}
      <DialogFooter>
        <Button onClick={onClose}>Looks right</Button>
      </DialogFooter>
    </>
  );
}

/* ---------- rubric ---------- */
type RRow = RubricCriterion & Record<string, unknown>;
function RubricEditor({ artefactId, onClose }: { artefactId: string; onClose: () => void }) {
  const r = useRubric(artefactId);
  const save = usePutRubric(artefactId);
  const [rows, setRows] = useState<RRow[]>([]);
  useEffect(() => { if (r.data) setRows(r.data as RRow[]); }, [r.data]);
  if (r.isPending) return <LoadingState />;
  if (r.isError) return <ErrorState error={r.error} onRetry={() => r.refetch()} />;
  const cols: Column<RRow>[] = [
    { key: 'code', label: 'Code', width: '80px' },
    { key: 'text', label: 'Criterion', type: 'textarea', lang: (x) => bn(x.text) },
    { key: 'max_score', label: 'Max', type: 'number', width: '100px' },
    { key: 'levels', label: 'Levels', render: (x) => <span className="text-xs text-muted-foreground">{x.levels.map((l) => `${l.label} (${l.score})`).join(' · ')}</span> },
  ];
  return (
    <>
      <EditableTable rows={rows} columns={cols} onChange={setRows} rowLabel="criterion" newRow={() => ({ code: `C${rows.length + 1}`, text: '', max_score: 5, levels: [] })} />
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button loading={save.isPending} onClick={() => save.mutate(rows.map(({ id, code, text, max_score, levels }) => ({ id, code, text, max_score, levels })), { onSuccess: () => { toast.success('Rubric confirmed'); onClose(); } })}>
          Confirm rubric
        </Button>
      </DialogFooter>
    </>
  );
}

/* ---------- answer set ---------- */
type ARow = Answer & Record<string, unknown>;
function AnswersEditor({ artefactId, onClose }: { artefactId: string; onClose: () => void }) {
  const a = useAnswers(artefactId);
  const save = usePutAnswers(artefactId);
  const [rows, setRows] = useState<ARow[]>([]);
  useEffect(() => { if (a.data) setRows(a.data as ARow[]); }, [a.data]);
  if (a.isPending) return <LoadingState />;
  if (a.isError) return <ErrorState error={a.error} onRetry={() => a.refetch()} />;
  const cols: Column<ARow>[] = [
    { key: 'student_anon_id', label: 'Student', type: 'readonly', width: '110px' },
    { key: 'question_ref', label: 'Q', width: '70px' },
    { key: 'text', label: 'Answer', type: 'textarea', lang: (x) => bn(x.text) },
    {
      key: 'grader_scores',
      label: 'Grader scores',
      render: (x) => (
        <div className="flex flex-wrap gap-1">
          {x.grader_scores.map((g) => (
            <Badge key={`${g.grader_label}-${g.criterion_code}`} variant="secondary" className="tabular">
              {g.grader_label}·{g.criterion_code}: {g.score}
            </Badge>
          ))}
        </div>
      ),
    },
  ];
  return (
    <>
      <EditableTable rows={rows} columns={cols} onChange={setRows} rowLabel="answer" />
      <DialogFooter>
        <Button variant="outline" onClick={onClose}>Cancel</Button>
        <Button loading={save.isPending} onClick={() => save.mutate(rows.map(({ id, student_anon_id, question_ref, text, grader_scores }) => ({ id, student_anon_id, question_ref, text, grader_scores })), { onSuccess: () => { toast.success('Answers confirmed'); onClose(); } })}>
          Confirm answers
        </Button>
      </DialogFooter>
    </>
  );
}

/* ---------- syllabus (topics preview) ---------- */
function SyllabusPreview({ courseId, onClose }: { courseId: string; onClose: () => void }) {
  const t = useTopics(courseId);
  if (t.isPending) return <LoadingState />;
  if (t.isError) return <ErrorState error={t.error} onRetry={() => t.refetch()} />;
  return (
    <>
      <p className="flex items-center gap-2 text-sm"><ComputedLabel /> {t.data.length} topics extracted</p>
      <ul className="grid gap-1 sm:grid-cols-2">
        {t.data.map((x) => (
          <li key={x.id} className="flex gap-2 rounded-md border px-3 py-2 text-sm" lang={bn(x.title)}>
            <span className="font-mono text-xs text-muted-foreground">{x.code}</span> {x.title}
          </li>
        ))}
      </ul>
      <p className="text-xs text-muted-foreground">Edit course outcomes and topics from the course overview.</p>
      <DialogFooter>
        <Button onClick={onClose}>Done</Button>
      </DialogFooter>
    </>
  );
}

/** F-012 — humans confirm/edit extracted structure before it feeds any analysis. */
export function ExtractionConfirm({ courseId, artefact, open, onOpenChange }: { courseId: string; artefact: Artefact; open: boolean; onOpenChange: (v: boolean) => void }) {
  const close = () => onOpenChange(false);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent size="xl">
        <DialogHeader>
          <DialogTitle>Review extraction — {artefact.label}</DialogTitle>
          <DialogDescription>
            {KIND_LABEL[artefact.kind]} · detected language {artefact.lang.toUpperCase()}. Fix anything the extractor got wrong; nothing runs until you confirm.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4">
          {artefact.kind === 'question_paper' && <QuestionsEditor courseId={courseId} artefactId={artefact.id} onClose={close} />}
          {artefact.kind === 'marks_sheet' && <MarksPreview artefactId={artefact.id} onClose={close} />}
          {artefact.kind === 'rubric' && <RubricEditor artefactId={artefact.id} onClose={close} />}
          {artefact.kind === 'answer_set' && <AnswersEditor artefactId={artefact.id} onClose={close} />}
          {artefact.kind === 'syllabus' && <SyllabusPreview courseId={courseId} onClose={close} />}
        </div>
      </DialogContent>
    </Dialog>
  );
}
