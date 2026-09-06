import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { FindingSeverity, FindingType, RunModule, RunStatus, ArtefactKind, BloomLevel } from '@/lib/types/api';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const pct = (n: number, digits = 0) => `${(n * (n <= 1 ? 100 : 1)).toFixed(digits)}%`;
export const fixed = (n: number, digits = 1) => n.toFixed(digits);

export function formatDate(iso: string | null | undefined, opts: Intl.DateTimeFormatOptions = { dateStyle: 'medium', timeStyle: 'short' }) {
  if (!iso) return '—';
  return new Intl.DateTimeFormat('en-GB', opts).format(new Date(iso));
}

export function relTime(iso: string | null | undefined) {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat('en', { numeric: 'auto' });
  if (diff < 60) return 'just now';
  if (diff < 3600) return rtf.format(-Math.round(diff / 60), 'minute');
  if (diff < 86400) return rtf.format(-Math.round(diff / 3600), 'hour');
  return rtf.format(-Math.round(diff / 86400), 'day');
}

export const MODULE_LABEL: Record<RunModule, string> = {
  exam_audit: 'Exam audit',
  attainment: 'CO/PO attainment',
  syllabus_check: 'Syllabus check',
  calibration: 'Grading calibration',
};
export const MODULE_PATH: Record<RunModule, string> = {
  exam_audit: 'exam-audit',
  attainment: 'attainment',
  syllabus_check: 'syllabus-check',
  calibration: 'calibration',
};
export const MODULE_DESC: Record<RunModule, string> = {
  exam_audit: 'Check a draft paper for CO coverage, over-weighting, Bloom balance and repeated questions.',
  attainment: 'Compute CO and PO attainment from a marks sheet and explain weak outcomes.',
  syllabus_check: 'Find overlaps, prerequisites and gaps against other courses in the department.',
  calibration: 'Surface grader disagreement, pre-score answers and propose rubric clarifications.',
};

export const STATUS_LABEL: Record<RunStatus, string> = {
  queued: 'Queued',
  analyzing: 'Analysing',
  completed: 'Completed',
  partial: 'Partial',
  failed: 'Failed',
};

export const SEVERITY_LABEL: Record<FindingSeverity, string> = { info: 'Info', low: 'Low', medium: 'Medium', high: 'High' };
export const SEVERITY_ORDER: FindingSeverity[] = ['high', 'medium', 'low', 'info'];

export const FINDING_TYPE_LABEL: Record<FindingType, string> = {
  coverage_gap: 'Coverage gap',
  overweight: 'Over-weighted',
  bloom_imbalance: 'Bloom imbalance',
  duplicate: 'Repeated question',
  fairness: 'Fairness',
  marks_total_mismatch: 'Marks total mismatch',
  suggestion: 'Suggested question',
  co_underperformance: 'CO under target',
  po_underperformance: 'PO under target',
  action: 'Suggested action',
  overlap: 'Overlap',
  prerequisite_gap: 'Prerequisite',
  missing_topic: 'Missing topic',
  repositioning: 'Repositioning',
  divergence: 'Grader divergence',
  prescore_note: 'Pre-score note',
  rubric_clarification: 'Rubric clarification',
};

export const KIND_LABEL: Record<ArtefactKind, string> = {
  syllabus: 'Syllabus',
  question_paper: 'Question paper',
  marks_sheet: 'Marks sheet',
  rubric: 'Rubric',
  answer_set: 'Answer set',
};

export const BLOOM_ORDER: BloomLevel[] = ['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create'];
export const BLOOM_LABEL: Record<BloomLevel, string> = {
  remember: 'Remember',
  understand: 'Understand',
  apply: 'Apply',
  analyze: 'Analyze',
  evaluate: 'Evaluate',
  create: 'Create',
};

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
