import type * as T from '@/lib/types/api';
import * as F from './fixtures';

// Deterministic "analysis" producing summary + findings for each module. Numbers here are
// computed from fixtures; rationale strings stand in for LLM output in demo mode.

let counter = 0;
const uid = (p: string) => `${p}-${(++counter).toString(36)}-${Math.random().toString(36).slice(2, 7)}`;

const mkFinding = (
  runId: string,
  f: Omit<T.Finding, 'id' | 'run_id' | 'status' | 'decided_at' | 'payload'> & { payload?: Record<string, unknown> },
): T.Finding => ({ id: uid('f'), run_id: runId, status: 'open', decided_at: null, payload: {}, ...f });

export const STAGES: Record<T.RunModule, { stage: string; message: string; pct: number }[]> = {
  exam_audit: [
    { stage: 'load_inputs', message: 'Loading draft paper, past papers and course outcomes', pct: 10 },
    { stage: 'embed_questions', message: 'Embedding 16 questions for similarity search', pct: 30 },
    { stage: 'map_and_bloom', message: 'Mapping questions to COs/topics and Bloom levels', pct: 55 },
    { stage: 'find_duplicates', message: 'Checking near-duplicates against past papers', pct: 75 },
    { stage: 'compute_stats', message: 'Computing coverage, weights and Bloom distribution', pct: 90 },
    { stage: 'build_findings', message: 'Writing findings with evidence', pct: 100 },
  ],
  attainment: [
    { stage: 'load', message: 'Loading marks sheet and question→CO map', pct: 15 },
    { stage: 'compute', message: 'Computing CO and PO attainment (deterministic)', pct: 55 },
    { stage: 'explain', message: 'Explaining under-performing COs', pct: 85 },
    { stage: 'persist', message: 'Saving results', pct: 100 },
  ],
  syllabus_check: [
    { stage: 'load', message: 'Loading draft syllabus and comparison courses', pct: 10 },
    { stage: 'embed_topics', message: 'Embedding topics', pct: 30 },
    { stage: 'pairwise', message: 'Finding similar topic pairs (pgvector)', pct: 50 },
    { stage: 'judge_overlap', message: 'Judging overlap vs prerequisite', pct: 75 },
    { stage: 'find_gaps', message: 'Looking for missing standard topics', pct: 90 },
    { stage: 'persist', message: 'Saving results', pct: 100 },
  ],
  calibration: [
    { stage: 'load', message: 'Loading rubric and graded answers', pct: 10 },
    { stage: 'divergence', message: 'Computing grader divergence per criterion', pct: 35 },
    { stage: 'explain', message: 'Explaining divergent scores', pct: 60 },
    { stage: 'prescore', message: 'Pre-scoring answers against the rubric', pct: 80 },
    { stage: 'rubric_v2', message: 'Proposing clarified rubric descriptors', pct: 100 },
  ],
};

