import type * as T from '@/lib/types/api';
import { ApiError, type Api, type RunEventHandlers } from '../types';
import * as F from './fixtures';
import * as E from './engine';

const LAT = () => 180 + Math.random() * 220;
const wait = (ms = LAT()) => new Promise((r) => setTimeout(r, ms));
const clone = <X>(x: X): X => JSON.parse(JSON.stringify(x));
const uid = (p: string) => `${p}-${Math.random().toString(36).slice(2, 10)}`;

interface RunRecord {
  run: T.Run;
  events: T.RunProgressEvent[];
  findings: T.Finding[];
  attainment?: T.AttainmentOut;
  prescores?: T.Prescore[];
  ownerEmail: string;
}

/** In-memory demo backend. `window.__fcDemo` exposes failure toggles for the demo. */
export class MockApi implements Api {
  private me_: T.Profile;
  private courses = clone(F.courses);
  private outcomes = clone(F.courseOutcomes);
  private coPo = clone(F.coPoMap);
  private topics = clone(F.topics);
  private artefacts = clone(F.artefacts);
  private questions = clone(F.questions);
  private rubric = clone(F.rubric);
  private answers = clone(F.answers);
  private runs = new Map<string, RunRecord>();
  private users: T.AdminUser[] = Object.values(F.profiles).map((p) => ({ ...p, courses: p.role === 'faculty' ? 2 : 0, runs: 0 }));
  /** Demo controls: next run ends 'partial' or 'failed'. */
  public nextRunOutcome: T.RunStatus | null = null;

  constructor(userId: string) {
    this.me_ = F.profiles[userId];
    this.load();
    (window as unknown as { __fcDemo: MockApi }).__fcDemo = this;
  }

  /** Finished runs survive reloads/HMR so a demo cannot lose its results. */
  private static STORE = 'fc-mock-runs';
  private load() {
    try {
      const raw = localStorage.getItem(MockApi.STORE);
      if (!raw) return;
      const arr = JSON.parse(raw) as RunRecord[];
      for (const rec of arr) if (['completed', 'partial', 'failed'].includes(rec.run.status)) this.runs.set(rec.run.id, rec);
    } catch {
      /* ignore corrupt storage */
    }
  }
  private persist() {
    try {
      const arr = [...this.runs.values()].filter((r) => ['completed', 'partial', 'failed'].includes(r.run.status));
      localStorage.setItem(MockApi.STORE, JSON.stringify(arr));
    } catch {
      /* quota or private mode */
    }
  }

  private notFound(code: string, what: string): never {
    throw new ApiError(404, code, `${what} not found`, uid('req'));
  }

  async me() {
    await wait(80);
    return clone(this.me_);
  }

  async listCourses(q?: string) {
    await wait();
    const items = this.courses
      .filter((c) => !q || `${c.code} ${c.title}`.toLowerCase().includes(q.toLowerCase()))
      .map((c) => ({ ...c, counts: this.countsFor(c.id) }));
    return { items: clone(items), page: 1, page_size: 100, total: items.length };
  }
  private countsFor(id: string) {
    return {
      artefacts: this.artefacts.filter((a) => a.course_id === id).length,
      runs: [...this.runs.values()].filter((r) => r.run.course_id === id).length,
      outcomes: (this.outcomes[id] ?? []).length,
    };
  }
  async getCourse(id: string) {
    await wait();
    const c = this.courses.find((x) => x.id === id) ?? this.notFound('COURSE_NOT_FOUND', 'Course');
    return { ...clone(c), counts: this.countsFor(id) };
  }
  async createCourse(body: T.CourseCreate) {
    await wait();
    const code = body.code.trim().toUpperCase();
    if (this.courses.some((c) => c.code === code)) throw new ApiError(409, 'COURSE_CODE_EXISTS', 'A course with this code already exists', uid('req'));
    const c: T.Course = { id: uid('c'), code, title: body.title, term: body.term ?? null, description: body.description ?? null, is_demo: false, created_at: new Date().toISOString(), counts: { artefacts: 0, runs: 0, outcomes: 0 } };
    this.courses.unshift(c);
    this.outcomes[c.id] = [];
    this.coPo[c.id] = [];
    this.topics[c.id] = [];
    return clone(c);
  }
  async updateCourse(id: string, body: Partial<T.CourseCreate>) {
    await wait();
    const c = this.courses.find((x) => x.id === id) ?? this.notFound('COURSE_NOT_FOUND', 'Course');
    Object.assign(c, body);
    return clone(c);
  }
  async deleteCourse(id: string) {
    await wait();
    this.courses = this.courses.filter((c) => c.id !== id);
  }
  async listRuns(courseId: string, filter?: { module?: T.RunModule; status?: T.RunStatus }) {
    await wait();
    const items = [...this.runs.values()]
      .map((r) => r.run)
      .filter((r) => r.course_id === courseId && (!filter?.module || r.module === filter.module) && (!filter?.status || r.status === filter.status))
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
    return { items: clone(items), page: 1, page_size: 100, total: items.length };
  }
  async seedDemo() {
    await wait(600);
    return { course_id: F.ids.course, created: false };
  }

