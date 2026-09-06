-- seed_demo(p_owner uuid) RETURNS uuid
-- Creates the demo workspace for p_owner: CSE 2201 (full) + CSE 2101 (syllabus only).
-- Structured children (questions, CO maps, marks, rubric, answers) are inserted directly with
-- status='done' so the demo never depends on LLM extraction. Fixture text files in ./fixtures
-- mirror this content for the upload path. Idempotent: returns the existing course id.
-- Marks formula (i = 1..40) must match fixtures/cse2201_marks.csv:
--   Q1 10-(i%4)  Q2 15-(i%5)  Q3 2+((i*7)%9)  Q4 14-(i%6)  Q5 15-(i%4)  Q6 10-(i%3)  Q7 18-(i%7)

CREATE OR REPLACE FUNCTION public.seed_demo(p_owner uuid) RETURNS uuid
LANGUAGE plpgsql SECURITY INVOKER AS $$
DECLARE
  v_course   uuid;
  v_course2  uuid;
  v_syl      uuid;
  v_p2024    uuid;
  v_p2025    uuid;
  v_draft    uuid;
  v_marks    uuid;
  v_rubric   uuid;
  v_answers  uuid;
  v_syl2     uuid;
  co         uuid[];   -- co[1..6]
  tp         uuid[];   -- tp[1..10]
  q          uuid;
  a          uuid;
  i          int;