export function examAudit(runId: string, inputs: T.RunInputsExamAudit, params: Record<string, unknown>) {
  const draft = F.questions[inputs.draft_artefact_id] ?? [];
  const cos = F.courseOutcomes[F.ids.course];
  const total = draft.reduce((s, x) => s + x.marks, 0);
  const overweight = Number(params.overweight_factor ?? 1.5);
  const expected = 1 / cos.length;

  const coverage: T.CoverageCell[] = cos.map((co) => {
    const m = draft.filter((x) => x.co_ids.includes(co.id)).reduce((s, x) => s + x.marks, 0);
    const share = total ? m / total : 0;
    return {
      target_kind: 'course_outcome',
      target_code: co.code,
      marks: m,
      share,
      expected_share: expected,
      status: m === 0 ? 'uncovered' : share > expected * overweight ? 'overweight' : 'covered',
    };
  });
  for (const t of F.topics[F.ids.course]) {
    const m = draft.filter((x) => x.topic_ids.includes(t.id)).reduce((s, x) => s + x.marks, 0);
    coverage.push({ target_kind: 'topic', target_code: t.code, marks: m, share: total ? m / total : 0, expected_share: 1 / 10, status: m === 0 ? 'uncovered' : 'covered' });
  }
  const covered = cos.filter((co) => coverage.find((c) => c.target_code === co.code)?.status !== 'uncovered').length;
  const bloom: Partial<Record<T.BloomLevel, number>> = {};
  for (const x of draft) if (x.bloom_level) bloom[x.bloom_level] = (bloom[x.bloom_level] ?? 0) + 1;

  const duplicates = [{ draft_number: '4', past_label: 'Final Exam 2024', past_number: '3', similarity: 0.94 }];

  const summary: T.ExamAuditSummary = {
    coverage_pct: Math.round((covered / cos.length) * 100),
    coverage,
    bloom,
    duplicates,
    fairness: { deviation_score: 0.31, notes: 'Marks are concentrated on CO2 (50 of 100). Q5 and Q7 carry 15 marks each for procedural tracing.' },
  };

  const findings: T.Finding[] = [];
  for (const c of coverage.filter((c) => c.target_kind === 'course_outcome')) {
    const co = cos.find((x) => x.code === c.target_code)!;
    if (c.status === 'uncovered') {
      findings.push(
        mkFinding(runId, {
          type: 'coverage_gap',
          severity: 'high',
          title: `${co.code} is not assessed by any question`,
          rationale: `None of the 8 draft questions map to ${co.code} ("${co.text}"). The 2024 paper assessed it with Q6 (3-SAT → CLIQUE reduction, 15 marks). Dropping it leaves an outcome with no evidence for attainment.`,
          evidence_snippet: `Mapped COs across draft: CO1(10) CO2(50) CO3(15) CO4(30) CO5(0) CO6(0)`,
          target_kind: 'course_outcome',
          target_id: co.id,
          target_label: co.code,
          payload: { marks: 0 },
        }),
      );
    }
    if (c.status === 'overweight') {
      findings.push(
        mkFinding(runId, {
          type: 'overweight',
          severity: 'medium',
          title: `${co.code} carries ${Math.round(c.share * 100)}% of marks (expected ≈ ${Math.round(expected * 100)}%)`,
          rationale: `Questions 2, 3, 6 and 8 all assess ${co.code}. Four questions on greedy/divide-and-conquer means a student weak in one strategy loses half the paper, while CO5 and CO6 have no marks at all.`,
          evidence_snippet: `Q2 (15) Huffman · Q3 (10) merge sort tree · Q6 (10) activity selection proof · Q8 (10) greedy-choice property`,
          target_kind: 'course_outcome',
          target_id: co.id,
          target_label: co.code,
          payload: { share: c.share, expected_share: expected, factor: c.share / expected },
        }),
      );
    }
  }
  findings.push(
    mkFinding(runId, {
      type: 'duplicate',
      severity: 'high',
      title: 'Draft Q4 is a near-duplicate of 2024 Q3 (similarity 0.94)',
      rationale: 'Both questions ask for the LCS length of the same strings X="ABCBDAB", Y="BDCABA" with a DP table. Only the wording changed. Students with access to the 2024 paper can reproduce the answer from memory.',
      evidence_snippet: 'Draft Q4: "Given X = "ABCBDAB" and Y = "BDCABA", compute the length of the longest common subsequence…"\n2024 Q3: "Given two strings X = "ABCBDAB" and Y = "BDCABA", compute the LCS length using dynamic programming…"',
      target_kind: 'question',
      target_id: 'q25-4',
      target_label: 'Q4',
      payload: { similarity: 0.94, past_label: 'Final Exam 2024', past_number: '3' },
    }),
    mkFinding(runId, {
      type: 'bloom_imbalance',
      severity: 'medium',
      title: '6 of 8 questions sit at Bloom "Apply"; nothing at "Analyze" or "Create"',
      rationale: 'CO1 (analyze) and CO3 (create) expect higher-order thinking, yet every mapped question asks for a procedure trace. The 2024 paper had two Analyze and two Evaluate items.',
      evidence_snippet: 'Bloom counts — apply: 6, evaluate: 1, understand: 1, analyze: 0, create: 0',
      target_kind: 'none',
      target_id: null,
      target_label: null,
      payload: { bloom },
    }),
    mkFinding(runId, {
      type: 'fairness',
      severity: 'low',
      title: 'Mark distribution is uneven across strategies',
      rationale: 'Half of the paper (50/100) rewards one problem-solving strategy family. Consider moving 10 marks from Q2 to a CO5 reduction item.',
      evidence_snippet: 'Deviation score 0.31 (0 = perfectly even). Per-CO shares: 10% / 50% / 15% / 30% / 0% / 0%',
      target_kind: 'course',
      target_id: F.ids.course,
      target_label: 'CSE 2201',
    }),
    mkFinding(runId, {
      type: 'coverage_gap',
      severity: 'medium',
      title: 'CO6 (evaluate trade-offs) has no marks',
      rationale: 'No question asks students to compare or justify a design choice. 2024 Q8 (knapsack DP vs greedy) served this outcome.',
      evidence_snippet: 'CO6 marks: 0 · nearest candidate: Q8 "Explain the greedy-choice property…" (understand, not evaluate)',
      target_kind: 'course_outcome',
      target_id: 'co-6',
      target_label: 'CO6',
    }),
  );
  for (const t of coverage.filter((c) => c.target_kind === 'topic' && c.status === 'uncovered')) {
    findings.push(
      mkFinding(runId, {
        type: 'coverage_gap',
        severity: 'info',
        title: `Topic ${t.target_code} not assessed`,
        rationale: `No draft question maps to "${F.topics[F.ids.course].find((x) => x.code === t.target_code)?.title}".`,
        evidence_snippet: `Topic ${t.target_code}: 0 marks`,
        target_kind: 'topic',
        target_id: F.topics[F.ids.course].find((x) => x.code === t.target_code)?.id ?? null,
        target_label: t.target_code,
      }),
    );
  }
  return { summary, findings };
}