  async listProgramOutcomes() {
    await wait();
    return clone(F.programOutcomes);
  }
  async listOutcomes(courseId: string) {
    await wait();
    return clone(this.outcomes[courseId] ?? []);
  }
  async putOutcomes(courseId: string, rows: T.CourseOutcomeIn[]) {
    await wait();
    this.outcomes[courseId] = rows.map((r) => ({ id: r.id ?? uid('co'), code: r.code, text: r.text, bloom_level: r.bloom_level ?? null, weight: r.weight ?? 1 }));
    return clone(this.outcomes[courseId]);
  }
  async getCoPoMap(courseId: string) {
    await wait();
    return clone(this.coPo[courseId] ?? []);
  }
  async putCoPoMap(courseId: string, cells: T.CoPoCell[]) {
    await wait();
    this.coPo[courseId] = clone(cells);
    return clone(cells);
  }
  async listTopics(courseId: string) {
    await wait();
    return clone(this.topics[courseId] ?? []);
  }
  async putTopics(courseId: string, rows: T.TopicIn[]) {
    await wait();
    this.topics[courseId] = rows.map((r, i) => ({ id: r.id ?? uid('t'), code: r.code, title: r.title, source_artefact_id: this.topics[courseId]?.[i]?.source_artefact_id ?? null }));
    return clone(this.topics[courseId]);
  }

