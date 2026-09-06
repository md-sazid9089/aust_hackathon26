// Hand-written mirror of architecture.md §19 / §21 / §28.6.
// Replace with `npm run gen:api` output once backend/openapi.json exists.

export type UUID = string;
export type ISODate = string;

export type AppRole = 'faculty' | 'admin';
export type ArtefactKind = 'syllabus' | 'question_paper' | 'marks_sheet' | 'rubric' | 'answer_set';
export type ExtractionStatus = 'pending' | 'extracting' | 'done' | 'failed';
export type TextLang = 'en' | 'bn' | 'mixed' | 'unknown';
export type BloomLevel = 'remember' | 'understand' | 'apply' | 'analyze' | 'evaluate' | 'create';
export type RunModule = 'exam_audit' | 'attainment' | 'syllabus_check' | 'calibration';
export type RunStatus = 'queued' | 'analyzing' | 'completed' | 'partial' | 'failed';
export type FindingSeverity = 'info' | 'low' | 'medium' | 'high';
export type FindingStatus = 'open' | 'accepted' | 'dismissed';
export type TargetKind =
  | 'question'
  | 'course_outcome'
  | 'program_outcome'
  | 'topic'
  | 'answer'
  | 'criterion'
  | 'course'
  | 'none';

export type FindingType =
  | 'coverage_gap'
  | 'overweight'
  | 'bloom_imbalance'
  | 'duplicate'
  | 'fairness'
  | 'marks_total_mismatch'
  | 'untagged_question'
  | 'suggestion'
  | 'co_underperformance'
  | 'po_underperformance'
  | 'action'
  | 'overlap'
  | 'prerequisite_gap'
  | 'missing_topic'
  | 'repositioning'
  | 'divergence'
  | 'prescore_note'
  | 'rubric_clarification';

export interface ApiErrorBody {
  error: { code: string; message: string; details?: unknown; request_id?: string };
}

export interface Page<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}

export interface Profile {
  id: UUID;
  email: string;
  full_name: string | null;
  role: AppRole;
  is_active: boolean;
  created_at: ISODate;
}

export interface Course {
  id: UUID;
  code: string;
  title: string;
  term: string | null;
  description: string | null;
  is_demo: boolean;
  created_at: ISODate;
  counts?: { artefacts: number; runs: number; outcomes: number };
}
export interface CourseCreate {
  code: string;
  title: string;
  term?: string;
  description?: string;
}

export interface ProgramOutcome {
  id: UUID;
  code: string;
  text: string;
  sort_order: number;
}
export interface CourseOutcome {
  id: UUID;
  code: string;
  text: string;
  bloom_level: BloomLevel | null;
  weight: number;
}
export interface CourseOutcomeIn {
  id?: UUID;
  code: string;
  text: string;
  bloom_level?: BloomLevel | null;
  weight?: number;
}
export interface CoPoCell {
  co_id: UUID;
  po_id: UUID;
  strength: 0 | 1 | 2 | 3;
}
export interface Topic {
  id: UUID;
  code: string;
  title: string;
  source_artefact_id: UUID | null;
}
export interface TopicIn {
  id?: UUID;
  code: string;
  title: string;
}

export interface Artefact {
  id: UUID;
  course_id: UUID;
  kind: ArtefactKind;
  label: string;
  year: number | null;
  term: string | null;
  declared_total_marks?: number | null;
  mime: string | null;
  lang: TextLang;
  status: ExtractionStatus;
  error: string | null;
  created_at: ISODate;
  counts?: Record<string, number>;
}
export interface ArtefactUpload {
  kind: ArtefactKind;
  label: string;
  year?: number;
  term?: string;
  declared_total_marks?: number;
  file?: File;
  text?: string;
  grader_labels?: string[];
}

export interface Question {
  id: UUID;
  number: string;
  text: string;
  marks: number;
  bloom_level: BloomLevel | null;
  co_ids: UUID[];
  topic_ids: UUID[];
}
export interface QuestionIn {
  id?: UUID;
  number: string;
  text: string;
  marks: number;
}
export interface QuestionCoMapIn {
  question_id: UUID;
  co_ids: UUID[];
}

export interface MarksSheet {
  students: number;
  questions: { number: string; max: number }[];
  rows: { student_anon_id: string; scores: Record<string, number> }[];
}

export interface RubricLevel {
  label: string;
  score: number;
  descriptor: string;
}
export interface RubricCriterion {
  id?: UUID;
  code: string;
  text: string;
  max_score: number;
  levels: RubricLevel[];
}

export interface GraderScore {
  grader_label: string;
  criterion_code: string;
  score: number;
}
export interface Answer {
  id?: UUID;
  student_anon_id: string;
  question_ref: string | null;
  text: string;
  grader_scores: GraderScore[];
}

export interface RunInputsExamAudit {
  draft_artefact_id: UUID;
  past_artefact_ids: UUID[];
}
export interface RunInputsAttainment {
  marks_artefact_id: UUID;
  paper_artefact_id: UUID;
  threshold: number;
}
export interface RunInputsSyllabusCheck {
  syllabus_artefact_id: UUID;
  compare_course_ids: UUID[];
}
export interface RunInputsCalibration {
  rubric_artefact_id: UUID;
  answer_set_artefact_id: UUID;
}
export type RunInputs =
  | RunInputsExamAudit
  | RunInputsAttainment
  | RunInputsSyllabusCheck
  | RunInputsCalibration;