export function suggestions(runId: string, coIds?: string[]): T.Finding[] {
  const cos = F.courseOutcomes[F.ids.course].filter((c) => (coIds ? coIds.includes(c.id) : ['co-5', 'co-6'].includes(c.id)));
  const bank: Record<string, { bloom: T.BloomLevel; text: string; why: string }> = {
    'co-5': { bloom: 'analyze', text: 'Show that VERTEX-COVER is NP-complete by giving a polynomial-time reduction from CLIQUE. State the mapping and argue both directions.', why: 'Replaces the missing reduction question; different problem pair from 2024 Q6 to avoid repetition.' },
    'co-6': { bloom: 'evaluate', text: 'A logistics company must plan deliveries for 10⁴ parcels each morning. Compare a DP formulation and a greedy heuristic for route ordering, and recommend one with justification of the time/quality trade-off.', why: 'Requires judgement about trade-offs (evaluate) rather than a procedure trace.' },
    'co-1': { bloom: 'analyze', text: 'Derive the recurrence for a divide-and-conquer algorithm that splits into three parts and merges in linear time; solve it and compare with merge sort.', why: 'Moves CO1 above pure application.' },
  };
  return cos.map((co) => {
    const b = bank[co.id] ?? bank['co-1'];
    return mkFinding(runId, {
      type: 'suggestion',
      severity: 'info',
      title: `Suggested question for ${co.code} (${b.bloom})`,
      rationale: b.why,
      evidence_snippet: b.text,
      target_kind: 'course_outcome',
      target_id: co.id,
      target_label: co.code,
      payload: { bloom_level: b.bloom, question_text: b.text },
    });
  });
}

