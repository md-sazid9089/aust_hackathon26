import type * as T from '@/lib/types/api';

// Demo fixtures — course "CSE 2201 Algorithms" with planted defects (architecture §21.6):
// CO5 uncovered · draft Q4 ≈ 2024 Q3 · CO2 overweight · CO3 weak attainment · 2 divergent answers.

export const ids = {
  faculty: 'u-faculty-0001',
  admin: 'u-admin-0001',
  course: 'c-cse2201',
  course2: 'c-cse2101',
  co: ['co-1', 'co-2', 'co-3', 'co-4', 'co-5', 'co-6'],
  po: Array.from({ length: 12 }, (_, i) => `po-${i + 1}`),
  syllabus: 'a-syllabus-2025',
  paper2024: 'a-paper-2024',
  paper2025: 'a-paper-2025-draft',
  marks2024: 'a-marks-2024',
  rubric: 'a-rubric-a1',
  answers: 'a-answers-a1',
  syllabus2: 'a-syllabus-cse2101',
};

const now = new Date();
const daysAgo = (d: number) => new Date(now.getTime() - d * 86400000).toISOString();

export const profiles: Record<string, T.Profile> = {
  [ids.faculty]: {
    id: ids.faculty,
    email: 'faculty@aust.edu',
    full_name: 'Dr. Farhana Rahman',
    role: 'faculty',
    is_active: true,
    created_at: daysAgo(40),
  },
  [ids.admin]: {
    id: ids.admin,
    email: 'admin@aust.edu',
    full_name: 'Prof. Kamal Hossain',
    role: 'admin',
    is_active: true,
    created_at: daysAgo(60),
  },
};

export const courses: T.Course[] = [
  {
    id: ids.course,
    code: 'CSE 2201',
    title: 'Algorithms',
    term: 'Spring 2026',
    description: 'Design and analysis of algorithms: divide & conquer, greedy, dynamic programming, graphs, NP-completeness.',
    is_demo: true,
    created_at: daysAgo(30),
    counts: { artefacts: 6, runs: 0, outcomes: 6 },
  },
  {
    id: ids.course2,
    code: 'CSE 2101',
    title: 'Data Structures',
    term: 'Fall 2025',
    description: 'Linear and non-linear data structures, sorting, hashing, trees and graph basics.',
    is_demo: true,
    created_at: daysAgo(90),
    counts: { artefacts: 1, runs: 0, outcomes: 4 },
  },
];

export const programOutcomes: T.ProgramOutcome[] = [
  'Engineering knowledge',
  'Problem analysis',
  'Design/development of solutions',
  'Investigation',
  'Modern tool usage',
  'The engineer and society',
  'Environment and sustainability',
  'Ethics',
  'Individual and team work',
  'Communication',
  'Project management and finance',
  'Life-long learning',
].map((text, i) => ({ id: ids.po[i], code: `PO${i + 1}`, text, sort_order: i }));

export const courseOutcomes: Record<string, T.CourseOutcome[]> = {
  [ids.course]: [
    { id: 'co-1', code: 'CO1', text: 'Analyse the asymptotic time and space complexity of algorithms.', bloom_level: 'analyze', weight: 1 },
    { id: 'co-2', code: 'CO2', text: 'Apply divide-and-conquer and greedy strategies to solve problems.', bloom_level: 'apply', weight: 1 },
    { id: 'co-3', code: 'CO3', text: 'Formulate and solve problems using dynamic programming.', bloom_level: 'create', weight: 1 },
    { id: 'co-4', code: 'CO4', text: 'Apply graph algorithms for shortest paths, spanning trees and flows.', bloom_level: 'apply', weight: 1 },
    { id: 'co-5', code: 'CO5', text: 'Explain NP-completeness and reason about reductions between problems.', bloom_level: 'understand', weight: 1 },
    { id: 'co-6', code: 'CO6', text: 'Evaluate algorithmic trade-offs and communicate design decisions.', bloom_level: 'evaluate', weight: 1 },
  ],
  [ids.course2]: [
    { id: 'co2-1', code: 'CO1', text: 'Implement linear data structures and analyse their operations.', bloom_level: 'apply', weight: 1 },
    { id: 'co2-2', code: 'CO2', text: 'Use trees and hashing for efficient search.', bloom_level: 'apply', weight: 1 },
    { id: 'co2-3', code: 'CO3', text: 'Compare sorting algorithms by complexity.', bloom_level: 'analyze', weight: 1 },
    { id: 'co2-4', code: 'CO4', text: 'Represent graphs and perform traversals.', bloom_level: 'apply', weight: 1 },
  ],
};