  async listArtefacts(courseId: string, filter?: { kind?: T.ArtefactKind; status?: T.ExtractionStatus }) {
    await wait();
    return clone(this.artefacts.filter((a) => a.course_id === courseId && (!filter?.kind || a.kind === filter.kind) && (!filter?.status || a.status === filter.status)));
  }
  async getArtefact(id: string) {
    await wait(120);
    return clone(this.artefacts.find((a) => a.id === id) ?? this.notFound('ARTEFACT_NOT_FOUND', 'Artefact'));
  }
  async uploadArtefact(courseId: string, body: T.ArtefactUpload) {
    await wait(500);
    if (body.file && body.file.size > 10 * 1024 * 1024) throw new ApiError(413, 'FILE_TOO_LARGE', 'File exceeds 10 MB', uid('req'));
    const a: T.Artefact = {
      id: uid('a'),
      course_id: courseId,
      kind: body.kind,
      label: body.label,
      year: body.year ?? null,
      term: body.term ?? null,
      mime: body.file?.type ?? 'text/plain',
      lang: /[\u0980-\u09FF]/.test(body.text ?? '') ? 'bn' : 'en',
      status: 'extracting',
      error: null,
      created_at: new Date().toISOString(),
    };
    this.artefacts.unshift(a);
    // simulate extraction: copy a fixture of the same kind so downstream pages work
    setTimeout(() => {
      const rec = this.artefacts.find((x) => x.id === a.id);
      if (!rec) return;
      if (body.kind === 'question_paper') {
        this.questions[a.id] = clone(F.questions[F.ids.paper2025]).map((q, i) => ({ ...q, id: `${a.id}-q${i}` }));
        rec.counts = { questions: this.questions[a.id].length };
      } else if (body.kind === 'rubric') {
        this.rubric[a.id] = clone(F.rubric[F.ids.rubric]);
        rec.counts = { criteria: 4 };
      } else if (body.kind === 'answer_set') {
        this.answers[a.id] = clone(F.answers[F.ids.answers]);
        rec.counts = { answers: 6 };
      } else if (body.kind === 'syllabus') {
        rec.counts = { topics: this.topics[courseId]?.length ?? 0 };
      } else rec.counts = { students: 42, questions: 8 };
      rec.status = 'done';
    }, 2500);
    return clone(a);
  }
  async deleteArtefact(id: string) {
    await wait();
    if ([...this.runs.values()].some((r) => JSON.stringify(r.run.inputs).includes(id))) throw new ApiError(409, 'ARTEFACT_IN_USE', 'Artefact is referenced by a completed run', uid('req'));
    this.artefacts = this.artefacts.filter((a) => a.id !== id);
  }
  async reextract(id: string) {
    await wait();
    const a = this.artefacts.find((x) => x.id === id) ?? this.notFound('ARTEFACT_NOT_FOUND', 'Artefact');
    a.status = 'extracting';
    setTimeout(() => (a.status = 'done'), 2000);
    return clone(a);
  }
  async getQuestions(artefactId: string) {
    await wait();
    return clone(this.questions[artefactId] ?? []);
  }
  async putQuestions(artefactId: string, rows: T.QuestionIn[]) {
    await wait();
    const prev = this.questions[artefactId] ?? [];
    this.questions[artefactId] = rows.map((r) => {
      const old = prev.find((p) => p.id === r.id);
      return { id: r.id ?? uid('q'), number: r.number, text: r.text, marks: r.marks, bloom_level: old?.bloom_level ?? null, co_ids: old?.co_ids ?? [], topic_ids: old?.topic_ids ?? [] };
    });
    return clone(this.questions[artefactId]);
  }
  async putQuestionCoMap(artefactId: string, rows: T.QuestionCoMapIn[]) {
    await wait();
    for (const r of rows) {
      const q = this.questions[artefactId]?.find((x) => x.id === r.question_id);
      if (q) q.co_ids = r.co_ids;
    }
  }
  async getMarks(artefactId: string) {
    await wait();
    return clone(F.marks[artefactId] ?? F.marks[F.ids.marks2024]);
  }
  async getRubric(artefactId: string) {
    await wait();
    return clone(this.rubric[artefactId] ?? []);
  }
  async putRubric(artefactId: string, rows: T.RubricCriterion[]) {
    await wait();
    this.rubric[artefactId] = rows.map((r) => ({ ...r, id: r.id ?? uid('rc') }));
    return clone(this.rubric[artefactId]);
  }
  async getAnswers(artefactId: string) {
    await wait();
    return clone(this.answers[artefactId] ?? []);
  }
  async putAnswers(artefactId: string, rows: T.Answer[]) {
    await wait();
    this.answers[artefactId] = rows.map((r) => ({ ...r, id: r.id ?? uid('ans') }));
    return clone(this.answers[artefactId]);
  }

  async createRun(courseId: string, body: T.RunCreate) {
    await wait();
    if (!(this.outcomes[courseId] ?? []).length && body.module !== 'syllabus_check' && body.module !== 'calibration')
      throw new ApiError(409, 'COURSE_HAS_NO_OUTCOMES', 'Add course outcomes before running this analysis', uid('req'));
    const id = uid('run');
    const run: T.Run = {
      id,
      course_id: courseId,
      module: body.module,
      status: 'queued',
      progress_pct: 0,
      current_stage: null,
      error: null,
      inputs: body.inputs,
      params: body.params ?? {},
      summary: null,
      started_at: null,
      finished_at: null,
      created_at: new Date().toISOString(),
    };
    const rec: RunRecord = { run, events: [{ seq: 0, stage: 'queued', message: 'Run queued', pct: 0, at: run.created_at }], findings: [], ownerEmail: this.me_.email };
    this.runs.set(id, rec);
    const outcome = this.nextRunOutcome;
    this.nextRunOutcome = null;
    this.simulate(rec, outcome);
    return clone(run);
  }