export interface RunCreate {
  module: RunModule;
  inputs: RunInputs;
  params?: Record<string, number | string | boolean>;
}

export interface CoverageCell {
  target_kind: 'course_outcome' | 'topic';
  target_code: string;
  marks: number;
  share: number;
  expected_share: number;
  status: 'covered' | 'uncovered' | 'overweight';
  questions?: string[];
}
/** Mirrors backend `modules/exam_audit/graph.py::_compute_and_build`. */
export interface ExamAuditSummary {
  draft_label?: string;
  questions?: number;
  past_questions?: number;
  coverage_pct: number;
  coverage: CoverageCell[];
  bloom: {
    counts: Partial<Record<BloomLevel | 'unclassified', number>>;
    marks: Partial<Record<BloomLevel | 'unclassified', number>>;
    lower_order_share: number;
    higher_order_share: number;
    unclassified: number;
  };
  marks_total?: { computed: number; declared: number | null; mismatch: boolean };
  duplicates: {
    draft_number?: string;
    other_label?: string;
    other_number?: string;
    similarity: number;
    confirmed?: boolean;
    [k: string]: unknown;
  }[];
  fairness: { deviation_score: number; heavy_questions: { number: string; marks: number; share: number }[]; notes: string[] };
  untagged?: string[];
  findings?: number;
  mapping?: {
    number: string;
    co_codes: string[];
    topic_codes: string[];
    bloom_level: BloomLevel | null;
    source: string | null;
    confidence: number | null;
    rationale: string | null;
  }[];
}
export interface AttainmentSummary {
  threshold: number;
  cos_met: number;
  cos_total: number;
  pos_met: number;
  pos_total: number;
}
export interface OverlapCell {
  course_code: string;
  topic_a: string;
  topic_b: string;
  similarity: number;
  relation: 'overlap' | 'distinct' | 'prerequisite';
}
export interface SyllabusCheckSummary {
  matrix: OverlapCell[];
  overlap_pct: number;
}
export interface CalibrationSummary {
  graders: string[];
  divergent_answers: number;
  mean_abs_dev: number;
  criteria_flagged: string[];
}
export type RunSummary =
  | ExamAuditSummary
  | AttainmentSummary
  | SyllabusCheckSummary
  | CalibrationSummary;

export interface Run {
  id: UUID;
  course_id: UUID;
  module: RunModule;
  status: RunStatus;
  progress_pct: number;
  current_stage: string | null;
  error: string | null;
  inputs: RunInputs;
  params: Record<string, unknown>;
  summary: RunSummary | null;
  started_at: ISODate | null;
  finished_at: ISODate | null;
  created_at: ISODate;
}

export interface RunProgressEvent {
  seq: number;
  stage: string;
  message: string | null;
  pct: number | null;
  level?: 'info' | 'warning' | 'error';
  at: ISODate;
}

export interface Finding {
  id: UUID;
  run_id: UUID;
  type: FindingType;
  severity: FindingSeverity;
  title: string;
  rationale: string;
  evidence_snippet: string | null;
  target_kind: TargetKind;
  target_id: UUID | null;
  target_label: string | null;
  payload: Record<string, unknown>;
  status: FindingStatus;
  decided_at: ISODate | null;
}

export interface CompareOut {
  resolved: Finding[];
  new: Finding[];
  persisting: { a: Finding; b: Finding }[];
}

export interface AttainmentOut {
  threshold: number;
  cos: { co_id: UUID; co_code: string; attained_pct: number; students: number; target_pct: number; met: boolean }[];
  pos: { po_id: UUID; po_code: string; attained_pct: number; met: boolean }[];
}

export interface Prescore {
  answer_id: UUID;
  student_anon_id: string;
  criterion_code: string;
  ai_score: number;
  rationale: string;
  grader_scores: Record<string, number>;
}

export interface DashboardOut {
  courses: {
    course_id: UUID;
    code: string;
    title: string;
    last_exam_audit: { run_id: UUID; open_findings: number; coverage_pct: number } | null;
    last_attainment: { run_id: UUID; cos_met: number; cos_total: number } | null;
  }[];
  totals: { runs: number; accepted_findings: number; dismissed_findings: number };
}

export interface AdminUser extends Profile {
  courses: number;
  runs: number;
}
export interface AdminRun extends Run {
  owner_email: string;
}
export interface UsageRow {
  key: string;
  calls: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  failures: number;
}
export interface DeptAttainmentRow {
  owner_email: string;
  course_code: string;
  run_id: UUID;
  finished_at: ISODate;
  cos_met: number;
  cos_total: number;
  weakest_co: string | null;
}
export interface DeptAuditRow {
  owner_email: string;
  course_code: string;
  run_id: UUID;
  finished_at: ISODate;
  coverage_pct: number;
  duplicates: number;
  open_findings: number;
}