export function attainment(runId: string, inputs: T.RunInputsAttainment) {
  const sheet = F.marks[inputs.marks_artefact_id];
  const qs = F.questions[inputs.paper_artefact_id] ?? [];
  const cos = F.courseOutcomes[F.ids.course];
  const threshold = inputs.threshold ?? 60;

  const perCo = cos.map((co) => {
    const coQs = qs.filter((x) => x.co_ids.includes(co.id));
    if (!coQs.length) return { co_id: co.id, co_code: co.code, attained_pct: 0, students: 0, target_pct: threshold, met: false };
    const max = coQs.reduce((s, x) => s + x.marks, 0);
    const attained = sheet.rows.filter((r) => coQs.reduce((s, x) => s + (r.scores[x.number] ?? 0), 0) / max >= threshold / 100).length;
    const pct = Math.round((attained / sheet.rows.length) * 1000) / 10;
    return { co_id: co.id, co_code: co.code, attained_pct: pct, students: sheet.rows.length, target_pct: threshold, met: pct >= threshold };
  });
  const pos = F.programOutcomes
    .map((po) => {
      const cells = F.coPoMap[F.ids.course].filter((c) => c.po_id === po.id && c.strength > 0);
      if (!cells.length) return null;
      const w = cells.reduce((s, c) => s + c.strength, 0);
      const pct = Math.round((cells.reduce((s, c) => s + c.strength * (perCo.find((p) => p.co_id === c.co_id)?.attained_pct ?? 0), 0) / w) * 10) / 10;
      return { po_id: po.id, po_code: po.code, attained_pct: pct, met: pct >= threshold };
    })
    .filter((x): x is NonNullable<typeof x> => !!x);

  const out: T.AttainmentOut = { threshold, cos: perCo, pos };
  const summary: T.AttainmentSummary = { threshold, cos_met: perCo.filter((c) => c.met).length, cos_total: perCo.length, pos_met: pos.filter((p) => p.met).length, pos_total: pos.length };

  const findings: T.Finding[] = [];
  for (const c of perCo.filter((c) => !c.met)) {
    const coQs = qs.filter((x) => x.co_ids.includes(c.co_id));
    const lowest = coQs
      .map((x) => ({ n: x.number, avg: sheet.rows.reduce((s, r) => s + (r.scores[x.number] ?? 0), 0) / sheet.rows.length / x.marks }))
      .sort((a, b) => a.avg - b.avg)[0];
    findings.push(
      mkFinding(runId, {
        type: 'co_underperformance',
        severity: c.attained_pct < threshold - 20 ? 'high' : 'medium',
        title: `${c.co_code}: ${c.attained_pct}% of students reached the ${threshold}% target`,
        rationale:
          c.co_code === 'CO3'
            ? 'Only Q3 and Q8 assess dynamic programming, and Q3 (LCS table) had the lowest class average on the paper. Students appear to know the recurrence but lose marks filling the table — a procedural fluency gap rather than a conceptual one.'
            : `Attainment for ${c.co_code} falls below the target. The weakest contributing question was Q${lowest?.n ?? '—'}.`,
        evidence_snippet: `Computed: ${c.attained_pct}% attained (n=${c.students}, threshold ${threshold}%). Lowest question: Q${lowest?.n} avg ${(100 * (lowest?.avg ?? 0)).toFixed(0)}% of max.`,
        target_kind: 'course_outcome',
        target_id: c.co_id,
        target_label: c.co_code,
        payload: { attained_pct: c.attained_pct, threshold },
      }),
      mkFinding(runId, {
        type: 'action',
        severity: 'info',
        title: `Suggested action for ${c.co_code}`,
        rationale: c.co_code === 'CO3' ? 'Add a timed in-class DP table-filling exercise (LCS, knapsack) two weeks before the final; publish a worked table with common off-by-one errors marked.' : `Add formative practice targeting ${c.co_code} before the next assessment.`,
        evidence_snippet: null,
        target_kind: 'course_outcome',
        target_id: c.co_id,
        target_label: c.co_code,
      }),
    );
  }
  for (const p of pos.filter((p) => !p.met)) {
    findings.push(
      mkFinding(runId, {
        type: 'po_underperformance',
        severity: 'low',
        title: `${p.po_code} weighted attainment ${p.attained_pct}% (< ${threshold}%)`,
        rationale: `Derived from CO→PO strengths; the shortfall is inherited from under-performing COs mapped to ${p.po_code}.`,
        evidence_snippet: `Computed from co_po_map strengths (weighted mean).`,
        target_kind: 'program_outcome',
        target_id: p.po_id,
        target_label: p.po_code,
      }),
    );
  }
  return { summary, findings, out };
}