  private simulate(rec: RunRecord, outcome: T.RunStatus | null) {
    const stages = E.STAGES[rec.run.module];
    const failAt = outcome === 'failed' ? 1 : outcome === 'partial' ? stages.length - 2 : -1;
    let i = 0;
    rec.run.status = 'analyzing';
    rec.run.started_at = new Date().toISOString();
    const tick = () => {
      if (i === failAt) {
        const s = stages[i];
        rec.events.push({ seq: rec.events.length, stage: s.stage, message: outcome === 'failed' ? 'LLM gateway unavailable after retry (503)' : `Stage "${s.stage}" timed out after retry; continuing with completed stages`, pct: s.pct, at: new Date().toISOString() });
        if (outcome === 'failed') {
          rec.run.status = 'failed';
          rec.run.error = 'LLM_UNAVAILABLE: gateway returned 503 twice';
          rec.run.finished_at = new Date().toISOString();
          this.persist();
          return;
        }
        this.finish(rec, 'partial');
        return;
      }
      const s = stages[i];
      rec.run.current_stage = s.stage;
      rec.run.progress_pct = s.pct;
      rec.events.push({ seq: rec.events.length, stage: s.stage, message: s.message, pct: s.pct, at: new Date().toISOString() });
      i++;
      if (i < stages.length) setTimeout(tick, 900 + Math.random() * 700);
      else this.finish(rec, 'completed');
    };
    setTimeout(tick, 400);
  }

  private finish(rec: RunRecord, status: 'completed' | 'partial') {
    const { run } = rec;
    if (run.module === 'exam_audit') {
      const r = E.examAudit(run.id, run.inputs as T.RunInputsExamAudit, run.params);
      run.summary = r.summary;
      rec.findings = status === 'partial' ? r.findings.filter((f) => f.type !== 'duplicate') : r.findings;
    } else if (run.module === 'attainment') {
      const r = E.attainment(run.id, run.inputs as T.RunInputsAttainment);
      run.summary = r.summary;
      rec.findings = status === 'partial' ? r.findings.filter((f) => f.type !== 'action') : r.findings;
      rec.attainment = r.out;
    } else if (run.module === 'syllabus_check') {
      const r = E.syllabusCheck(run.id, run.inputs as T.RunInputsSyllabusCheck);
      run.summary = r.summary;
      rec.findings = status === 'partial' ? r.findings.filter((f) => f.type === 'overlap') : r.findings;
    } else {
      const r = E.calibration(run.id, run.inputs as T.RunInputsCalibration);
      run.summary = r.summary;
      rec.findings = status === 'partial' ? r.findings.filter((f) => f.type === 'divergence') : r.findings;
      rec.prescores = status === 'partial' ? [] : r.prescores;
    }
    run.status = status;
    run.progress_pct = 100;
    run.finished_at = new Date().toISOString();
    if (status === 'partial') run.error = 'One stage failed after retry; results from completed stages are shown.';
    this.persist();
  }

  async getRun(runId: string) {
    await wait(120);
    return clone((this.runs.get(runId) ?? this.notFound('RUN_NOT_FOUND', 'Run')).run);
  }

  subscribeRunEvents(runId: string, afterSeq: number, h: RunEventHandlers) {
    const rec = this.runs.get(runId);
    if (!rec) {
      h.onError(new ApiError(404, 'RUN_NOT_FOUND', 'Run not found'));
      return () => {};
    }
    let sent = afterSeq;
    let stopped = false;
    const poll = () => {
      if (stopped) return;
      for (const e of rec.events) if (e.seq > sent) (sent = e.seq, h.onProgress(clone(e)));
      if (['completed', 'partial', 'failed'].includes(rec.run.status)) {
        h.onDone(rec.run.status);
        return;
      }
      setTimeout(poll, 400);
    };
    setTimeout(poll, 100);
    return () => (stopped = true);
  }

