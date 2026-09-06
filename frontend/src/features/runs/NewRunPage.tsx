import { useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Play } from 'lucide-react';
import { toast } from 'sonner';
import type { RunCreate, RunModule } from '@/lib/types/api';
import { useArtefacts, useCourse, useCourses, useCreateRun, useOutcomes } from '@/lib/queries';
import { PageHeader, QueryBoundary } from '@/components/feedback/states';
import { ArtefactUploader } from '@/components/domain/ArtefactUploader';
import { Button } from '@/components/ui/button';
import { Field, Input } from '@/components/ui/input';
import { Checkbox } from '@/components/ui/primitives';
import { MODULE_DESC, MODULE_LABEL, MODULE_PATH } from '@/lib/format';

function Step({ n, title, children, hint }: { n: number; title: string; hint?: string; children: React.ReactNode }) {
  return (
    <section aria-labelledby={`step-${n}`} className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground tabular" aria-hidden>{n}</span>
        <h2 id={`step-${n}`} className="text-lg font-semibold">{title}</h2>
        {hint && <span className="text-sm text-muted-foreground">{hint}</span>}
      </div>
      {children}
    </section>
  );
}

function toggle(list: string[], id: string) {
  return list.includes(id) ? list.filter((x) => x !== id) : [...list, id];
}

