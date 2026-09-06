import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ArrowRight, ClipboardCheck, GitCompare, Scale, Target, Save } from 'lucide-react';
import { toast } from 'sonner';
import type { CoPoCell, CourseOutcome, RunModule } from '@/lib/types/api';
import { useCoPoMap, useCourse, useOutcomes, useProgramOutcomes, usePutCoPoMap, usePutOutcomes, useRuns, useTopics } from '@/lib/queries';
import { PageHeader, QueryBoundary, LoadingState, ErrorState, EmptyState } from '@/components/feedback/states';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/primitives';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { EditableTable, type Column } from '@/components/data/EditableTable';
import { ArtefactUploader } from '@/components/domain/ArtefactUploader';
import { StatusBadge } from '@/components/domain/RunProgress';
import { BLOOM_LABEL, BLOOM_ORDER, MODULE_DESC, MODULE_LABEL, MODULE_PATH, cn, formatDate } from '@/lib/format';

const MODULE_ICON = { exam_audit: ClipboardCheck, attainment: Target, syllabus_check: GitCompare, calibration: Scale } as const;

type ORow = CourseOutcome & Record<string, unknown>;
function OutcomesEditor({ courseId }: { courseId: string }) {
  const q = useOutcomes(courseId);
  const save = usePutOutcomes(courseId);
  const [rows, setRows] = useState<ORow[]>([]);
  useEffect(() => { if (q.data) setRows(q.data as ORow[]); }, [q.data]);
  const dirty = JSON.stringify(rows) !== JSON.stringify(q.data ?? []);
  const cols: Column<ORow>[] = [
    { key: 'code', label: 'Code', width: '90px' },
    { key: 'text', label: 'Outcome statement', type: 'textarea' },
    { key: 'bloom_level', label: 'Bloom', type: 'select', width: '160px', options: BLOOM_ORDER.map((b) => ({ value: b, label: BLOOM_LABEL[b] })) },
    { key: 'weight', label: 'Weight', type: 'number', width: '100px' },
  ];
  if (q.isPending) return <LoadingState />;
  if (q.isError) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  return (
    <div className="flex flex-col gap-3">
      <EditableTable rows={rows} columns={cols} onChange={setRows} rowLabel="outcome" newRow={() => ({ id: `new-${Date.now()}`, code: `CO${rows.length + 1}`, text: '', bloom_level: null, weight: 1 })} />
      <div className="flex justify-end">
        <Button
          disabled={!dirty}
          loading={save.isPending}
          onClick={() => save.mutate(rows.map((r) => ({ id: r.id.startsWith('new-') ? undefined : r.id, code: r.code, text: r.text, bloom_level: r.bloom_level, weight: Number(r.weight) })), { onSuccess: () => toast.success('Outcomes saved') })}
        >
          <Save aria-hidden /> Save outcomes
        </Button>
      </div>
    </div>
  );
}