  async listFindings(runId: string, filter?: { type?: T.FindingType; status?: T.FindingStatus; severity?: T.FindingSeverity }) {
    await wait();
    const rec = this.runs.get(runId) ?? this.notFound('RUN_NOT_FOUND', 'Run');
    return clone(rec.findings.filter((f) => (!filter?.type || f.type === filter.type) && (!filter?.status || f.status === filter.status) && (!filter?.severity || f.severity === filter.severity)));
  }
  async patchFinding(findingId: string, status: T.FindingStatus) {
    await wait(150);
    for (const rec of this.runs.values()) {
      const f = rec.findings.find((x) => x.id === findingId);
      if (f) {
        if (this.me_.role === 'admin') throw new ApiError(403, 'FORBIDDEN', 'Admins are read-only', uid('req'));
        f.status = status;
        f.decided_at = status === 'open' ? null : new Date().toISOString();
        this.persist();
        return clone(f);
      }
    }
    return this.notFound('FINDING_NOT_FOUND', 'Finding');
  }
  async exportRun(runId: string, format: 'md' | 'pdf', include: 'accepted' | 'all') {
    await wait(400);
    if (format === 'pdf') throw new ApiError(503, 'EXPORT_PDF_UNAVAILABLE', 'PDF export unavailable in demo mode', uid('req'));
    const rec = this.runs.get(runId) ?? this.notFound('RUN_NOT_FOUND', 'Run');
    const course = this.courses.find((c) => c.id === rec.run.course_id);
    const fs = rec.findings.filter((f) => include === 'all' || f.status === 'accepted');
    const lines = [
      `# ${course?.code ?? ''} — ${rec.run.module.replace('_', ' ')} report`,
      '',
      `Run ${rec.run.id} · ${rec.run.status} · finished ${rec.run.finished_at ?? '—'}`,
      '',
      '## Summary',
      '',
      '```json',
      JSON.stringify(rec.run.summary, null, 2),
      '```',
      '',
      `## Findings (${include})`,
      '',
      ...fs.flatMap((f) => [
        `### [${f.severity.toUpperCase()}] ${f.title}`,
        '',
        `- Type: ${f.type}  ·  Target: ${f.target_label ?? '—'}  ·  Status: ${f.status}`,
        `- Rationale: ${f.rationale}`,
        ...(f.evidence_snippet ? ['', '> ' + f.evidence_snippet.split('\n').join('\n> ')] : []),
        '',
      ]),
    ];
    return new Blob([lines.join('\n')], { type: 'text/markdown' });
  }
  async compareRuns(a: string, b: string) {
    await wait();
    const A = this.runs.get(a) ?? this.notFound('RUN_NOT_FOUND', 'Run A');
    const B = this.runs.get(b) ?? this.notFound('RUN_NOT_FOUND', 'Run B');
    if (A.run.module !== 'exam_audit' || B.run.module !== 'exam_audit' || A.run.course_id !== B.run.course_id || A.run.status === 'failed' || B.run.status === 'failed')
      throw new ApiError(409, 'RUNS_NOT_COMPARABLE', 'Both runs must be completed exam audits of the same course', uid('req'));
    const key = (f: T.Finding) => `${f.type}|${f.target_kind}|${f.target_label}`;
    const bMap = new Map(B.findings.map((f) => [key(f), f]));
    const aMap = new Map(A.findings.map((f) => [key(f), f]));
    const out: T.CompareOut = { resolved: [], new: [], persisting: [] };
    for (const f of A.findings) {
      const m = bMap.get(key(f));
      if (m) out.persisting.push({ a: clone(f), b: clone(m) });
      else out.resolved.push(clone(f));
    }
    for (const f of B.findings) if (!aMap.has(key(f))) out.new.push(clone(f));
    return out;
  }
  async suggestQuestions(runId: string, coIds?: string[]) {
    await wait(1800);
    const rec = this.runs.get(runId) ?? this.notFound('RUN_NOT_FOUND', 'Run');
    const s = E.suggestions(runId, coIds);
    rec.findings.push(...s);
    this.persist();
    return clone(s);
  }
  async getAttainment(runId: string) {
    await wait();
    const rec = this.runs.get(runId) ?? this.notFound('RUN_NOT_FOUND', 'Run');
    return clone(rec.attainment ?? { threshold: 60, cos: [], pos: [] });
  }
  async getPrescores(runId: string) {
    await wait();
    const rec = this.runs.get(runId) ?? this.notFound('RUN_NOT_FOUND', 'Run');
    return clone(rec.prescores ?? []);
  }

  async dashboardSummary() {
    await wait();
    const all = [...this.runs.values()];
    const courses = this.courses.map((c) => {
      const ea = all.filter((r) => r.run.course_id === c.id && r.run.module === 'exam_audit' && r.run.summary).sort((x, y) => y.run.created_at.localeCompare(x.run.created_at))[0];
      const at = all.filter((r) => r.run.course_id === c.id && r.run.module === 'attainment' && r.run.summary).sort((x, y) => y.run.created_at.localeCompare(x.run.created_at))[0];
      return {
        course_id: c.id,
        code: c.code,
        title: c.title,
        last_exam_audit: ea ? { run_id: ea.run.id, open_findings: ea.findings.filter((f) => f.status === 'open').length, coverage_pct: (ea.run.summary as T.ExamAuditSummary).coverage_pct } : null,
        last_attainment: at ? { run_id: at.run.id, cos_met: (at.run.summary as T.AttainmentSummary).cos_met, cos_total: (at.run.summary as T.AttainmentSummary).cos_total } : null,
      };
    });
    const fs = all.flatMap((r) => r.findings);
    return { courses, totals: { runs: all.length, accepted_findings: fs.filter((f) => f.status === 'accepted').length, dismissed_findings: fs.filter((f) => f.status === 'dismissed').length } };
  }