export function syllabusCheck(runId: string, inputs: T.RunInputsSyllabusCheck) {
  const matrix: T.OverlapCell[] = [
    { course_code: 'CSE 2101', topic_a: 'T2 Divide and conquer: merge sort, quicksort, Strassen', topic_b: 'T5 Sorting: insertion, merge, quick, heap', similarity: 0.83, relation: 'overlap' },
    { course_code: 'CSE 2101', topic_a: 'T5 Graph traversal: BFS, DFS, topological sort', topic_b: 'T6 Graph representation, BFS and DFS', similarity: 0.88, relation: 'overlap' },
    { course_code: 'CSE 2101', topic_a: 'T1 Asymptotic notation and recurrences', topic_b: 'T2 Recursion and complexity basics', similarity: 0.79, relation: 'prerequisite' },
  ];
  const summary: T.SyllabusCheckSummary = { matrix, overlap_pct: 20 };
  const findings: T.Finding[] = [
    mkFinding(runId, {
      type: 'overlap',
      severity: 'medium',
      title: 'Graph traversal (T5) repeats CSE 2101 T6 (similarity 0.88)',
      rationale: 'Both syllabi teach BFS/DFS from scratch. In CSE 2201 this could be a one-lecture refresher, freeing time for topological sort applications and DAG shortest paths.',
      evidence_snippet: 'CSE 2201 T5: "Graph traversal: BFS, DFS, topological sort" ↔ CSE 2101 T6: "Graph representation, BFS and DFS"',
      target_kind: 'topic',
      target_id: 't-5',
      target_label: 'T5',
      payload: { similarity: 0.88, other_course: 'CSE 2101' },
    }),
    mkFinding(runId, {
      type: 'overlap',
      severity: 'low',
      title: 'Sorting under divide-and-conquer (T2) overlaps CSE 2101 T5 (0.83)',
      rationale: 'Merge sort and quicksort are implemented in Data Structures. Keep them here only as analysis examples (recurrences, worst-case), and add Strassen as the new material.',
      evidence_snippet: 'CSE 2201 T2 ↔ CSE 2101 T5, similarity 0.83',
      target_kind: 'topic',
      target_id: 't-2',
      target_label: 'T2',
    }),
    mkFinding(runId, {
      type: 'prerequisite_gap',
      severity: 'info',
      title: 'T1 assumes recursion/complexity basics from CSE 2101 T2',
      rationale: 'Classified as prerequisite rather than overlap: CSE 2201 builds on it. No action needed if CSE 2101 is a hard prerequisite.',
      evidence_snippet: 'similarity 0.79 · relation: prerequisite',
      target_kind: 'topic',
      target_id: 't-1',
      target_label: 'T1',
    }),
    mkFinding(runId, {
      type: 'missing_topic',
      severity: 'medium',
      title: 'Amortised analysis is absent',
      rationale: 'Standard algorithms syllabi (CLRS ch. 17, ACM CS2013 AL/Basic Analysis) include amortised analysis; it is needed for union-find in Kruskal (T7) which the syllabus does teach.',
      evidence_snippet: 'Draft topics T1–T10 contain no mention of "amortised", "potential method" or "union-find".',
      target_kind: 'course',
      target_id: F.ids.course,
      target_label: 'CSE 2201',
    }),
    mkFinding(runId, {
      type: 'repositioning',
      severity: 'info',
      title: 'Move T8 Network flow after T9 NP-completeness?',
      rationale: 'Flow is typically taught as an example of a polynomial problem contrasted with NP-hard variants; ordering T9 before T8 gives that contrast. Optional.',
      evidence_snippet: null,
      target_kind: 'topic',
      target_id: 't-8',
      target_label: 'T8',
    }),
  ];
  void inputs;
  return { summary, findings };
}