export const coPoMap: Record<string, T.CoPoCell[]> = {
  [ids.course]: [
    { co_id: 'co-1', po_id: 'po-1', strength: 3 },
    { co_id: 'co-1', po_id: 'po-2', strength: 2 },
    { co_id: 'co-2', po_id: 'po-2', strength: 3 },
    { co_id: 'co-2', po_id: 'po-3', strength: 2 },
    { co_id: 'co-3', po_id: 'po-3', strength: 3 },
    { co_id: 'co-3', po_id: 'po-2', strength: 2 },
    { co_id: 'co-4', po_id: 'po-3', strength: 2 },
    { co_id: 'co-4', po_id: 'po-5', strength: 1 },
    { co_id: 'co-5', po_id: 'po-1', strength: 2 },
    { co_id: 'co-5', po_id: 'po-4', strength: 1 },
    { co_id: 'co-6', po_id: 'po-10', strength: 3 },
    { co_id: 'co-6', po_id: 'po-12', strength: 1 },
  ],
  [ids.course2]: [],
};

export const topics: Record<string, T.Topic[]> = {
  [ids.course]: [
    ['T1', 'Asymptotic notation and recurrences'],
    ['T2', 'Divide and conquer: merge sort, quicksort, Strassen'],
    ['T3', 'Greedy algorithms: activity selection, Huffman coding'],
    ['T4', 'Dynamic programming: LCS, knapsack, matrix chain'],
    ['T5', 'Graph traversal: BFS, DFS, topological sort'],
    ['T6', 'Shortest paths: Dijkstra, Bellman-Ford, Floyd-Warshall'],
    ['T7', 'Minimum spanning trees: Kruskal, Prim'],
    ['T8', 'Network flow: Ford-Fulkerson'],
    ['T9', 'NP-completeness and reductions'],
    ['T10', 'Approximation algorithms (intro)'],
  ].map(([code, title], i) => ({ id: `t-${i + 1}`, code, title, source_artefact_id: ids.syllabus })),
  [ids.course2]: [
    ['T1', 'Arrays, linked lists, stacks and queues'],
    ['T2', 'Recursion and complexity basics'],
    ['T3', 'Binary search trees and balanced trees'],
    ['T4', 'Hashing and hash tables'],
    ['T5', 'Sorting: insertion, merge, quick, heap'],
    ['T6', 'Graph representation, BFS and DFS'],
  ].map(([code, title], i) => ({ id: `t2-${i + 1}`, code, title, source_artefact_id: ids.syllabus2 })),
};