  async adminUsers() {
    await wait();
    return { items: clone(this.users), page: 1, page_size: 25, total: this.users.length };
  }
  async adminPatchUser(id: string, body: { is_active?: boolean; role?: T.AppRole }) {
    await wait();
    if (id === this.me_.id) throw new ApiError(409, 'CANNOT_MODIFY_SELF', 'You cannot modify your own account', uid('req'));
    const u = this.users.find((x) => x.id === id) ?? this.notFound('USER_NOT_FOUND', 'User');
    Object.assign(u, body);
    return clone(u);
  }
  async adminRuns(params: { page?: number; module?: T.RunModule; status?: T.RunStatus }) {
    await wait();
    const items = [...this.runs.values()]
      .filter((r) => (!params.module || r.run.module === params.module) && (!params.status || r.run.status === params.status))
      .map((r) => ({ ...clone(r.run), owner_email: r.ownerEmail }))
      .sort((a, b) => b.created_at.localeCompare(a.created_at));
    return { items, page: 1, page_size: 25, total: items.length };
  }
  async adminUsage(params: { group?: 'user' | 'day' }) {
    await wait();
    return clone(params.group === 'day' ? F.usageByDay : F.usage);
  }
  async adminDemoReset() {
    await wait(900);
    this.runs.clear();
    this.persist();
    this.courses = clone(F.courses);
    this.artefacts = clone(F.artefacts);
    this.outcomes = clone(F.courseOutcomes);
    this.topics = clone(F.topics);
    return { course_id: F.ids.course };
  }
  async adminDeptAttainment() {
    await wait();
    return [...this.runs.values()]
      .filter((r) => r.run.module === 'attainment' && r.run.summary)
      .map((r) => {
        const s = r.run.summary as T.AttainmentSummary;
        const weakest = [...(r.attainment?.cos ?? [])].sort((a, b) => a.attained_pct - b.attained_pct)[0];
        return { owner_email: r.ownerEmail, course_code: this.courses.find((c) => c.id === r.run.course_id)?.code ?? '', run_id: r.run.id, finished_at: r.run.finished_at ?? '', cos_met: s.cos_met, cos_total: s.cos_total, weakest_co: weakest?.co_code ?? null };
      });
  }
  async adminDeptExamAudits() {
    await wait();
    return [...this.runs.values()]
      .filter((r) => r.run.module === 'exam_audit' && r.run.summary)
      .map((r) => {
        const s = r.run.summary as T.ExamAuditSummary;
        return { owner_email: r.ownerEmail, course_code: this.courses.find((c) => c.id === r.run.course_id)?.code ?? '', run_id: r.run.id, finished_at: r.run.finished_at ?? '', coverage_pct: s.coverage_pct, duplicates: s.duplicates.length, open_findings: r.findings.filter((f) => f.status === 'open').length };
      });
  }

  /** Minimal in-browser assistant: lists courses / points at pages; real planning lives in the backend. */
  async assistantChat(body: T.AssistantChatRequest): Promise<T.AssistantChatResponse> {
    await wait(400);
    const low = body.message.toLowerCase();
    const mine = this.courses.filter((c) => c.owner_id === this.userId && !c.deleted_at);
    if (body.file) {
      return { reply: `In demo mode I can't upload **${body.file.name}**. Switch to the live API (VITE_API_MODE=live) to let the assistant upload and analyse files.`, actions: [], navigate: null, model: 'mock-fe' };
    }
    if (low.includes('course')) {
      return {
        reply: mine.length ? `You have ${mine.length} course(s):\n${mine.map((c) => `- **${c.code}** — ${c.title}`).join('\n')}` : 'You have no courses yet.',
        actions: [{ tool: 'list_courses', status: 'ok', summary: `${mine.length} course(s)` }],
        navigate: '/courses',
        model: 'mock-fe',
      };
    }
    return {
      reply: 'I can list your courses, open pages, and — with the live backend — upload files, run exam audits and decide findings. Try “list my courses”.',
      actions: [],
      navigate: null,
      model: 'mock-fe',
    };
  }
}