export function calibration(runId: string, inputs: T.RunInputsCalibration) {
  const ans = F.answers[inputs.answer_set_artefact_id] ?? [];
  const crit = F.rubric[inputs.rubric_artefact_id] ?? [];
  const graders = [...new Set(ans.flatMap((a) => a.grader_scores.map((g) => g.grader_label)))];
  let divergentAnswers = 0;
  let devSum = 0;
  let devN = 0;
  const flagged = new Set<string>();
  const findings: T.Finding[] = [];
  for (const a of ans) {
    let any = false;
    for (const c of crit) {
      const scores = a.grader_scores.filter((g) => g.criterion_code === c.code).map((g) => g.score);
      const range = Math.max(...scores) - Math.min(...scores);
      devSum += range;
      devN++;
      if (range >= 0.25 * c.max_score) {
        any = true;
        flagged.add(c.code);
        findings.push(
          mkFinding(runId, {
            type: 'divergence',
            severity: range >= 0.5 * c.max_score ? 'high' : 'medium',
            title: `${a.student_anon_id} · ${c.code}: graders differ by ${range} of ${c.max_score}`,
            rationale:
              c.code === 'C4'
                ? 'Grader A penalised the Bangla answer for brevity under "Clarity", Grader B scored full marks. The descriptor "well-structured, readable" does not say whether language or length affects clarity.'
                : c.code === 'C1'
                  ? 'Grader A read the missing explicit subproblem definition as "unclear", Grader B inferred it from the correct table. The rubric does not state whether an implicit definition counts.'
                  : `Grader scores ${scores.join(' vs ')} for "${c.text}". Interpretations differ on whether stated-but-unjustified bounds earn the middle level.`,
            evidence_snippet: `${graders.map((g, i) => `${g}: ${scores[i]}`).join(' · ')}\nAnswer excerpt: "${a.text.slice(0, 140)}…"`,
            target_kind: 'answer',
            target_id: a.id ?? null,
            target_label: `${a.student_anon_id}/${c.code}`,
            payload: { scores, criterion: c.code },
          }),
        );
      }
    }
    if (any) divergentAnswers++;
  }
  for (const code of flagged) {
    const c = crit.find((x) => x.code === code)!;
    findings.push(
      mkFinding(runId, {
        type: 'rubric_clarification',
        severity: 'medium',
        title: `Clarify ${c.code} "${c.text}"`,
        rationale:
          c.code === 'C4'
            ? 'Proposed: "Clarity is judged on structure and logical flow only; language (Bangla/English) and length do not affect the score."'
            : c.code === 'C1'
              ? 'Proposed: "Subproblems may be defined implicitly through a correct recurrence; award Adequate if the recurrence is correct but the state is not named."'
              : 'Proposed: "Adequate requires the bound to be stated with at least one sentence of justification."',
        evidence_snippet: `Current descriptors: ${c.levels.map((l) => `${l.label} (${l.score}): ${l.descriptor}`).join(' | ')}`,
        target_kind: 'criterion',
        target_id: c.id ?? null,
        target_label: c.code,
        payload: {
          proposed: {
            ...c,
            levels: c.levels.map((l) =>
              l.label === 'Adequate'
                ? { ...l, descriptor: c.code === 'C4' ? 'Understandable structure; language and length are not penalised' : c.code === 'C1' ? 'Recurrence correct; subproblem state implicit or briefly named' : 'Bounds stated with brief justification' }
                : l,
            ),
          },
        },
      }),
    );
  }
  const summary: T.CalibrationSummary = { graders, divergent_answers: divergentAnswers, mean_abs_dev: Math.round((devSum / Math.max(devN, 1)) * 100) / 100, criteria_flagged: [...flagged] };
  const prescores: T.Prescore[] = ans.flatMap((a) =>
    crit.map((c) => {
      const gsc: Record<string, number> = {};
      for (const g of a.grader_scores.filter((g) => g.criterion_code === c.code)) gsc[g.grader_label] = g.score;
      const vals = Object.values(gsc);
      const ai = Math.round(vals.reduce((s, v) => s + v, 0) / vals.length);
      return {
        answer_id: a.id!,
        student_anon_id: a.student_anon_id,
        criterion_code: c.code,
        ai_score: ai,
        rationale: `Matches level "${c.levels.find((l) => l.score <= ai)?.label ?? 'Weak'}": ${c.levels.find((l) => l.score <= ai)?.descriptor ?? ''}.`,
        grader_scores: gsc,
      };
    }),
  );
  return { summary, findings, prescores };
}
