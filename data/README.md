# Seed dataset v1.1 — AI Build Hackathon (AUST CSE Carnival 8.0)

63 tables, one JSON file per table. All foreign keys validated. Seed course: **CSE 3103 Database Management Systems**.
`_all_tables_bundle.json` is everything in one file. `student_marks_wide.csv` is the spreadsheet-shaped marks.

## Four journeys, each with input → AI reasoning → useful result

| # | Journey | Faculty gives | System returns |
|---|---|---|---|
| J1 | Assessment quality | Draft question paper PDF | Findings, duplicate evidence, accepted revisions with a version trail |
| J2 | Attainment + fairness | Marks for a past paper | CO/PO attainment, two-session trend, per-item difficulty and discrimination |
| J3 | Grading consistency | Rubric + double-marked scripts | Divergence diagnosis, resolution, and a **rubric amendment** |
| J4 | Curriculum design | New course proposal | Standards violations, computed overlap with existing courses, inferred prerequisites |

Pick one or two. J1 alone is a complete MVP. J4 is the problem statement's own opening example and is the one most teams will skip.

## 25 planted flaws
Full list in `_manifest.json → planted_flaws`, each mapped to the record that should catch it.
Nothing here is clean by accident — if a feature finds nothing, check that list first.

## Numbers your dashboard should reproduce
**Draft paper:** 58 marks vs 60 declared · quality 54/100 · CO coverage 18/6/14/10/5/**0** + 5 untagged · Bloom 48.3% lower (cap 40), 17.2% higher (floor 30) · 3 duplicate pairs (0.94, 0.87, 0.81)
**Attainment (Spring 2025):** CO1 100 · CO2 70 · CO3 80 · **CO4 40** · **CO5 40** · CO6 63.3 — CO4 and CO5 failed two sessions running, so the alert is systemic
**Item analysis:** Q1(a) p=0.857 D=0.100 (too easy, 5 wasted marks) · Q4 D=0.100 at Bloom L5 (ambiguous) · Q5 D=0.488 (best) · mean D 0.314
**Grading:** ANS-03 13 v 6, ANS-05 17 v 11 — both trace to criterion R3
**Curriculum:** proposal CSE 4109 overlaps CSE 4101 by 66.7% on 8 topics (limit 40%) · CSE 3103 undeclared prerequisite · CO4 unmapped to any PO · PO7 covered by no course

## Table groups
- **Reference** departments, programs, program_outcomes, bloom_levels, faculty, policy, rule_catalog, accreditation_standards
- **Curriculum** curriculum_courses, course_proposals, curriculum_overlap, prerequisite_edges, proposal_findings, po_course_coverage
- **Course** courses, course_offerings, course_outcomes, co_po_map, syllabus_topics, assessment_plan
- **Papers** question_papers, questions, question_bank, paper_versions
- **Pipeline** extraction_runs, extracted_questions_raw, extraction_corrections, similarity_pairs, paper_analysis, findings, recommendations, recommendation_feedback
- **Attainment** students, student_marks, co_attainment, po_attainment, attainment_history, attainment_insights, item_analysis, item_analysis_summary
- **Grading** rubrics, rubric_criteria, rubric_amendments, exemplar_scripts, answer_scripts, grading_sessions, grader_scores, script_totals, grading_consistency, grading_divergences, divergence_resolutions, grader_profiles
- **Workflow** approval_workflow, review_threads, review_comments, notifications, faculty_preferences, file_assets
- **Ops** audit_log, llm_calls, api_quota, offline_cache, demo_script

## Demo
`demo_script.json` is a 10-beat, ~5-minute run sheet. Step 3 is the on-stage extraction edit — the single most important beat.
`offline_cache.json` is the fallback payload if the network dies. `api_quota.json` documents the quota guardrails.

## Regenerating
`build.py` then `extend.py`. Item difficulty and discrimination come from a per-question item-response model in `build.py → item_params`; overlap percentages are computed Jaccard over topic keyword sets, not typed in.
