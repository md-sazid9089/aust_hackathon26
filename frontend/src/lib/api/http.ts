import type * as T from '@/lib/types/api';
import { ApiError, type Api, type RunEventHandlers } from './types';

type TokenGetter = () => Promise<string | null>;

export class HttpApi implements Api {
  constructor(
    private baseUrl: string,
    private getToken: TokenGetter,
    private onUnauthorized: () => void,
  ) {}

  private async request<R>(
    path: string,
    init: RequestInit & { query?: Record<string, string | number | undefined>; raw?: boolean } = {},
  ): Promise<R> {
    const url = new URL(this.baseUrl + path, window.location.origin);
    for (const [k, v] of Object.entries(init.query ?? {})) {
      if (v !== undefined && v !== '') url.searchParams.set(k, String(v));
    }
    const headers = new Headers(init.headers);
    const token = await this.getToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
    if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json');

    const res = await fetch(url, { ...init, headers });
    if (res.status === 401) this.onUnauthorized();
    if (!res.ok) {
      let body: T.ApiErrorBody | null = null;
      try {
        body = (await res.json()) as T.ApiErrorBody;
      } catch {
        /* non-JSON error */
      }
      throw new ApiError(
        res.status,
        body?.error.code ?? 'HTTP_ERROR',
        body?.error.message ?? res.statusText,
        body?.error.request_id ?? res.headers.get('x-request-id') ?? undefined,
        body?.error.details,
      );
    }
    if (init.raw) return (await res.blob()) as R;
    if (res.status === 204) return undefined as R;
    return (await res.json()) as R;
  }

  private json(body: unknown): string {
    return JSON.stringify(body);
  }

  me() {
    return this.request<T.Profile>('/me');
  }

  listCourses(q?: string) {
    return this.request<T.Page<T.Course>>('/courses', { query: { q, page_size: 100 } });
  }
  getCourse(id: string) {
    return this.request<T.Course>(`/courses/${id}`);
  }
  createCourse(body: T.CourseCreate) {
    return this.request<T.Course>('/courses', { method: 'POST', body: this.json(body) });
  }
  updateCourse(id: string, body: Partial<T.CourseCreate>) {
    return this.request<T.Course>(`/courses/${id}`, { method: 'PATCH', body: this.json(body) });
  }
  deleteCourse(id: string) {
    return this.request<void>(`/courses/${id}`, { method: 'DELETE' });
  }
  listRuns(courseId: string, filter?: { module?: T.RunModule; status?: T.RunStatus }) {
    return this.request<T.Page<T.Run>>(`/courses/${courseId}/runs`, { query: { ...filter, page_size: 100, sort: 'created_at:desc' } });
  }
  seedDemo() {
    return this.request<{ course_id: string; created: boolean }>('/demo/seed', { method: 'POST' });
  }

  listProgramOutcomes() {
    return this.request<T.ProgramOutcome[]>('/program-outcomes');
  }
  listOutcomes(courseId: string) {
    return this.request<T.CourseOutcome[]>(`/courses/${courseId}/outcomes`);
  }
  putOutcomes(courseId: string, rows: T.CourseOutcomeIn[]) {
    return this.request<T.CourseOutcome[]>(`/courses/${courseId}/outcomes`, { method: 'PUT', body: this.json(rows) });
  }
  getCoPoMap(courseId: string) {
    return this.request<T.CoPoCell[]>(`/courses/${courseId}/co-po-map`);
  }
  putCoPoMap(courseId: string, cells: T.CoPoCell[]) {
    return this.request<T.CoPoCell[]>(`/courses/${courseId}/co-po-map`, { method: 'PUT', body: this.json(cells) });
  }
  listTopics(courseId: string) {
    return this.request<T.Topic[]>(`/courses/${courseId}/topics`);
  }
  putTopics(courseId: string, rows: T.TopicIn[]) {
    return this.request<T.Topic[]>(`/courses/${courseId}/topics`, { method: 'PUT', body: this.json(rows) });
  }