BEGIN
  PERFORM public.assert_owner_or_admin(p_owner);
  IF public.is_admin() THEN
    PERFORM set_config('app.user_id', p_owner::text, true);
  END IF;

  SELECT id INTO v_course FROM public.courses
   WHERE owner_id = p_owner AND is_demo AND code = 'CSE2201' AND deleted_at IS NULL;
  IF v_course IS NOT NULL THEN
    RETURN v_course;
  END IF;

  -- ---------------- course + outcomes ----------------
  INSERT INTO public.courses (owner_id, code, title, term, description, is_demo)
  VALUES (p_owner, 'CSE2201', 'Design and Analysis of Algorithms', 'Spring 2026',
          'Demo course seeded by seed_demo()', true)
  RETURNING id INTO v_course;

  co := ARRAY[gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid()];
  INSERT INTO public.course_outcomes (id, course_id, code, text, bloom_level, sort_order) VALUES
    (co[1], v_course, 'CO1', 'Analyse the asymptotic time and space complexity of iterative and recursive algorithms.', 'analyze', 1),
    (co[2], v_course, 'CO2', 'Apply divide-and-conquer and comparison-based sorting algorithms to solve problems.', 'apply', 2),
    (co[3], v_course, 'CO3', 'Design dynamic-programming solutions for optimisation problems and justify optimal substructure.', 'create', 3),
    (co[4], v_course, 'CO4', 'Apply greedy algorithms and evaluate the correctness of greedy choices.', 'evaluate', 4),
    (co[5], v_course, 'CO5', 'Apply graph algorithms (BFS, DFS, shortest paths, minimum spanning trees) to model and solve problems.', 'apply', 5),
    (co[6], v_course, 'CO6', 'Explain the classes P, NP and NP-complete and describe polynomial-time reductions.', 'understand', 6);

  INSERT INTO public.co_po_map (co_id, po_id, strength)
  SELECT c.co_id, p.id, c.strength
  FROM (VALUES
    (co[1], 'PO1', 3), (co[1], 'PO2', 3),
    (co[2], 'PO1', 2), (co[2], 'PO3', 3),
    (co[3], 'PO2', 2), (co[3], 'PO3', 3), (co[3], 'PO4', 1),
    (co[4], 'PO2', 3), (co[4], 'PO4', 2),
    (co[5], 'PO1', 2), (co[5], 'PO3', 2), (co[5], 'PO5', 1),
    (co[6], 'PO1', 3), (co[6], 'PO12', 1)
  ) AS c(co_id, po_code, strength)
  JOIN public.program_outcomes p ON p.code = c.po_code;

  -- ---------------- syllabus artefact + topics ----------------
  INSERT INTO public.artefacts (course_id, kind, label, storage_path, mime, lang, status, extracted_text)
  VALUES (v_course, 'syllabus', 'Course syllabus', 'demo/cse2201_syllabus.txt', 'text/plain', 'en', 'done',
          'CSE 2201 Design and Analysis of Algorithms. CO1-CO6 and topics T01-T10 (see fixtures/cse2201_syllabus.txt).')
  RETURNING id INTO v_syl;

  tp := ARRAY[gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(),
              gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid(), gen_random_uuid()];
  INSERT INTO public.topics (id, course_id, code, title, source_artefact_id, sort_order) VALUES
    (tp[1],  v_course, 'T01', 'Asymptotic notation: Big-O, Big-Omega, Big-Theta; growth of functions', v_syl, 1),
    (tp[2],  v_course, 'T02', 'Recurrence relations, substitution method, recursion tree, Master theorem', v_syl, 2),
    (tp[3],  v_course, 'T03', 'Divide and conquer: binary search, maximum subarray, Strassen''s matrix multiplication', v_syl, 3),
    (tp[4],  v_course, 'T04', 'Sorting: merge sort, quicksort, heap sort, lower bound for comparison sorting', v_syl, 4),
    (tp[5],  v_course, 'T05', 'Dynamic programming: rod cutting, 0/1 knapsack, longest common subsequence, matrix-chain', v_syl, 5),
    (tp[6],  v_course, 'T06', 'Greedy algorithms: activity selection, fractional knapsack, Huffman coding', v_syl, 6),
    (tp[7],  v_course, 'T07', 'Graph traversal: BFS, DFS, topological sort, strongly connected components', v_syl, 7),
    (tp[8],  v_course, 'T08', 'Shortest paths: Dijkstra, Bellman-Ford, Floyd-Warshall', v_syl, 8),
    (tp[9],  v_course, 'T09', 'Minimum spanning trees: Prim''s and Kruskal''s algorithms, union-find', v_syl, 9),
    (tp[10], v_course, 'T10', 'NP-completeness: P vs NP, reductions, Vertex Cover, SAT, Hamiltonian cycle', v_syl, 10);

  -- ---------------- past paper 2024 (100 marks) ----------------
  INSERT INTO public.artefacts (course_id, kind, label, year, term, storage_path, mime, lang, status, declared_total_marks, extracted_text)
  VALUES (v_course, 'question_paper', 'Final Exam Fall 2024', 2024, 'Fall', 'demo/cse2201_paper_2024.txt', 'text/plain', 'en', 'done', 100,
          'CSE 2201 Final Examination, Fall 2024 (see fixtures/cse2201_paper_2024.txt)')
  RETURNING id INTO v_p2024;

  INSERT INTO public.questions (artefact_id, number, text, marks, bloom_level, bloom_source, sort_order) VALUES
    (v_p2024, '1',  'Define Big-O and Big-Theta notation. Show that 3n^2 + 2n + 7 = Theta(n^2).', 10, 'understand', 'faculty', 1),
    (v_p2024, '2a', 'Solve the recurrence T(n) = 2T(n/2) + n using the Master theorem and state which case applies.', 10, 'apply', 'faculty', 2),
    (v_p2024, '2b', 'Describe the merge sort algorithm and derive its recurrence relation.', 10, 'understand', 'faculty', 3),
    (v_p2024, '3',  'Consider the 0/1 knapsack instance with weights {2, 3, 4, 5}, values {3, 4, 5, 6} and capacity 5. Fill in the dynamic programming table and find the optimal value.', 15, 'apply', 'faculty', 4),
    (v_p2024, '4',  'Prove that the greedy activity-selection algorithm, which always picks the compatible activity with the earliest finish time, produces an optimal solution.', 15, 'evaluate', 'faculty', 5),
    (v_p2024, '5a', 'Run Dijkstra''s algorithm from source A on the given weighted graph and show the distance table after each iteration.', 10, 'apply', 'faculty', 6),
    (v_p2024, '5b', 'Compare Prim''s and Kruskal''s algorithms for minimum spanning trees in terms of approach and complexity.', 10, 'analyze', 'faculty', 7),
    (v_p2024, '6',  'Define the classes NP and NP-complete. Show that Vertex Cover is NP-complete by giving a polynomial-time reduction from Independent Set.', 20, 'analyze', 'faculty', 8);

  INSERT INTO public.question_co_map (question_id, co_id, confidence, source)
  SELECT qq.id, m.co_id, 1, 'faculty'
  FROM public.questions qq
  JOIN (VALUES ('1', co[1]), ('2a', co[1]), ('2b', co[2]), ('3', co[3]), ('4', co[4]), ('5a', co[5]), ('5b', co[5]), ('6', co[6]))
       AS m(number, co_id) ON m.number = qq.number
  WHERE qq.artefact_id = v_p2024;

  INSERT INTO public.question_topic_map (question_id, topic_id, confidence, source)
  SELECT qq.id, m.topic_id, 1, 'faculty'
  FROM public.questions qq
  JOIN (VALUES ('1', tp[1]), ('2a', tp[2]), ('2b', tp[4]), ('3', tp[5]), ('4', tp[6]), ('5a', tp[8]), ('5b', tp[9]), ('6', tp[10]))
       AS m(number, topic_id) ON m.number = qq.number
  WHERE qq.artefact_id = v_p2024;

  -- ---------------- past paper 2025 (100 marks; the one students sat -> marks sheet) ----------------
  INSERT INTO public.artefacts (course_id, kind, label, year, term, storage_path, mime, lang, status, declared_total_marks, extracted_text)
  VALUES (v_course, 'question_paper', 'Final Exam Fall 2025', 2025, 'Fall', 'demo/cse2201_paper_2025.txt', 'text/plain', 'en', 'done', 100,
          'CSE 2201 Final Examination, Fall 2025 (see fixtures/cse2201_paper_2025.txt)')
  RETURNING id INTO v_p2025;

  INSERT INTO public.questions (artefact_id, number, text, marks, bloom_level, bloom_source, sort_order) VALUES
    (v_p2025, '1', 'Using the definition of Big-O, prove that n log n = O(n^2) and that n^2 is not O(n log n).', 10, 'analyze', 'faculty', 1),
    (v_p2025, '2', 'Trace quicksort on the array [7, 2, 9, 4, 3, 8] using the last element as pivot. Give the worst-case recurrence and solve it.', 15, 'apply', 'faculty', 2),
    (v_p2025, '3', 'Construct the dynamic programming table for the longest common subsequence of X = ABCBDAB and Y = BDCABA. State the length of the LCS and recover one LCS.', 15, 'apply', 'faculty', 3),
    (v_p2025, '4', 'Build the Huffman code for the characters a, b, c, d, e with frequencies 45, 13, 12, 16, 9. Explain why the greedy merge step is safe.', 15, 'evaluate', 'faculty', 4),
    (v_p2025, '5', 'Perform BFS and DFS from vertex 1 on the given undirected graph. Give the discovery order for each traversal and the DFS tree.', 15, 'apply', 'faculty', 5),
    (v_p2025, '6', 'Apply Kruskal''s algorithm to the given weighted graph. List the edges in the order they are added and give the total weight of the MST.', 10, 'apply', 'faculty', 6),
    (v_p2025, '7', 'Define the class NP-complete. Describe a polynomial-time reduction from 3-SAT to Clique and explain why it proves Clique is NP-hard.', 20, 'analyze', 'faculty', 7);

  INSERT INTO public.question_co_map (question_id, co_id, confidence, source)
  SELECT qq.id, m.co_id, 1, 'faculty'
  FROM public.questions qq
  JOIN (VALUES ('1', co[1]), ('2', co[2]), ('3', co[3]), ('4', co[4]), ('5', co[5]), ('6', co[5]), ('7', co[6]))
       AS m(number, co_id) ON m.number = qq.number
  WHERE qq.artefact_id = v_p2025;

  INSERT INTO public.question_topic_map (question_id, topic_id, confidence, source)
  SELECT qq.id, m.topic_id, 1, 'faculty'
  FROM public.questions qq
  JOIN (VALUES ('1', tp[1]), ('2', tp[4]), ('3', tp[5]), ('4', tp[6]), ('5', tp[7]), ('6', tp[9]), ('7', tp[10]))
       AS m(number, topic_id) ON m.number = qq.number
  WHERE qq.artefact_id = v_p2025;

  -- ---------------- draft paper (declared 100, sums to 90; CO5 uncovered; CO2 = 40; Q4 ~ 2024 Q3; no 'create') ----------------
  INSERT INTO public.artefacts (course_id, kind, label, year, term, storage_path, mime, lang, status, declared_total_marks, extracted_text)
  VALUES (v_course, 'question_paper', 'Final Exam Spring 2026 (draft)', 2026, 'Spring', 'demo/cse2201_paper_draft.txt', 'text/plain', 'en', 'done', 100,
          'CSE 2201 Final Examination, Spring 2026 DRAFT (see fixtures/cse2201_paper_draft.txt)')
  RETURNING id INTO v_draft;

  INSERT INTO public.questions (artefact_id, number, text, marks, sort_order) VALUES
    (v_draft, '1', 'State the formal definition of Big-O notation. Explain with an example why constant factors are ignored.', 10, 1),
    (v_draft, '2', 'Trace merge sort on the array [38, 27, 43, 3, 9, 82, 10]. Write the recurrence for merge sort and state its solution.', 15, 2),
    (v_draft, '3', 'Show the partition step of quicksort on [5, 3, 8, 4, 2, 7, 1] with the last element as pivot. Explain when quicksort degrades to O(n^2).', 15, 3),
    (v_draft, '4', 'Consider the 0/1 knapsack problem with item weights {2, 3, 4, 5}, values {3, 4, 5, 6} and knapsack capacity 5. Construct the dynamic programming table and report the optimal value.', 15, 4),
    (v_draft, '5', 'Build a max-heap from [4, 10, 3, 5, 1] and show the array after each step of heap sort.', 10, 5),
    (v_draft, '6', 'Solve the fractional knapsack instance with weights {10, 20, 30}, values {60, 100, 120} and capacity 50 using the greedy method.', 10, 6),
    (v_draft, '7', 'Explain the difference between the classes P and NP. Name two NP-complete problems and describe them briefly.', 15, 7);
  -- draft has no CO/Bloom mapping on purpose: P1 must produce it

  -- ---------------- marks sheet for the 2025 paper ----------------
  INSERT INTO public.artefacts (course_id, kind, label, year, term, storage_path, mime, lang, status, extracted_text)
  VALUES (v_course, 'marks_sheet', 'Final Exam Fall 2025 marks', 2025, 'Fall', 'demo/cse2201_marks.csv', 'text/csv', 'en', 'done',
          'student_anon_id,1,2,Q3.,4,5,6,7 (40 students; see fixtures/cse2201_marks.csv)')
  RETURNING id INTO v_marks;

  INSERT INTO public.marks_rows (artefact_id, student_anon_id, question_number, score, max_score)
  SELECT v_marks, 'S' || lpad(g.i::text, 3, '0'), v.qnum, v.score, v.mx
  FROM generate_series(1, 40) AS g(i)
  CROSS JOIN LATERAL (VALUES
    ('1', 10 - (g.i % 4),        10),
    ('2', 15 - (g.i % 5),        15),
    ('3', 2 + ((g.i * 7) % 9),   15),   -- CO3 weak: only 9 or 10 pass 60 %
    ('4', 14 - (g.i % 6),        15),
    ('5', 15 - (g.i % 4),        15),
    ('6', 10 - (g.i % 3),        10),
    ('7', 18 - (g.i % 7),        20)
  ) AS v(qnum, score, mx);

  -- ---------------- rubric ----------------
  INSERT INTO public.artefacts (course_id, kind, label, storage_path, mime, lang, status, extracted_text)
  VALUES (v_course, 'rubric', 'Algorithm-analysis answer rubric', 'demo/cse2201_rubric.txt', 'text/plain', 'en', 'done',
          'Rubric C1-C4, max 5 each (see fixtures/cse2201_rubric.txt)')
  RETURNING id INTO v_rubric;

  INSERT INTO public.rubric_criteria (artefact_id, code, text, max_score, levels, sort_order) VALUES
    (v_rubric, 'C1', 'Correctness', 5, '[{"label":"Excellent","score":5,"descriptor":"result and reasoning fully correct"},{"label":"Adequate","score":3,"descriptor":"minor slip that does not change the conclusion"},{"label":"Weak","score":1,"descriptor":"major error or unsupported claim"}]', 1),
    (v_rubric, 'C2', 'Completeness', 5, '[{"label":"Excellent","score":5,"descriptor":"all required steps and cases covered"},{"label":"Adequate","score":3,"descriptor":"one required step missing"},{"label":"Weak","score":1,"descriptor":"most steps missing"}]', 2),
    (v_rubric, 'C3', 'Clarity', 5, '[{"label":"Excellent","score":5,"descriptor":"well structured, precise notation"},{"label":"Adequate","score":3,"descriptor":"readable but loosely organised"},{"label":"Weak","score":1,"descriptor":"hard to follow"}]', 3),
    (v_rubric, 'C4', 'Complexity analysis', 5, '[{"label":"Excellent","score":5,"descriptor":"tight bound derived and justified"},{"label":"Adequate","score":3,"descriptor":"correct bound stated without derivation"},{"label":"Weak","score":1,"descriptor":"bound missing or wrong"}]', 4);

  -- ---------------- answer set (6 answers x graders A, B; answers 2 and 5 diverge) ----------------
  INSERT INTO public.artefacts (course_id, kind, label, storage_path, mime, lang, status, grader_labels, extracted_text)
  VALUES (v_course, 'answer_set', 'Merge sort complexity answers', 'demo/cse2201_answers.txt', 'text/plain', 'en', 'done', ARRAY['A','B'],
          '6 typed answers with scores from graders A and B (see fixtures/cse2201_answers.txt)')
  RETURNING id INTO v_answers;

  FOR i IN 1..6 LOOP
    INSERT INTO public.answers (artefact_id, student_anon_id, question_ref, text, sort_order)
    VALUES (v_answers, 'S' || (100 + i)::text, 'Q1',
      CASE i
        WHEN 1 THEN 'Merge sort splits the array into two halves, sorts each half recursively and merges them in linear time. The recurrence is T(n) = 2T(n/2) + cn. Using the recursion tree there are log2 n levels and each level does cn work, so T(n) = O(n log n). This holds for every input because the split does not depend on the data.'
        WHEN 2 THEN 'Merge sort divides and conquers. Merging takes n steps. Because you divide by two each time you get log n divisions. So it is n log n.'
        WHEN 3 THEN 'T(n) = 2T(n/2) + n. By the Master theorem a = 2, b = 2, f(n) = n = Theta(n^(log_b a)), which is case 2, so T(n) = Theta(n log n). The merge step is linear because each element is copied once.'
        WHEN 4 THEN 'Merge sort is fast because it uses recursion. Recursion is usually log n and there are n elements so the total is n log n.'
        WHEN 5 THEN 'Each level of recursion processes all n elements during merging. The depth of recursion is log2 n since the size halves each time. Therefore total work is n times log n. Worst, best and average cases are the same because merge always compares all remaining elements.'
        ELSE        'Merge sort has complexity O(n log n) because the merge is O(n) and there are O(log n) levels. Quicksort can be O(n^2) but merge sort cannot.'
      END, i)
    RETURNING id INTO a;

    INSERT INTO public.grader_scores (answer_id, grader_label, criterion_code, score)
    SELECT a, s.grader, x.crit, x.score
    FROM (VALUES
      -- answer, grader, C1, C2, C3, C4
      (1, 'A', 5,5,5,5), (1, 'B', 5,4,5,5),
      (2, 'A', 4,3,3,2), (2, 'B', 2,1,2,1),
      (3, 'A', 5,4,4,5), (3, 'B', 5,4,4,5),
      (4, 'A', 2,2,2,1), (4, 'B', 2,1,2,1),
      (5, 'A', 5,5,4,4), (5, 'B', 3,3,4,2),
      (6, 'A', 4,3,4,3), (6, 'B', 4,3,3,3)
    ) AS s(ans, grader, c1, c2, c3, c4)
    CROSS JOIN LATERAL (VALUES ('C1', s.c1), ('C2', s.c2), ('C3', s.c3), ('C4', s.c4)) AS x(crit, score)
    WHERE s.ans = i;
  END LOOP;

  -- ---------------- second course for syllabus overlap (P3) ----------------
  INSERT INTO public.courses (owner_id, code, title, term, description, is_demo)
  VALUES (p_owner, 'CSE2101', 'Data Structures', 'Fall 2025', 'Demo comparison course seeded by seed_demo()', true)
  RETURNING id INTO v_course2;

  INSERT INTO public.course_outcomes (course_id, code, text, bloom_level, sort_order) VALUES
    (v_course2, 'CO1', 'Explain the time and space complexity of basic operations using asymptotic notation.', 'understand', 1),
    (v_course2, 'CO2', 'Implement linear data structures (arrays, linked lists, stacks, queues) and their operations.', 'apply', 2),
    (v_course2, 'CO3', 'Implement tree-based structures (binary search trees, heaps) and analyse their operations.', 'analyze', 3),
    (v_course2, 'CO4', 'Apply hashing techniques and collision-resolution strategies.', 'apply', 4),
    (v_course2, 'CO5', 'Apply graph representations and traversal algorithms to solve problems.', 'apply', 5);

  INSERT INTO public.artefacts (course_id, kind, label, storage_path, mime, lang, status, extracted_text)
  VALUES (v_course2, 'syllabus', 'Course syllabus', 'demo/cse2101_syllabus.txt', 'text/plain', 'en', 'done',
          'CSE 2101 Data Structures. CO1-CO5 and topics T01-T10 (see fixtures/cse2101_syllabus.txt).')
  RETURNING id INTO v_syl2;

  INSERT INTO public.topics (course_id, code, title, source_artefact_id, sort_order) VALUES
    (v_course2, 'T01', 'Complexity basics: Big-O notation, best/average/worst case', v_syl2, 1),
    (v_course2, 'T02', 'Recursion and simple recurrence relations', v_syl2, 2),
    (v_course2, 'T03', 'Arrays, linked lists, stacks and queues', v_syl2, 3),
    (v_course2, 'T04', 'Sorting algorithms: insertion, merge and quick sort', v_syl2, 4),
    (v_course2, 'T05', 'Binary heaps and priority queues; heap sort', v_syl2, 5),
    (v_course2, 'T06', 'Binary search trees and balanced trees (AVL)', v_syl2, 6),
    (v_course2, 'T07', 'Hash tables, hash functions, collision resolution', v_syl2, 7),
    (v_course2, 'T08', 'Graph representations; breadth-first and depth-first search', v_syl2, 8),
    (v_course2, 'T09', 'Introduction to shortest paths: Dijkstra''s algorithm', v_syl2, 9),
    (v_course2, 'T10', 'Introduction to minimum spanning trees: Prim''s algorithm', v_syl2, 10);

  RETURN v_course;
END $$;