export function NewRunPage({ module }: { module: RunModule }) {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const course = useCourse(id);
  const create = useCreateRun(id);

  const [draft, setDraft] = useState<string | null>(null);
  const [past, setPast] = useState<string[]>([]);
  const [marks, setMarks] = useState<string | null>(null);
  const [paper, setPaper] = useState<string | null>(null);
  const [threshold, setThreshold] = useState('60');
  const [syllabus, setSyllabus] = useState<string | null>(null);
  const [compare, setCompare] = useState<string[]>([]);
  const [rubric, setRubric] = useState<string | null>(null);
  const [answers, setAnswers] = useState<string | null>(null);

  const papers = useArtefacts(id, 'question_paper');
  const courses = useCourses();
  const cos = useOutcomes(id);

  const body = useMemo<RunCreate | null>(() => {
    switch (module) {
      case 'exam_audit':
        return draft ? { module, inputs: { draft_artefact_id: draft, past_artefact_ids: past } } : null;
      case 'attainment': {
        const t = Number(threshold);
        return marks && paper && t >= 1 && t <= 100 ? { module, inputs: { marks_artefact_id: marks, paper_artefact_id: paper, threshold: t } } : null;
      }
      case 'syllabus_check':
        return syllabus && compare.length > 0 ? { module, inputs: { syllabus_artefact_id: syllabus, compare_course_ids: compare } } : null;
      case 'calibration':
        return rubric && answers ? { module, inputs: { rubric_artefact_id: rubric, answer_set_artefact_id: answers } } : null;
    }
  }, [module, draft, past, marks, paper, threshold, syllabus, compare, rubric, answers]);

  const readyPapers = (papers.data ?? []).filter((a) => a.status === 'done');
  const noCos = cos.data && cos.data.length === 0;

  const start = () => {
    if (!body) return;
    create.mutate(body, {
      onSuccess: (r) => nav(`/courses/${id}/${MODULE_PATH[module]}/${r.id}`),
      onError: (e) => toast.error(e.message),
    });
  };

  return (
    <QueryBoundary query={course} rows={6}>
      {(c) => (
        <>
          <PageHeader eyebrow={<span className="font-mono">{c.code}</span>} title={`New ${MODULE_LABEL[module].toLowerCase()}`} description={MODULE_DESC[module]} />
          {noCos && module !== 'syllabus_check' && (
            <p role="status" className="mb-6 rounded-md border border-sev-medium-fg/30 bg-sev-medium p-3 text-sm text-sev-medium-fg">
              This course has no course outcomes yet — coverage and attainment will be empty. Add COs from the course overview first.
            </p>
          )}
          <div className="flex flex-col gap-8">
            {module === 'exam_audit' && (
              <>
                <Step n={1} title="Draft paper to audit" hint="one, extraction confirmed">
                  <ArtefactUploader courseId={id} kind="question_paper" selected={draft ? [draft] : []} onSelect={setDraft} title="Question papers" />
                </Step>
                <Step n={2} title="Past papers to compare against" hint="optional, for repeated questions">
                  {readyPapers.filter((a) => a.id !== draft).length === 0 ? (
                    <p className="text-sm text-muted-foreground">Upload another paper above to enable duplicate detection.</p>
                  ) : (
                    <ul className="flex flex-col gap-2">
                      {readyPapers.filter((a) => a.id !== draft).map((a) => (
                        <li key={a.id} className="flex items-center gap-3 rounded-md border bg-card px-3 py-2">
                          <Checkbox id={`past-${a.id}`} checked={past.includes(a.id)} onCheckedChange={() => setPast(toggle(past, a.id))} />
                          <label htmlFor={`past-${a.id}`} className="cursor-pointer text-sm">{a.label}{a.year ? ` (${a.year})` : ''}</label>
                        </li>
                      ))}
                    </ul>
                  )}
                </Step>
              </>
            )}

            {module === 'attainment' && (
              <>
                <Step n={1} title="Marks sheet">
                  <ArtefactUploader courseId={id} kind="marks_sheet" selected={marks ? [marks] : []} onSelect={setMarks} />
                </Step>
                <Step n={2} title="Question paper the marks belong to" hint="questions must be mapped to COs">
                  <ArtefactUploader courseId={id} kind="question_paper" selected={paper ? [paper] : []} onSelect={setPaper} />
                </Step>
                <Step n={3} title="Attainment threshold">
                  <Field id="threshold" label="Percent of max marks a student must score for a CO to count as attained" hint="AUST OBE guideline default is 60%.">
                    <Input type="number" inputMode="numeric" min={1} max={100} value={threshold} onChange={(e) => setThreshold(e.target.value)} className="w-32 tabular" />
                  </Field>
                </Step>
              </>
            )}

            {module === 'syllabus_check' && (
              <>
                <Step n={1} title="Syllabus of this course">
                  <ArtefactUploader courseId={id} kind="syllabus" selected={syllabus ? [syllabus] : []} onSelect={setSyllabus} />
                </Step>
                <Step n={2} title="Courses to compare against" hint="at least one">
                  <QueryBoundary query={courses} isEmpty={(d) => d.items.filter((x) => x.id !== id).length === 0} empty={<p className="text-sm text-muted-foreground">No other courses available. Create one or load the demo.</p>}>
                    {(d) => (
                      <ul className="grid gap-2 sm:grid-cols-2">
                        {d.items.filter((x) => x.id !== id).map((x) => (
                          <li key={x.id} className="flex items-center gap-3 rounded-md border bg-card px-3 py-2">
                            <Checkbox id={`cmp-${x.id}`} checked={compare.includes(x.id)} onCheckedChange={() => setCompare(toggle(compare, x.id))} />
                            <label htmlFor={`cmp-${x.id}`} className="cursor-pointer text-sm"><span className="font-mono font-semibold">{x.code}</span> {x.title}</label>
                          </li>
                        ))}
                      </ul>
                    )}
                  </QueryBoundary>
                </Step>
              </>
            )}

            {module === 'calibration' && (
              <>
                <Step n={1} title="Rubric">
                  <ArtefactUploader courseId={id} kind="rubric" selected={rubric ? [rubric] : []} onSelect={setRubric} />
                </Step>
                <Step n={2} title="Answer set with grader scores" hint="anonymised">
                  <ArtefactUploader courseId={id} kind="answer_set" selected={answers ? [answers] : []} onSelect={setAnswers} />
                </Step>
              </>
            )}

            {/* pr-44 keeps the primary action clear of the fixed Assistant button (bottom-right) */}
            <div className="sticky bottom-0 -mx-4 flex items-center justify-between gap-3 border-t bg-background/95 px-4 py-3 pr-44 md:-mx-8 md:px-8 md:pr-48">
              <p className="text-sm text-muted-foreground">{body ? 'Ready. The run takes about 10–20 seconds.' : 'Select the required inputs above to start.'}</p>
              <Button size="lg" disabled={!body} loading={create.isPending} onClick={start}>
                <Play aria-hidden /> Run analysis
              </Button>
            </div>
          </div>
        </>
      )}
    </QueryBoundary>
  );
}