export const artefacts: T.Artefact[] = [
  { id: ids.syllabus, course_id: ids.course, kind: 'syllabus', label: 'CSE 2201 Syllabus (2025 draft)', year: 2025, term: null, mime: 'application/pdf', lang: 'en', status: 'done', error: null, created_at: daysAgo(20), counts: { topics: 10 } },
  { id: ids.paper2024, course_id: ids.course, kind: 'question_paper', label: 'Final Exam 2024', year: 2024, term: 'Fall', mime: 'application/pdf', lang: 'mixed', status: 'done', error: null, created_at: daysAgo(18), counts: { questions: 8 } },
  { id: ids.paper2025, course_id: ids.course, kind: 'question_paper', label: 'Final Exam 2025 (draft)', year: 2025, term: 'Spring', mime: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', lang: 'en', status: 'done', error: null, created_at: daysAgo(2), counts: { questions: 8 } },
  { id: ids.marks2024, course_id: ids.course, kind: 'marks_sheet', label: 'Final 2024 marks (anonymised)', year: 2024, term: 'Fall', mime: 'text/csv', lang: 'en', status: 'done', error: null, created_at: daysAgo(17), counts: { students: 42, questions: 8 } },
  { id: ids.rubric, course_id: ids.course, kind: 'rubric', label: 'Assignment 1 rubric — DP design', year: 2025, term: 'Spring', mime: 'text/plain', lang: 'en', status: 'done', error: null, created_at: daysAgo(9), counts: { criteria: 4 } },
  { id: ids.answers, course_id: ids.course, kind: 'answer_set', label: 'Assignment 1 answers — graders A/B', year: 2025, term: 'Spring', mime: 'text/csv', lang: 'mixed', status: 'done', error: null, created_at: daysAgo(8), counts: { answers: 6 } },
  { id: ids.syllabus2, course_id: ids.course2, kind: 'syllabus', label: 'CSE 2101 Syllabus', year: 2025, term: null, mime: 'application/pdf', lang: 'en', status: 'done', error: null, created_at: daysAgo(80), counts: { topics: 6 } },
];

const q = (id: string, number: string, text: string, marks: number, bloom: T.BloomLevel, cos: string[], tops: string[]): T.Question => ({
  id,
  number,
  text,
  marks,
  bloom_level: bloom,
  co_ids: cos,
  topic_ids: tops,
});

export const questions: Record<string, T.Question[]> = {
  [ids.paper2024]: [
    q('q24-1', '1', 'Solve the recurrence T(n) = 2T(n/2) + n using the master theorem and state the tight bound.', 10, 'apply', ['co-1'], ['t-1']),
    q('q24-2', '2', 'Prove that the greedy choice is optimal for the activity-selection problem.', 10, 'evaluate', ['co-2'], ['t-3']),
    q('q24-3', '3', 'Given two strings X = "ABCBDAB" and Y = "BDCABA", compute the LCS length using dynamic programming and show the table.', 15, 'apply', ['co-3'], ['t-4']),
    q('q24-4', '4', 'Run Dijkstra’s algorithm on the given weighted graph from source A. Show the distance array after each iteration.', 15, 'apply', ['co-4'], ['t-6']),
    q('q24-5', '5', 'Explain the difference between Kruskal’s and Prim’s algorithms and their complexities.', 10, 'understand', ['co-4'], ['t-7']),
    q('q24-6', '6', 'Show that 3-SAT reduces to CLIQUE in polynomial time.', 15, 'analyze', ['co-5'], ['t-9']),
    q('q24-7', '7', 'Write the pseudocode for quicksort and analyse its worst case.', 10, 'analyze', ['co-1', 'co-2'], ['t-2']),
    q('q24-8', '8', 'Compare a DP and a greedy approach for the fractional and 0/1 knapsack problems; justify which is appropriate.', 15, 'evaluate', ['co-6', 'co-3'], ['t-4']),
  ],
  [ids.paper2025]: [
    q('q25-1', '1', 'Solve T(n) = 4T(n/2) + n² and give the asymptotic bound.', 10, 'apply', ['co-1'], ['t-1']),
    q('q25-2', '2', 'Construct the Huffman code for the given frequency table and compute the average code length.', 15, 'apply', ['co-2'], ['t-3']),
    q('q25-3', '3', 'Show the merge sort recursion tree for 8 elements and count comparisons.', 10, 'apply', ['co-2'], ['t-2']),
    q('q25-4', '4', 'Given X = "ABCBDAB" and Y = "BDCABA", compute the length of the longest common subsequence with a DP table.', 15, 'apply', ['co-3'], ['t-4']),
    q('q25-5', '5', 'Apply Kruskal’s algorithm to the given graph and list edges in the order chosen.', 15, 'apply', ['co-4'], ['t-7']),
    q('q25-6', '6', 'Prove the greedy activity-selection algorithm returns a maximum-size set.', 10, 'evaluate', ['co-2'], ['t-3']),
    q('q25-7', '7', 'Trace Bellman-Ford on the given graph with a negative edge and explain detection of negative cycles.', 15, 'apply', ['co-4'], ['t-6']),
    q('q25-8', '8', 'Explain the greedy-choice property and optimal substructure with one example each.', 10, 'understand', ['co-2'], ['t-3']),
  ],
};

export const marks: Record<string, T.MarksSheet> = {
  [ids.marks2024]: (() => {
    const qs = questions[ids.paper2024];
    const rows = Array.from({ length: 42 }, (_, i) => {
      const seed = (i * 7919) % 100;
      const scores: Record<string, number> = {};
      for (const qq of qs) {
        let frac = 0.55 + ((seed + qq.number.charCodeAt(0) * 13) % 45) / 100;
        if (qq.co_ids.includes('co-3')) frac -= 0.28; // CO3 weak
        if (qq.co_ids.includes('co-5')) frac -= 0.05;
        frac = Math.max(0.1, Math.min(1, frac));
        scores[qq.number] = Math.round(qq.marks * frac * 2) / 2;
      }
      return { student_anon_id: `S${String(i + 1).padStart(3, '0')}`, scores };
    });
    return { students: 42, questions: qs.map((x) => ({ number: x.number, max: x.marks })), rows };
  })(),
};

export const rubric: Record<string, T.RubricCriterion[]> = {
  [ids.rubric]: [
    { id: 'rc-1', code: 'C1', text: 'Correct identification of subproblems and recurrence', max_score: 5, levels: [{ label: 'Excellent', score: 5, descriptor: 'Recurrence is correct and clearly justified' }, { label: 'Adequate', score: 3, descriptor: 'Recurrence mostly correct with minor gaps' }, { label: 'Weak', score: 1, descriptor: 'Subproblems unclear or incorrect' }] },
    { id: 'rc-2', code: 'C2', text: 'Correctness of the DP table / memoisation', max_score: 5, levels: [{ label: 'Excellent', score: 5, descriptor: 'Table fully correct' }, { label: 'Adequate', score: 3, descriptor: 'Few cell errors, method sound' }, { label: 'Weak', score: 1, descriptor: 'Table largely incorrect' }] },
    { id: 'rc-3', code: 'C3', text: 'Complexity analysis', max_score: 5, levels: [{ label: 'Excellent', score: 5, descriptor: 'Tight time and space bounds with justification' }, { label: 'Adequate', score: 3, descriptor: 'Bounds stated without justification' }, { label: 'Weak', score: 1, descriptor: 'Missing or wrong' }] },
    { id: 'rc-4', code: 'C4', text: 'Clarity of explanation', max_score: 5, levels: [{ label: 'Excellent', score: 5, descriptor: 'Well-structured, readable' }, { label: 'Adequate', score: 3, descriptor: 'Understandable but disorganised' }, { label: 'Weak', score: 1, descriptor: 'Hard to follow' }] },
  ],
};

const gs = (a: number[], b: number[]): T.GraderScore[] => [
  ...a.map((s, i) => ({ grader_label: 'Grader A', criterion_code: `C${i + 1}`, score: s })),
  ...b.map((s, i) => ({ grader_label: 'Grader B', criterion_code: `C${i + 1}`, score: s })),
];

export const answers: Record<string, T.Answer[]> = {
  [ids.answers]: [
    { id: 'ans-1', student_anon_id: 'S001', question_ref: 'A1', text: 'Let dp[i][j] be the LCS of prefixes X[1..i], Y[1..j]. If X[i]=Y[j], dp[i][j]=dp[i-1][j-1]+1, else max(dp[i-1][j], dp[i][j-1]). Time O(mn), space O(mn), reducible to O(min(m,n)).', grader_scores: gs([5, 5, 5, 4], [5, 5, 4, 4]) },
    { id: 'ans-2', student_anon_id: 'S002', question_ref: 'A1', text: 'The subproblem is the LCS of suffixes. The recurrence uses +1 on a match. I filled the table but the last row has two mistakes. Complexity is O(n²).', grader_scores: gs([4, 3, 2, 3], [4, 3, 4, 3]) },
    { id: 'ans-3', student_anon_id: 'S003', question_ref: 'A1', text: 'সাবপ্রবলেম হিসেবে প্রিফিক্সের LCS ধরি। মিল হলে dp[i][j] = dp[i-1][j-1] + 1, না হলে বড়টা নিই। টেবিল ভরার পর জটিলতা O(mn)। ব্যাখ্যা সংক্ষিপ্ত রাখা হয়েছে।', grader_scores: gs([5, 4, 5, 2], [5, 4, 5, 5]) },
    { id: 'ans-4', student_anon_id: 'S004', question_ref: 'A1', text: 'I used recursion without memoisation; it works for small strings. Complexity exponential. Subproblems: same as LCS.', grader_scores: gs([3, 1, 1, 3], [3, 1, 2, 3]) },
    { id: 'ans-5', student_anon_id: 'S005', question_ref: 'A1', text: 'Define dp over prefixes, recurrence as standard. Table correct. I state O(mn) time but do not justify. The write-up is in bullet form.', grader_scores: gs([5, 5, 3, 4], [5, 5, 3, 4]) },
    { id: 'ans-6', student_anon_id: 'S006', question_ref: 'A1', text: 'Subproblems are not clearly defined; I jump to the table. Table correct for the given example. Space can be reduced to two rows.', grader_scores: gs([2, 5, 4, 3], [4, 5, 4, 3]) },
  ],
};

export const usage: T.UsageRow[] = [
  { key: 'faculty@aust.edu', calls: 38, tokens_in: 91240, tokens_out: 22810, cost_usd: 0.31, failures: 1 },
  { key: 'admin@aust.edu', calls: 6, tokens_in: 12000, tokens_out: 3100, cost_usd: 0.04, failures: 0 },
];

export const usageByDay: T.UsageRow[] = Array.from({ length: 7 }, (_, i) => ({
  key: daysAgo(6 - i).slice(0, 10),
  calls: [3, 5, 9, 4, 12, 7, 4][i],
  tokens_in: [6000, 11000, 22000, 9500, 28000, 15000, 9200][i],
  tokens_out: [1500, 2700, 5400, 2200, 7100, 3600, 2300][i],
  cost_usd: [0.02, 0.04, 0.08, 0.03, 0.1, 0.05, 0.03][i],
  failures: [0, 0, 1, 0, 0, 0, 0][i],
}));