function CoPoEditor({ courseId }: { courseId: string }) {
  const cos = useOutcomes(courseId);
  const pos = useProgramOutcomes();
  const map = useCoPoMap(courseId);
  const save = usePutCoPoMap(courseId);
  const [cells, setCells] = useState<CoPoCell[]>([]);
  useEffect(() => { if (map.data) setCells(map.data); }, [map.data]);
  const get = (co: string, po: string) => cells.find((c) => c.co_id === co && c.po_id === po)?.strength ?? 0;
  const cycle = (co: string, po: string) => {
    const next = ((get(co, po) + 1) % 4) as CoPoCell['strength'];
    setCells((prev) => [...prev.filter((c) => !(c.co_id === co && c.po_id === po)), ...(next ? [{ co_id: co, po_id: po, strength: next }] : [])]);
  };
  if (cos.isPending || pos.isPending || map.isPending) return <LoadingState />;
  if (cos.isError || pos.isError || map.isError) return <ErrorState error={cos.error ?? pos.error ?? map.error} onRetry={() => { void cos.refetch(); void pos.refetch(); void map.refetch(); }} />;
  if (cos.data.length === 0) return <EmptyState title="Add course outcomes first" description="The CO→PO map needs at least one CO." />;
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm text-muted-foreground">Click a cell to cycle strength: 0 (none) → 1 (slight) → 2 (moderate) → 3 (substantial). Keyboard: Tab to a cell, press Space.</p>
      <Table dense>
        <caption className="sr-only">CO to PO mapping strengths</caption>
        <TableHeader>
          <TableRow>
            <TableHead>CO \ PO</TableHead>
            {pos.data.map((p) => (
              <TableHead key={p.id} className="text-center" title={p.text}>{p.code}</TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {cos.data.map((co) => (
            <TableRow key={co.id}>
              <TableCell className="font-semibold">{co.code}</TableCell>
              {pos.data.map((p) => {
                const s = get(co.id, p.id);
                return (
                  <TableCell key={p.id} className="p-1 text-center">
                    <button
                      type="button"
                      onClick={() => cycle(co.id, p.id)}
                      aria-label={`${co.code} to ${p.code}: strength ${s}`}
                      className={cn(
                        'h-9 w-9 rounded-md border text-sm font-semibold tabular transition-colors duration-fast cursor-pointer',
                        s === 0 && 'bg-card text-muted-foreground',
                        s === 1 && 'bg-primary/15 text-primary border-primary/30',
                        s === 2 && 'bg-primary/40 text-primary-foreground border-primary/50',
                        s === 3 && 'bg-primary text-primary-foreground border-primary',
                      )}
                    >
                      {s || '·'}
                    </button>
                  </TableCell>
                );
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
      <div className="flex justify-end">
        <Button loading={save.isPending} onClick={() => save.mutate(cells, { onSuccess: () => toast.success('CO→PO map saved') })}>
          <Save aria-hidden /> Save mapping
        </Button>
      </div>
    </div>
  );
}

function TopicsList({ courseId }: { courseId: string }) {
  const t = useTopics(courseId);
  return (
    <QueryBoundary query={t} empty={<EmptyState title="No topics yet" description="Upload a syllabus; topics are extracted automatically and shown here." />}>
      {(topics) => (
        <ul className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {topics.map((x) => (
            <li key={x.id} className="flex gap-2 rounded-md border bg-card px-3 py-2 text-sm">
              <span className="font-mono text-xs text-muted-foreground">{x.code}</span> {x.title}
            </li>
          ))}
        </ul>
      )}
    </QueryBoundary>
  );
}

function RunsList({ courseId }: { courseId: string }) {
  const runs = useRuns(courseId);
  return (
    <QueryBoundary query={runs} isEmpty={(d) => d.items.length === 0} empty={<EmptyState title="No analyses yet" description="Start one of the four modules above." />}>
      {(d) => (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Module</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Started</TableHead>
              <TableHead className="text-right">Progress</TableHead>
              <TableHead><span className="sr-only">Open</span></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {d.items.map((r) => (
              <TableRow key={r.id}>
                <TableCell className="font-medium">{MODULE_LABEL[r.module]}</TableCell>
                <TableCell><StatusBadge status={r.status} /></TableCell>
                <TableCell className="text-muted-foreground">{formatDate(r.created_at)}</TableCell>
                <TableCell className="text-right tabular">{Math.round(r.progress_pct)}%</TableCell>
                <TableCell className="text-right">
                  <Button asChild variant="ghost" size="sm">
                    <Link to={`/courses/${courseId}/${MODULE_PATH[r.module]}/${r.id}`}>Open <ArrowRight aria-hidden /></Link>
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </QueryBoundary>
  );
}

export function CoursePage() {
  const { id = '' } = useParams();
  const course = useCourse(id);
  const modules = useMemo(() => Object.keys(MODULE_LABEL) as RunModule[], []);

  return (
    <QueryBoundary query={course} rows={6}>
      {(c) => (
        <>
          <PageHeader
            eyebrow={<span className="font-mono">{c.code}{c.term ? ` · ${c.term}` : ''}</span>}
            title={<span className="flex flex-wrap items-center gap-3">{c.title}{c.is_demo && <Badge variant="secondary">Demo</Badge>}</span>}
            description={c.description ?? undefined}
          />

          <section aria-labelledby="modules-h" className="mb-8">
            <h2 id="modules-h" className="sr-only">Analysis modules</h2>
            <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              {modules.map((m) => {
                const Icon = MODULE_ICON[m];
                return (
                  <li key={m}>
                    <Link to={`/courses/${id}/${MODULE_PATH[m]}/new`} className="group flex h-full flex-col gap-2 rounded-lg border bg-card p-4 transition-[border-color,box-shadow] duration-fast hover:border-primary/60 hover:shadow-md">
                      <span className="flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary"><Icon className="h-5 w-5" aria-hidden /></span>
                      <span className="font-semibold">{MODULE_LABEL[m]}</span>
                      <span className="text-sm text-muted-foreground">{MODULE_DESC[m]}</span>
                      <span className="mt-auto flex items-center gap-1 pt-1 text-sm font-semibold text-primary">Start <ArrowRight className="h-4 w-4 transition-transform duration-fast group-hover:translate-x-0.5" aria-hidden /></span>
                    </Link>
                  </li>
                );
              })}
            </ul>
          </section>

          <Tabs defaultValue="artefacts">
            <TabsList aria-label="Course sections">
              <TabsTrigger value="artefacts">Artefacts</TabsTrigger>
              <TabsTrigger value="outcomes">Outcomes</TabsTrigger>
              <TabsTrigger value="copo">CO→PO map</TabsTrigger>
              <TabsTrigger value="topics">Topics</TabsTrigger>
              <TabsTrigger value="runs">Runs</TabsTrigger>
            </TabsList>
            <TabsContent value="artefacts" className="grid gap-4 lg:grid-cols-2">
              <ArtefactUploader courseId={id} kind="syllabus" />
              <ArtefactUploader courseId={id} kind="question_paper" />
              <ArtefactUploader courseId={id} kind="marks_sheet" />
              <ArtefactUploader courseId={id} kind="rubric" />
              <ArtefactUploader courseId={id} kind="answer_set" />
            </TabsContent>
            <TabsContent value="outcomes"><OutcomesEditor courseId={id} /></TabsContent>
            <TabsContent value="copo"><CoPoEditor courseId={id} /></TabsContent>
            <TabsContent value="topics"><TopicsList courseId={id} /></TabsContent>
            <TabsContent value="runs"><RunsList courseId={id} /></TabsContent>
          </Tabs>
        </>
      )}
    </QueryBoundary>
  );
}