  listArtefacts(courseId: string, filter?: { kind?: T.ArtefactKind; status?: T.ExtractionStatus }) {
    return this.request<T.Artefact[]>(`/courses/${courseId}/artefacts`, { query: filter });
  }
  getArtefact(id: string) {
    return this.request<T.Artefact>(`/artefacts/${id}`);
  }
  uploadArtefact(courseId: string, body: T.ArtefactUpload) {
    const fd = new FormData();
    fd.set('kind', body.kind);
    fd.set('label', body.label);
    if (body.year) fd.set('year', String(body.year));
    if (body.term) fd.set('term', body.term);
    if (body.file) fd.set('file', body.file);
    if (body.text) fd.set('text', body.text);
    if (body.grader_labels) fd.set('grader_labels', JSON.stringify(body.grader_labels));
    return this.request<T.Artefact>(`/courses/${courseId}/artefacts`, { method: 'POST', body: fd });
  }
  deleteArtefact(id: string) {
    return this.request<void>(`/artefacts/${id}`, { method: 'DELETE' });
  }
  reextract(id: string) {
    return this.request<T.Artefact>(`/artefacts/${id}/reextract`, { method: 'POST' });
  }
  getQuestions(artefactId: string) {
    return this.request<T.Question[]>(`/artefacts/${artefactId}/questions`);
  }
  putQuestions(artefactId: string, rows: T.QuestionIn[]) {
    return this.request<T.Question[]>(`/artefacts/${artefactId}/questions`, { method: 'PUT', body: this.json(rows) });
  }
  putQuestionCoMap(artefactId: string, rows: T.QuestionCoMapIn[]) {
    return this.request<void>(`/artefacts/${artefactId}/questions/co-map`, { method: 'PUT', body: this.json(rows) });
  }
  getMarks(artefactId: string) {
    return this.request<T.MarksSheet>(`/artefacts/${artefactId}/marks`);
  }
  getRubric(artefactId: string) {
    return this.request<T.RubricCriterion[]>(`/artefacts/${artefactId}/rubric`);
  }
  putRubric(artefactId: string, rows: T.RubricCriterion[]) {
    return this.request<T.RubricCriterion[]>(`/artefacts/${artefactId}/rubric`, { method: 'PUT', body: this.json(rows) });
  }
  getAnswers(artefactId: string) {
    return this.request<T.Answer[]>(`/artefacts/${artefactId}/answers`);
  }
  putAnswers(artefactId: string, rows: T.Answer[]) {
    return this.request<T.Answer[]>(`/artefacts/${artefactId}/answers`, { method: 'PUT', body: this.json(rows) });
  }

  createRun(courseId: string, body: T.RunCreate) {
    return this.request<T.Run>(`/courses/${courseId}/runs`, {
      method: 'POST',
      body: this.json(body),
      headers: { 'Idempotency-Key': crypto.randomUUID() },
    });
  }
  getRun(runId: string) {
    return this.request<T.Run>(`/runs/${runId}`);
  }
  subscribeRunEvents(runId: string, afterSeq: number, h: RunEventHandlers) {
    let es: EventSource | null = null;
    let closed = false;
    void this.getToken().then((token) => {
      if (closed) return;
      const url = new URL(`${this.baseUrl}/runs/${runId}/events`, window.location.origin);
      if (token) url.searchParams.set('access_token', token);
      if (afterSeq) url.searchParams.set('after_seq', String(afterSeq));
      es = new EventSource(url);
      es.addEventListener('progress', (ev) => h.onProgress(JSON.parse((ev as MessageEvent).data)));
      es.addEventListener('done', (ev) => {
        h.onDone(JSON.parse((ev as MessageEvent).data).status);
        es?.close();
      });
      es.onerror = (e) => h.onError(e);
    });
    return () => {
      closed = true;
      es?.close();
    };
  }
  listFindings(runId: string, filter?: { type?: T.FindingType; status?: T.FindingStatus; severity?: T.FindingSeverity }) {
    return this.request<T.Finding[]>(`/runs/${runId}/findings`, { query: filter });
  }
  patchFinding(findingId: string, status: T.FindingStatus) {
    return this.request<T.Finding>(`/findings/${findingId}`, { method: 'PATCH', body: this.json({ status }) });
  }
  exportRun(runId: string, format: 'md' | 'pdf', include: 'accepted' | 'all') {
    return this.request<Blob>(`/runs/${runId}/export`, { query: { format, include }, raw: true });
  }
  compareRuns(a: string, b: string) {
    return this.request<T.CompareOut>('/runs/compare', { query: { a, b } });
  }
  suggestQuestions(runId: string, coIds?: string[]) {
    return this.request<T.Finding[]>(`/runs/${runId}/suggest-questions`, {
      method: 'POST',
      body: this.json(coIds ? { co_ids: coIds } : {}),
    });
  }
  getAttainment(runId: string) {
    return this.request<T.AttainmentOut>(`/runs/${runId}/attainment`);
  }
  getPrescores(runId: string) {
    return this.request<T.Prescore[]>(`/runs/${runId}/prescores`);
  }

  dashboardSummary() {
    return this.request<T.DashboardOut>('/dashboard/summary');
  }

  adminUsers(page = 1) {
    return this.request<T.Page<T.AdminUser>>('/admin/users', { query: { page, page_size: 25 } });
  }
  adminPatchUser(id: string, body: { is_active?: boolean; role?: T.AppRole }) {
    return this.request<T.AdminUser>(`/admin/users/${id}`, { method: 'PATCH', body: this.json(body) });
  }
  adminRuns(params: { page?: number; module?: T.RunModule; status?: T.RunStatus }) {
    return this.request<T.Page<T.AdminRun>>('/admin/runs', { query: { ...params, page_size: 25 } });
  }
  adminUsage(params: { from?: string; to?: string; group?: 'user' | 'day' }) {
    return this.request<T.UsageRow[]>('/admin/usage', { query: params });
  }
  adminDemoReset() {
    return this.request<{ course_id: string }>('/admin/demo/reset', { method: 'POST' });
  }
  adminDeptAttainment() {
    return this.request<T.DeptAttainmentRow[]>('/admin/department/attainment');
  }
  adminDeptExamAudits() {
    return this.request<T.DeptAuditRow[]>('/admin/department/exam-audits');
  }
}
