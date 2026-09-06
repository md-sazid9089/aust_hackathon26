import {
  BarChart3,
  CheckCircle2,
  ClipboardCheck,
  FileSearch,
  GitCompareArrows,
  Layers,
  Lock,
  Scale,
  Sigma,
  type LucideIcon,
} from 'lucide-react';

// Planned app entry (architecture.md §13); redirects home until the dashboard route exists.
export const APP_ENTRY_PATH = '/dashboard';

export const NAV_LINKS = [
  { label: 'Problem', href: '#problem' },
  { label: 'Modules', href: '#features' },
  { label: 'How it works', href: '#how-it-works' },
  { label: 'Principles', href: '#principles' },
] as const;

export interface FeatureItem {
  icon: LucideIcon;
  title: string;
  description: string;
}

export const FEATURES: FeatureItem[] = [
  {
    icon: FileSearch,
    title: 'Exam Paper Auditor',
    description:
      'Checks a draft paper against your course outcomes: coverage gaps, over-weighted topics, Bloom-level balance, marks mismatches and near-duplicates from past years.',
  },
  {
    icon: BarChart3,
    title: 'CO–PO Attainment Analyst',
    description:
      'Turns a marks sheet into per-outcome attainment with deterministic arithmetic, then explains which outcomes fell short and why.',
  },
  {
    icon: GitCompareArrows,
    title: 'Syllabus Overlap & Gap Analyzer',
    description:
      'Compares a new syllabus with existing courses to surface duplicated topics, missing prerequisites and repositioning options.',
  },
  {
    icon: Scale,
    title: 'Grading Consistency Calibrator',
    description:
      'Reads a rubric and graded answers from multiple examiners, highlights where they diverge, and proposes clearer rubric wording.',
  },
];

export interface StepItem {
  number: string;
  title: string;
  description: string;
  icon: LucideIcon;
}

export const STEPS: StepItem[] = [
  {
    number: '01',
    title: 'Set up the course once',
    description: 'Add the syllabus, course outcomes and CO→PO map. Every module reuses this one workspace.',
    icon: Layers,
  },
  {
    number: '02',
    title: 'Upload an artefact',
    description: 'A question paper, marks sheet, rubric with answers, or a draft syllabus — PDF, DOCX, TXT, CSV or pasted text.',
    icon: ClipboardCheck,
  },
  {
    number: '03',
    title: 'AI evaluates, code computes',
    description: 'The model maps questions to outcomes and classifies; all percentages and statistics are computed deterministically.',
    icon: Sigma,
  },
  {
    number: '04',
    title: 'You decide',
    description: 'Review each finding with its rationale and evidence, accept or dismiss it, then export what you accepted.',
    icon: CheckCircle2,
  },
];

export interface PrincipleItem {
  icon: LucideIcon;
  title: string;
  description: string;
}

export const PRINCIPLES: PrincipleItem[] = [
  {
    icon: CheckCircle2,
    title: 'Every finding carries evidence',
    description: 'A rationale and a quoted snippet from your document accompany each result, so you can verify before you act.',
  },
  {
    icon: Sigma,
    title: 'Numbers are never guessed',
    description: 'Attainment, coverage and divergence are computed in code. The model only classifies, maps and explains.',
  },
  {
    icon: Lock,
    title: 'Your data stays yours',
    description: 'Courses and artefacts are scoped to their owner, student identifiers are anonymised, and API keys never reach the browser.',
  },
];

export const PROBLEM_POINTS = [
  'Does this paper actually cover every course outcome, or does it lean on the same two chapters?',
  'Did a near-identical question appear in 2024? Which Bloom levels are missing entirely?',
  'Which outcomes did the cohort fail to attain, and how do we show it with data?',
  'Two examiners, same script, different marks — where does the rubric leave room for interpretation?',
] as const;

export const SOLUTION_POINTS = [
  'One course workspace with your outcomes; four modules that reuse it.',
  'Upload the artefact you already have — no re-typing, no new formats.',
  'Evidence-backed findings you accept or dismiss; the tool advises, you decide.',
  'Export the accepted findings as a report for your department or accreditation file.',
] as const;
