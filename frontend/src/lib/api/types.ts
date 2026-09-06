import type * as T from '@/lib/types/api';

export interface RunEventHandlers {
  onProgress: (e: T.RunProgressEvent) => void;
  onDone: (status: T.RunStatus) => void;
  onError: (err: unknown) => void;
}

/** Single seam between UI and transport (architecture §12). Implemented by HttpApi. */
export interface Api {
  // auth
  me(): Promise<T.Profile>;

  // courses
  listCourses(q?: string): Promise<T.Page<T.Course>>;
  getCourse(id: string): Promise<T.Course>;
  createCourse(body: T.CourseCreate): Promise<T.Course>;
  updateCourse(id: string, body: Partial<T.CourseCreate>): Promise<T.Course>;
  deleteCourse(id: string): Promise<void>;
  listRuns(courseId: string, filter?: { module?: T.RunModule; status?: T.RunStatus }): Promise<T.Page<T.Run>>;
  seedDemo(): Promise<{ course_id: string; created: boolean }>;

  // outcomes
  listProgramOutcomes(): Promise<T.ProgramOutcome[]>;
  listOutcomes(courseId: string): Promise<T.CourseOutcome[]>;
  putOutcomes(courseId: string, rows: T.CourseOutcomeIn[]): Promise<T.CourseOutcome[]>;
  getCoPoMap(courseId: string): Promise<T.CoPoCell[]>;
  putCoPoMap(courseId: string, cells: T.CoPoCell[]): Promise<T.CoPoCell[]>;
  listTopics(courseId: string): Promise<T.Topic[]>;
  putTopics(courseId: string, rows: T.TopicIn[]): Promise<T.Topic[]>;

  // artefacts
  listArtefacts(courseId: string, filter?: { kind?: T.ArtefactKind; status?: T.ExtractionStatus }): Promise<T.Artefact[]>;
  getArtefact(id: string): Promise<T.Artefact>;
  uploadArtefact(courseId: string, body: T.ArtefactUpload): Promise<T.Artefact>;
  deleteArtefact(id: string): Promise<void>;
  reextract(id: string): Promise<T.Artefact>;
  getQuestions(artefactId: string): Promise<T.Question[]>;
  putQuestions(artefactId: string, rows: T.QuestionIn[]): Promise<T.Question[]>;
  putQuestionCoMap(artefactId: string, rows: T.QuestionCoMapIn[]): Promise<void>;
  getMarks(artefactId: string): Promise<T.MarksSheet>;
  getRubric(artefactId: string): Promise<T.RubricCriterion[]>;
  putRubric(artefactId: string, rows: T.RubricCriterion[]): Promise<T.RubricCriterion[]>;
  getAnswers(artefactId: string): Promise<T.Answer[]>;
  putAnswers(artefactId: string, rows: T.Answer[]): Promise<T.Answer[]>;

  // runs
  createRun(courseId: string, body: T.RunCreate): Promise<T.Run>;
  getRun(runId: string): Promise<T.Run>;
  /** Opens an SSE-like stream; returns a close function. */
  subscribeRunEvents(runId: string, afterSeq: number, h: RunEventHandlers): () => void;
  listFindings(runId: string, filter?: { type?: T.FindingType; status?: T.FindingStatus; severity?: T.FindingSeverity }): Promise<T.Finding[]>;
  patchFinding(findingId: string, status: T.FindingStatus): Promise<T.Finding>;
  exportRun(runId: string, format: 'md' | 'pdf', include: 'accepted' | 'all'): Promise<Blob>;
  compareRuns(a: string, b: string): Promise<T.CompareOut>;
  suggestQuestions(runId: string, coIds?: string[]): Promise<T.Finding[]>;
  getAttainment(runId: string): Promise<T.AttainmentOut>;
  getPrescores(runId: string): Promise<T.Prescore[]>;

  // dashboard
  dashboardSummary(): Promise<T.DashboardOut>;

  // admin
  adminUsers(page?: number): Promise<T.Page<T.AdminUser>>;
  adminPatchUser(id: string, body: { is_active?: boolean; role?: T.AppRole }): Promise<T.AdminUser>;
  adminRuns(params: { page?: number; module?: T.RunModule; status?: T.RunStatus }): Promise<T.Page<T.AdminRun>>;
  adminUsage(params: { from?: string; to?: string; group?: 'user' | 'day' }): Promise<T.UsageRow[]>;
  adminDemoReset(): Promise<{ course_id: string }>;
  adminDeptAttainment(): Promise<T.DeptAttainmentRow[]>;
  adminDeptExamAudits(): Promise<T.DeptAuditRow[]>;

  // assistant
  assistantChat(body: T.AssistantChatRequest): Promise<T.AssistantChatResponse>;
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public requestId?: string,
    public details?: unknown,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}
