#!/usr/bin/env python3
"""Seed-data generator for the AI Build Hackathon academic-quality system.
Emits one JSON file per table into ./data. All cross-references are ID-based.
Planted flaws are intentional: coverage gap (CO6), Bloom skew, 3 duplicate pairs,
marks-total mismatch, 1 untagged question, 3 extraction errors, weak CO4,
and 2 grader divergences.
"""
import json, os, random, statistics
from datetime import datetime, timedelta

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)
random.seed(20260906)

def dump(name, obj):
    p = os.path.join(OUT, name)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
    print(f"  {name:38s} {len(obj) if isinstance(obj, list) else 1:4d} rows")

# ---------------------------------------------------------------- reference
departments = [{
    "department_id": "DEPT-CSE",
    "code": "CSE",
    "name": "Department of Computer Science and Engineering",
    "university": "Ahsanullah University of Science and Technology",
    "accreditation_body": "BAETE",
    "obe_enabled": True
}]

bloom_levels = [
    {"bloom_id": "L1", "level": 1, "name": "Remember", "order_class": "lower",
     "verbs": ["define", "list", "state", "name", "recall", "identify"],
     "description": "Recall of facts and basic concepts."},
    {"bloom_id": "L2", "level": 2, "name": "Understand", "order_class": "lower",
     "verbs": ["explain", "describe", "compare", "distinguish", "summarize", "interpret"],
     "description": "Explain ideas or concepts."},
    {"bloom_id": "L3", "level": 3, "name": "Apply", "order_class": "middle",
     "verbs": ["apply", "compute", "write", "draw", "construct", "solve", "demonstrate"],
     "description": "Use information in new situations."},
    {"bloom_id": "L4", "level": 4, "name": "Analyze", "order_class": "higher",
     "verbs": ["analyze", "differentiate", "determine", "examine", "decompose", "diagnose"],
     "description": "Draw connections among ideas."},
    {"bloom_id": "L5", "level": 5, "name": "Evaluate", "order_class": "higher",
     "verbs": ["evaluate", "justify", "critique", "assess", "recommend", "defend"],
     "description": "Justify a stand or decision."},
    {"bloom_id": "L6", "level": 6, "name": "Create", "order_class": "higher",
     "verbs": ["design", "formulate", "propose", "develop", "compose"],
     "description": "Produce new or original work."},
]

program_outcomes = [
    ("PO1", "Engineering Knowledge", "Apply knowledge of mathematics, science and engineering fundamentals to the solution of complex engineering problems."),
    ("PO2", "Problem Analysis", "Identify, formulate, research literature and analyse complex engineering problems reaching substantiated conclusions."),
    ("PO3", "Design/Development of Solutions", "Design solutions for complex engineering problems and design systems, components or processes that meet specified needs."),
    ("PO4", "Investigation", "Conduct investigations of complex problems using research-based knowledge and research methods."),
    ("PO5", "Modern Tool Usage", "Create, select and apply appropriate techniques, resources and modern engineering and IT tools."),
    ("PO6", "The Engineer and Society", "Apply reasoning informed by contextual knowledge to assess societal, health, safety, legal and cultural issues."),
    ("PO7", "Environment and Sustainability", "Understand and evaluate the sustainability and impact of professional engineering work."),
    ("PO8", "Ethics", "Apply ethical principles and commit to professional ethics and responsibilities."),
    ("PO9", "Individual Work and Teamwork", "Function effectively as an individual, and as a member or leader in diverse teams."),
    ("PO10", "Communication", "Communicate effectively on complex engineering activities with the engineering community and society at large."),
    ("PO11", "Project Management and Finance", "Demonstrate knowledge and understanding of engineering management principles and economic decision-making."),
    ("PO12", "Life-long Learning", "Recognise the need for, and have the preparation and ability to engage in independent and life-long learning."),
]
program_outcomes = [{"po_id": p, "code": p, "title": t, "statement": s,
                     "program_id": "PROG-BSC-CSE"} for p, t, s in program_outcomes]

programs = [{
    "program_id": "PROG-BSC-CSE",
    "department_id": "DEPT-CSE",
    "name": "B.Sc. in Computer Science and Engineering",
    "duration_years": 4,
    "total_credits": 160.0,
    "po_count": 12
}]

# ---------------------------------------------------------------- faculty
faculty = [
    {"faculty_id": "F-001", "full_name": "Dr. Rezwana Karim", "short_name": "RK",
     "designation": "Professor", "email": "rezwana.cse@aust.edu", "department_id": "DEPT-CSE",
     "role": "course_coordinator", "is_active": True, "joined_on": "2009-03-01"},
    {"faculty_id": "F-002", "full_name": "Dr. Nusrat Jahan", "short_name": "NJ",
     "designation": "Associate Professor", "email": "nusrat.cse@aust.edu", "department_id": "DEPT-CSE",
     "role": "examiner", "is_active": True, "joined_on": "2013-08-15"},
    {"faculty_id": "F-003", "full_name": "Md. Tanvir Hasan", "short_name": "TH",
     "designation": "Assistant Professor", "email": "tanvir.cse@aust.edu", "department_id": "DEPT-CSE",
     "role": "examiner", "is_active": True, "joined_on": "2017-01-10"},
    {"faculty_id": "F-004", "full_name": "Sadia Afrin", "short_name": "SA",
     "designation": "Lecturer", "email": "sadia.cse@aust.edu", "department_id": "DEPT-CSE",
     "role": "course_teacher", "is_active": True, "joined_on": "2022-09-01"},
    {"faculty_id": "F-005", "full_name": "Dr. Kamrul Islam", "short_name": "KI",
     "designation": "Professor", "email": "kamrul.cse@aust.edu", "department_id": "DEPT-CSE",
     "role": "obe_committee_chair", "is_active": True, "joined_on": "2005-06-20"},
]

# ---------------------------------------------------------------- course
courses = [
    {"course_id": "C-CSE3103", "code": "CSE 3103", "title": "Database Management Systems",
     "credit_hours": 3.0, "contact_hours_per_week": 3, "level": 3, "term": 1,
     "program_id": "PROG-BSC-CSE", "department_id": "DEPT-CSE",
     "course_type": "theory", "prerequisite_codes": ["CSE 2103"],
     "coordinator_id": "F-001", "is_seed_course": True,
     "catalog_description": "Database concepts and architecture; ER modelling; relational model and algebra; SQL; functional dependency and normalisation; transaction management, concurrency control and recovery; indexing and query optimisation."},
    {"course_id": "C-CSE3104", "code": "CSE 3104", "title": "Database Management Systems Lab",
     "credit_hours": 1.5, "contact_hours_per_week": 3, "level": 3, "term": 1,
     "program_id": "PROG-BSC-CSE", "department_id": "DEPT-CSE",
     "course_type": "lab", "prerequisite_codes": [], "coordinator_id": "F-004",
     "is_seed_course": False,
     "catalog_description": "Laboratory work based on CSE 3103."},
    {"course_id": "C-CSE4101", "code": "CSE 4101", "title": "Advanced Database Systems",
     "credit_hours": 3.0, "contact_hours_per_week": 3, "level": 4, "term": 1,
     "program_id": "PROG-BSC-CSE", "department_id": "DEPT-CSE",
     "course_type": "theory", "prerequisite_codes": ["CSE 3103"], "coordinator_id": "F-005",
     "is_seed_course": False,
     "catalog_description": "Distributed databases, NoSQL stores, data warehousing, advanced query optimisation."},
]

course_offerings = [
    {"offering_id": "OFF-2024-SP", "course_id": "C-CSE3103", "session": "Spring 2024",
     "academic_year": "2023-24", "section": "A", "teacher_id": "F-002", "enrolled_count": 30},
    {"offering_id": "OFF-2025-SP", "course_id": "C-CSE3103", "session": "Spring 2025",
     "academic_year": "2024-25", "section": "A", "teacher_id": "F-002", "enrolled_count": 30},
    {"offering_id": "OFF-2026-SP", "course_id": "C-CSE3103", "session": "Spring 2026",
     "academic_year": "2025-26", "section": "A", "teacher_id": "F-004", "enrolled_count": 30},
]

# ---------------------------------------------------------------- COs
course_outcomes = [
    {"co_id": "CO1", "course_id": "C-CSE3103", "code": "CO1", "sequence": 1,
     "statement": "Explain fundamental database concepts, DBMS architecture and the major data models.",
     "target_bloom_id": "L2", "weight_percent": 15, "delivery_weeks": [1, 2, 3]},
    {"co_id": "CO2", "course_id": "C-CSE3103", "code": "CO2", "sequence": 2,
     "statement": "Design entity-relationship models for a given requirement and translate them into relational schemas.",
     "target_bloom_id": "L3", "weight_percent": 20, "delivery_weeks": [4, 5, 6]},
    {"co_id": "CO3", "course_id": "C-CSE3103", "code": "CO3", "sequence": 3,
     "statement": "Formulate SQL statements involving joins, nested subqueries and aggregate functions to retrieve required information.",
     "target_bloom_id": "L3", "weight_percent": 20, "delivery_weeks": [7, 8]},
    {"co_id": "CO4", "course_id": "C-CSE3103", "code": "CO4", "sequence": 4,
     "statement": "Analyse functional dependencies of a relation and normalise it up to BCNF.",
     "target_bloom_id": "L4", "weight_percent": 20, "delivery_weeks": [9, 10]},
    {"co_id": "CO5", "course_id": "C-CSE3103", "code": "CO5", "sequence": 5,
     "statement": "Evaluate transaction management, concurrency-control and recovery techniques for a given workload.",
     "target_bloom_id": "L5", "weight_percent": 15, "delivery_weeks": [11, 12]},
    {"co_id": "CO6", "course_id": "C-CSE3103", "code": "CO6", "sequence": 6,
     "statement": "Assess indexing and query-optimisation strategies and recommend an appropriate plan for a given query.",
     "target_bloom_id": "L5", "weight_percent": 10, "delivery_weeks": [13, 14]},
]

co_po_map = [
    ("CO1", "PO1", 3), ("CO1", "PO12", 1),
    ("CO2", "PO3", 3), ("CO2", "PO1", 1),
    ("CO3", "PO1", 2), ("CO3", "PO3", 2), ("CO3", "PO5", 1),
    ("CO4", "PO2", 3), ("CO4", "PO1", 1),
    ("CO5", "PO2", 2), ("CO5", "PO1", 1),
    ("CO6", "PO4", 2), ("CO6", "PO2", 1), ("CO6", "PO5", 1),
]
co_po_map = [{"map_id": f"MAP-{i+1:03d}", "co_id": c, "po_id": p, "strength": s,
              "strength_label": {1: "Low", 2: "Medium", 3: "High"}[s]}
             for i, (c, p, s) in enumerate(co_po_map)]

syllabus_topics = [
    ("T-01", 1, "Introduction to database systems, file system vs DBMS", "CO1", 3),
    ("T-02", 2, "Three-schema architecture, data independence, DBMS components", "CO1", 3),
    ("T-03", 3, "Data models: hierarchical, network, relational, object-relational", "CO1", 3),
    ("T-04", 4, "Entity-relationship model: entities, attributes, relationships, cardinality", "CO2", 3),
    ("T-05", 5, "Enhanced ER: specialisation, generalisation, aggregation", "CO2", 3),
    ("T-06", 6, "ER-to-relational mapping, integrity constraints", "CO2", 3),
    ("T-07", 7, "Relational algebra; SQL DDL and DML; joins", "CO3", 3),
    ("T-08", 8, "Nested subqueries, aggregate functions, GROUP BY, HAVING, views", "CO3", 3),
    ("T-09", 9, "Functional dependencies, closure, candidate keys, 1NF-2NF-3NF", "CO4", 3),
    ("T-10", 10, "BCNF, lossless-join and dependency-preserving decomposition", "CO4", 3),
    ("T-11", 11, "Transactions, ACID properties, schedules, serialisability", "CO5", 3),
    ("T-12", 12, "Concurrency control: two-phase locking, timestamp ordering, deadlock", "CO5", 3),
    ("T-13", 13, "Recovery: logging, checkpointing, ARIES overview", "CO5", 3),
    ("T-14", 14, "Indexing: B+ tree, hashing; query processing and optimisation", "CO6", 3),
]
syllabus_topics = [{"topic_id": t, "course_id": "C-CSE3103", "week": w, "title": ti,
                    "co_id": co, "contact_hours": h, "is_covered_in_draft_paper": None}
                   for t, w, ti, co, h in syllabus_topics]

assessment_plan = [
    {"plan_id": "AP-01", "course_id": "C-CSE3103", "component": "Class Test", "weight_percent": 20,
     "co_ids": ["CO1", "CO2"], "count": 3},
    {"plan_id": "AP-02", "course_id": "C-CSE3103", "component": "Mid Term", "weight_percent": 20,
     "co_ids": ["CO1", "CO2", "CO3"], "count": 1},
    {"plan_id": "AP-03", "course_id": "C-CSE3103", "component": "Attendance", "weight_percent": 10,
     "co_ids": [], "count": 1},
    {"plan_id": "AP-04", "course_id": "C-CSE3103", "component": "Final Examination", "weight_percent": 50,
     "co_ids": ["CO1", "CO2", "CO3", "CO4", "CO5", "CO6"], "count": 1},
]

# ---------------------------------------------------------------- policy
policy = {
    "policy_id": "POL-AUST-CSE-01",
    "department_id": "DEPT-CSE",
    "effective_from": "2024-01-01",
    "co_attainment": {
        "student_pass_percent": 60,
        "class_attainment_percent": 60,
        "levels": [{"level": 3, "min_percent": 70}, {"level": 2, "min_percent": 60},
                   {"level": 1, "min_percent": 50}, {"level": 0, "min_percent": 0}]
    },
    "paper_rules": {
        "max_lower_order_percent": 40,
        "min_higher_order_percent": 30,
        "min_marks_per_co_percent": 8,
        "max_marks_per_co_percent": 30,
        "require_all_cos_assessed": True,
        "max_intra_paper_similarity": 0.75,
        "max_cross_paper_similarity": 0.80,
        "cross_paper_lookback_years": 3,
        "allow_untagged_questions": False,
        "marks_total_tolerance": 0
    },
    "grading_rules": {
        "double_marking_enabled": True,
        "divergence_flag_percent_of_total": 20,
        "divergence_flag_absolute_marks": 4,
        "resolution": "third_examiner"
    }
}

# ---------------------------------------------------------------- papers
question_papers = [
    {"paper_id": "QP-2024-MID-01", "course_id": "C-CSE3103", "offering_id": "OFF-2024-SP",
     "title": "Mid Term Examination, Spring 2024", "exam_type": "midterm",
     "session": "Spring 2024", "exam_date": "2024-03-18", "duration_minutes": 90,
     "declared_total_marks": 30, "status": "archived", "setter_id": "F-002",
     "source_file": "CSE3103_Mid_Spring2024.pdf", "is_draft": False},
    {"paper_id": "QP-2025-FIN-01", "course_id": "C-CSE3103", "offering_id": "OFF-2025-SP",
     "title": "Final Examination, Spring 2025", "exam_type": "final",
     "session": "Spring 2025", "exam_date": "2025-06-02", "duration_minutes": 180,
     "declared_total_marks": 60, "status": "archived", "setter_id": "F-002",
     "source_file": "CSE3103_Final_Spring2025.pdf", "is_draft": False},
    {"paper_id": "QP-2026-DRAFT-01", "course_id": "C-CSE3103", "offering_id": "OFF-2026-SP",
     "title": "Final Examination, Spring 2026 (DRAFT)", "exam_type": "final",
     "session": "Spring 2026", "exam_date": "2026-06-08", "duration_minutes": 180,
     "declared_total_marks": 60, "status": "under_review", "setter_id": "F-004",
     "source_file": "CSE3103_Final_Spring2026_DRAFT.pdf", "is_draft": True,
     "uploaded_at": "2026-09-06T09:12:44+06:00", "computed_total_marks": 58,
     "note": "Seed draft. Flaws are intentional: CO6 uncovered, Bloom skew, 3 duplicate pairs, 1 untagged question, total mismatch 58 vs 60."},
]

Q = lambda qid, paper, num, part, text, marks, co, bloom, topic, opt=False, parent=None: {
    "question_id": qid, "paper_id": paper, "question_number": num, "part_label": part,
    "display_label": f"{num}{'('+part+')' if part else ''}",
    "text": text, "marks": marks, "co_id": co, "bloom_id": bloom, "topic_id": topic,
    "is_optional": opt, "parent_question_id": parent}

questions = [
    # ---- 2024 Mid
    Q("Q-2024M-1A", "QP-2024-MID-01", 1, "a",
      "Distinguish between physical data independence and logical data independence with a suitable example for each.", 5, "CO1", "L2", "T-02"),
    Q("Q-2024M-1B", "QP-2024-MID-01", 1, "b",
      "Explain the three-schema architecture of a DBMS and state the purpose of each level.", 5, "CO1", "L2", "T-02"),
    Q("Q-2024M-2A", "QP-2024-MID-01", 2, "a",
      "Draw an ER diagram for a hospital management system containing at least four entities. Clearly show the cardinality of every relationship.", 8, "CO2", "L3", "T-04"),
    Q("Q-2024M-2B", "QP-2024-MID-01", 2, "b",
      "Convert the ER diagram of question 2(a) into an equivalent set of relational schemas, indicating primary and foreign keys.", 5, "CO2", "L3", "T-06"),
    Q("Q-2024M-3A", "QP-2024-MID-01", 3, "a",
      "Write an SQL query to list the names of the employees who earn more than the average salary of their own department.", 7, "CO3", "L3", "T-08"),
    # ---- 2025 Final
    Q("Q-2025F-1A", "QP-2025-FIN-01", 1, "a",
      "Compare the hierarchical, network and relational data models in terms of structure, flexibility and query capability.", 5, "CO1", "L2", "T-03"),
    Q("Q-2025F-1B", "QP-2025-FIN-01", 1, "b",
      "Write an SQL query using GROUP BY and HAVING to find the departments that employ more than five employees, showing the department name and the head count.", 5, "CO3", "L3", "T-08"),
    Q("Q-2025F-2", "QP-2025-FIN-01", 2, None,
      "Design an ER diagram for a university library system covering members, books, copies, loans and reservations, then map it to relational schemas.", 10, "CO2", "L3", "T-06"),
    Q("Q-2025F-3", "QP-2025-FIN-01", 3, None,
      "Given R(A, B, C, D, E) with F = {A->BC, CD->E, B->D, E->A}, determine all candidate keys and decompose R into BCNF. State whether your decomposition is lossless-join.", 10, "CO4", "L4", "T-10"),
    Q("Q-2025F-4", "QP-2025-FIN-01", 4, None,
      "Evaluate two-phase locking against timestamp-ordering concurrency control for a workload with frequent short read-only transactions. Justify which one you would recommend.", 10, "CO5", "L5", "T-12"),
    Q("Q-2025F-5", "QP-2025-FIN-01", 5, None,
      "A query joins a 2-million-row orders table with a 5000-row customers table and filters on order_date. Assess three candidate index strategies and recommend one, justifying your choice with the expected cost.", 10, "CO6", "L5", "T-14"),
    Q("Q-2025F-6", "QP-2025-FIN-01", 6, None,
      "Analyse the relation Enrollment(student_id, course_code, course_title, instructor, grade) for update, insertion and deletion anomalies. Identify the functional dependencies and normalise it to 3NF.", 10, "CO4", "L4", "T-09"),
    # ---- 2026 Draft  (flaws intentional)
    Q("Q-2026D-1A", "QP-2026-DRAFT-01", 1, "a",
      "Define data independence and explain its two types with appropriate examples.", 6, "CO1", "L2", "T-02"),
    Q("Q-2026D-1B", "QP-2026-DRAFT-01", 1, "b",
      "List and describe the main responsibilities of a database administrator.", 6, "CO1", "L1", "T-01"),
    Q("Q-2026D-2A", "QP-2026-DRAFT-01", 2, "a",
      "Draw an ER diagram for an online course-registration system showing entities, attributes and cardinalities.", 6, "CO2", "L3", "T-04"),
    Q("Q-2026D-2B", "QP-2026-DRAFT-01", 2, "b",
      "Write an SQL query to list the names of the employees whose salary exceeds the average salary of their own department.", 7, "CO3", "L3", "T-08"),
    Q("Q-2026D-3A", "QP-2026-DRAFT-01", 3, "a",
      "Explain physical versus logical data independence with a suitable example.", 6, "CO1", "L2", "T-02"),
    Q("Q-2026D-3B", "QP-2026-DRAFT-01", 3, "b",
      "Given R(A, B, C, D, E) with F = {AB->C, C->D, D->E}, find the candidate keys and normalise the relation up to 3NF.", 10, "CO4", "L4", "T-09"),
    Q("Q-2026D-4A", "QP-2026-DRAFT-01", 4, "a",
      "Write an SQL query using GROUP BY and HAVING to find the departments having more than five employees.", 7, "CO3", "L3", "T-08"),
    Q("Q-2026D-4B", "QP-2026-DRAFT-01", 4, "b",
      "Define a transaction and state the ACID properties of a transaction.", 5, "CO5", "L2", "T-11"),
    Q("Q-2026D-5", "QP-2026-DRAFT-01", 5, None,
      "Briefly explain the purpose of the database log file.", 5, None, "L2", None),
]

# ---------------------------------------------------------------- extraction
extraction_runs = [{
    "run_id": "EXT-RUN-001", "paper_id": "QP-2026-DRAFT-01",
    "source_file": "CSE3103_Final_Spring2026_DRAFT.pdf", "page_count": 2,
    "extractor": "pdfplumber+llm-structurer", "model": "claude-sonnet-4-6",
    "started_at": "2026-09-06T09:12:47+06:00", "finished_at": "2026-09-06T09:13:09+06:00",
    "duration_ms": 22140, "status": "needs_review",
    "questions_detected": 9, "questions_confirmed": 0,
    "low_confidence_count": 3, "mean_confidence": 0.81,
    "requires_human_confirmation": True
}]

# raw extraction: three deliberate errors for the confirm-table demo
raw = [
    ("EXR-001", "Q-2026D-1A", "1", "a", "Define data independence and explain its two types with appropriate examples.", 6, "CO1", "L2", 0.96, [], "clean"),
    ("EXR-002", "Q-2026D-1B", "1", "b", "List and describe the main responsibilities of a database administrator.", 6, "CO1", "L1", 0.94, [], "clean"),
    ("EXR-003", "Q-2026D-2A", "2", "a", "Draw an ER diagram for an online course-registration system showing entities, attributes and cardinalities.", 6, "CO2", "L3", 0.92, [], "clean"),
    ("EXR-004", "Q-2026D-2B", "2", "b", "Write an SQL query to list the names of the employees whose salary exceeds the average salary of their own department.", 7, "CO1", "L3", 0.55,
     ["co_tag_low_confidence"], "WRONG CO: model suggested CO1, correct is CO3 (SQL formulation)."),
    ("EXR-005", "Q-2026D-3A", "3", "a", "Explain physical versus logical data independence with a suitable example.", 6, "CO1", "L2", 0.93, [], "clean"),
    ("EXR-006", "Q-2026D-3B", "3", "b", "Given R(A, B, C, D, E) with F = {AB->C, C->D, D->E}, find the candidate keys and normalise the relation up to 3NF.", 1, "CO4", "L4", 0.42,
     ["marks_ocr_ambiguous"], "WRONG MARKS: '1O' read as 1, actual 10. This is the row faculty edits on stage."),
    ("EXR-007", "Q-2026D-4A", "4", "a", "Write an SQL query using GROUP BY and HAVING to find the departments having more than five employees. (b) Define a transaction and state the ACID properties of a transaction.", 12, "CO3", "L3", 0.51,
     ["parts_merged"], "MERGED PARTS: 4(a) and 4(b) captured as one row with combined marks."),
    ("EXR-008", "Q-2026D-5", "5", None, "Briefly explain the purpose of the database log file.", 5, None, "L2", 0.88,
     ["no_co_tag"], "UNTAGGED: no CO could be inferred with confidence."),
]
extracted_questions_raw = [{
    "raw_id": r[0], "run_id": "EXT-RUN-001", "maps_to_question_id": r[1],
    "detected_number": r[2], "detected_part": r[3], "extracted_text": r[4],
    "extracted_marks": r[5], "suggested_co_id": r[6], "suggested_bloom_id": r[7],
    "confidence": r[8], "flags": r[9], "review_note": r[10],
    "is_confirmed": False, "corrected_by": None, "corrected_at": None
} for r in raw]

extraction_corrections = [
    {"correction_id": "COR-001", "raw_id": "EXR-006", "run_id": "EXT-RUN-001",
     "field": "marks", "old_value": 1, "new_value": 10,
     "corrected_by": "F-004", "corrected_at": "2026-09-06T09:15:02+06:00",
     "reason": "OCR misread '10' as '1'.", "is_demo_scripted": True},
    {"correction_id": "COR-002", "raw_id": "EXR-004", "run_id": "EXT-RUN-001",
     "field": "co_id", "old_value": "CO1", "new_value": "CO3",
     "corrected_by": "F-004", "corrected_at": "2026-09-06T09:15:31+06:00",
     "reason": "Question asks for SQL formulation, which maps to CO3.", "is_demo_scripted": True},
    {"correction_id": "COR-003", "raw_id": "EXR-007", "run_id": "EXT-RUN-001",
     "field": "split", "old_value": "4(a)+4(b) merged, 12 marks",
     "new_value": "4(a) 7 marks CO3 L3 | 4(b) 5 marks CO5 L2",
     "corrected_by": "F-004", "corrected_at": "2026-09-06T09:16:10+06:00",
     "reason": "Two separate parts merged during extraction.", "is_demo_scripted": True},
]

# ---------------------------------------------------------------- similarity
similarity_pairs = [
    {"pair_id": "SIM-001", "source_question_id": "Q-2026D-2B", "target_question_id": "Q-2024M-3A",
     "source_paper_id": "QP-2026-DRAFT-01", "target_paper_id": "QP-2024-MID-01",
     "scope": "cross_paper", "similarity": 0.94, "method": "embedding_cosine+llm_verify",
     "verdict": "near_duplicate", "severity": "high",
     "rationale": "Identical task: retrieve employees earning above their own department average. Only surface wording differs ('earn more than' vs 'salary exceeds').",
     "recommendation": "Replace, or raise difficulty by requiring the department name and a correlated subquery with a HAVING clause."},
    {"pair_id": "SIM-002", "source_question_id": "Q-2026D-4A", "target_question_id": "Q-2025F-1B",
     "source_paper_id": "QP-2026-DRAFT-01", "target_paper_id": "QP-2025-FIN-01",
     "scope": "cross_paper", "similarity": 0.87, "method": "embedding_cosine+llm_verify",
     "verdict": "near_duplicate", "severity": "high",
     "rationale": "Same GROUP BY / HAVING pattern over the same threshold of five employees; appeared in the immediately previous final.",
     "recommendation": "Change the aggregate and the grouping attribute, or ask the student to justify why HAVING cannot be replaced by WHERE."},
    {"pair_id": "SIM-003", "source_question_id": "Q-2026D-3A", "target_question_id": "Q-2026D-1A",
     "source_paper_id": "QP-2026-DRAFT-01", "target_paper_id": "QP-2026-DRAFT-01",
     "scope": "intra_paper", "similarity": 0.81, "method": "embedding_cosine+llm_verify",
     "verdict": "redundant_within_paper", "severity": "high",
     "rationale": "Both questions assess the same concept (physical vs logical data independence) under CO1; 12 of 58 marks are spent twice on one topic.",
     "recommendation": "Drop 3(a) and reallocate 6 marks to CO6, which is currently unassessed."},
    {"pair_id": "SIM-004", "source_question_id": "Q-2026D-1A", "target_question_id": "Q-2024M-1A",
     "source_paper_id": "QP-2026-DRAFT-01", "target_paper_id": "QP-2024-MID-01",
     "scope": "cross_paper", "similarity": 0.79, "method": "embedding_cosine+llm_verify",
     "verdict": "borderline", "severity": "medium",
     "rationale": "Same concept as the 2024 midterm question but phrased as a definition task rather than a comparison.",
     "recommendation": "Acceptable if retained, but consider raising to Bloom L3 by asking for a scenario-based judgement."},
    {"pair_id": "SIM-005", "source_question_id": "Q-2026D-3B", "target_question_id": "Q-2025F-3",
     "source_paper_id": "QP-2026-DRAFT-01", "target_paper_id": "QP-2025-FIN-01",
     "scope": "cross_paper", "similarity": 0.68, "method": "embedding_cosine+llm_verify",
     "verdict": "acceptable", "severity": "low",
     "rationale": "Same normalisation skill but a different dependency set and a lower target normal form (3NF vs BCNF).",
     "recommendation": "No action required."},
]

# ---------------------------------------------------------------- coverage analysis (computed)
draft_qs = [q for q in questions if q["paper_id"] == "QP-2026-DRAFT-01"]
draft_total = sum(q["marks"] for q in draft_qs)

co_cov = []
for co in course_outcomes:
    m = sum(q["marks"] for q in draft_qs if q["co_id"] == co["co_id"])
    pct = round(m / draft_total * 100, 1)
    target = co["weight_percent"]
    if m == 0:
        status, sev = "not_assessed", "critical"
    elif pct < policy["paper_rules"]["min_marks_per_co_percent"]:
        status, sev = "under_weighted", "high"
    elif pct < target * 0.7:
        status, sev = "under_weighted", "high"
    elif pct > target * 1.5:
        status, sev = "over_weighted", "medium"
    else:
        status, sev = "balanced", "none"
    co_cov.append({"co_id": co["co_id"], "marks": m, "percent_of_paper": pct,
                   "target_percent": target, "deviation": round(pct - target, 1),
                   "question_ids": [q["question_id"] for q in draft_qs if q["co_id"] == co["co_id"]],
                   "status": status, "severity": sev})
untagged_marks = sum(q["marks"] for q in draft_qs if q["co_id"] is None)

bl_cov = []
for b in bloom_levels:
    m = sum(q["marks"] for q in draft_qs if q["bloom_id"] == b["bloom_id"])
    bl_cov.append({"bloom_id": b["bloom_id"], "name": b["name"], "order_class": b["order_class"],
                   "marks": m, "percent_of_paper": round(m / draft_total * 100, 1),
                   "question_ids": [q["question_id"] for q in draft_qs if q["bloom_id"] == b["bloom_id"]]})
lower = sum(x["marks"] for x in bl_cov if x["order_class"] == "lower")
higher = sum(x["marks"] for x in bl_cov if x["order_class"] == "higher")
middle = draft_total - lower - higher

topic_cov = []
covered_topics = {q["topic_id"] for q in draft_qs if q["topic_id"]}
for t in syllabus_topics:
    t["is_covered_in_draft_paper"] = t["topic_id"] in covered_topics
    topic_cov.append({"topic_id": t["topic_id"], "week": t["week"], "title": t["title"],
                      "co_id": t["co_id"], "covered": t["topic_id"] in covered_topics,
                      "marks": sum(q["marks"] for q in draft_qs if q["topic_id"] == t["topic_id"])})

paper_analysis = [{
    "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01", "run_id": "EXT-RUN-001",
    "generated_at": "2026-09-06T09:17:22+06:00", "policy_id": "POL-AUST-CSE-01",
    "model": "claude-sonnet-4-6", "engine_version": "1.0.0",
    "declared_total_marks": 60, "computed_total_marks": draft_total,
    "marks_mismatch": 60 - draft_total,
    "question_count": len(draft_qs),
    "quality_score": 54, "quality_band": "needs_revision",
    "sub_scores": {"co_coverage": 48, "bloom_balance": 45, "originality": 52,
                   "structural_integrity": 62, "tagging_completeness": 66},
    "co_coverage": co_cov,
    "untagged_marks": untagged_marks,
    "bloom_distribution": bl_cov,
    "bloom_summary": {
        "lower_order_marks": lower, "lower_order_percent": round(lower / draft_total * 100, 1),
        "middle_order_marks": middle, "middle_order_percent": round(middle / draft_total * 100, 1),
        "higher_order_marks": higher, "higher_order_percent": round(higher / draft_total * 100, 1),
        "policy_max_lower_percent": 40, "policy_min_higher_percent": 30,
        "lower_order_violation": round(lower / draft_total * 100, 1) > 40,
        "higher_order_violation": round(higher / draft_total * 100, 1) < 30},
    "topic_coverage": topic_cov,
    "duplicate_pair_ids": ["SIM-001", "SIM-002", "SIM-003", "SIM-004"],
    "uncovered_topic_ids": [t["topic_id"] for t in topic_cov if not t["covered"]],
}]

findings = [
    {"finding_id": "FND-001", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "co_coverage", "severity": "critical", "rule_id": "R-CO-NOT-ASSESSED",
     "title": "CO6 is not assessed anywhere in the paper",
     "detail": "CO6 (assess indexing and query-optimisation strategies) carries 10% of the course weight but receives 0 of 58 marks. Weeks 13-14 of the syllabus are therefore untested.",
     "evidence_question_ids": [], "evidence_topic_ids": ["T-14"],
     "suggested_action": "Add a 6-8 mark question on index selection or query-plan comparison; take the marks from the redundant question 3(a)."},
    {"finding_id": "FND-002", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "bloom_balance", "severity": "high", "rule_id": "R-BLOOM-LOWER-EXCESS",
     "title": f"Lower-order questions occupy {round(lower/draft_total*100,1)}% of marks (policy limit 40%)",
     "detail": f"Remember and Understand levels account for {lower} of {draft_total} marks, while Analyze/Evaluate/Create account for only {higher} marks ({round(higher/draft_total*100,1)}%, policy minimum 30%).",
     "evidence_question_ids": ["Q-2026D-1B", "Q-2026D-4B", "Q-2026D-5", "Q-2026D-1A", "Q-2026D-3A"],
     "evidence_topic_ids": [],
     "suggested_action": "Convert 4(b) from a definition of ACID into an evaluation of an interleaved schedule, and add a CO6 evaluation question."},
    {"finding_id": "FND-003", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "originality", "severity": "high", "rule_id": "R-DUP-CROSS-PAPER",
     "title": "Question 2(b) is a near duplicate of Mid Term Spring 2024, question 3(a)",
     "detail": "Similarity 0.94. The same correlated-subquery task appeared two years ago and is likely to be circulating in student question banks.",
     "evidence_question_ids": ["Q-2026D-2B", "Q-2024M-3A"], "evidence_topic_ids": [],
     "suggested_action": "Rewrite with a different aggregate and an added ordering or window requirement."},
    {"finding_id": "FND-004", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "originality", "severity": "high", "rule_id": "R-DUP-CROSS-PAPER",
     "title": "Question 4(a) repeats Final Spring 2025, question 1(b)",
     "detail": "Similarity 0.87, and the source paper is only one year old, which is inside the three-year lookback window.",
     "evidence_question_ids": ["Q-2026D-4A", "Q-2025F-1B"], "evidence_topic_ids": [],
     "suggested_action": "Replace the HAVING threshold task with a multi-table aggregate over a different schema."},
    {"finding_id": "FND-005", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "redundancy", "severity": "high", "rule_id": "R-DUP-INTRA-PAPER",
     "title": "Questions 1(a) and 3(a) assess the same concept twice",
     "detail": "Similarity 0.81 within the same paper. 12 of 58 marks are spent on data independence, while CO6 receives none.",
     "evidence_question_ids": ["Q-2026D-1A", "Q-2026D-3A"], "evidence_topic_ids": ["T-02"],
     "suggested_action": "Remove 3(a) and reallocate its 6 marks to CO6."},
    {"finding_id": "FND-006", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "structural", "severity": "medium", "rule_id": "R-MARKS-TOTAL-MISMATCH",
     "title": f"Marks do not add up: header declares 60, questions total {draft_total}",
     "detail": f"A shortfall of {60-draft_total} marks. Either the header is wrong or a question has been dropped during editing.",
     "evidence_question_ids": [], "evidence_topic_ids": [],
     "suggested_action": "Reconcile the header total after the CO6 question is added."},
    {"finding_id": "FND-007", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "tagging", "severity": "medium", "rule_id": "R-UNTAGGED-QUESTION",
     "title": "Question 5 carries no course-outcome tag",
     "detail": "5 marks cannot be attributed to any CO, so they will be excluded from the attainment calculation and the OBE report will not reconcile.",
     "evidence_question_ids": ["Q-2026D-5"], "evidence_topic_ids": [],
     "suggested_action": "Tag to CO5 (recovery and logging, week 13) or rewrite to target CO6."},
    {"finding_id": "FND-008", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "co_coverage", "severity": "high", "rule_id": "R-CO-UNDERWEIGHT",
     "title": "CO5 is assessed at 8.6% against a course weight of 15%",
     "detail": "The only CO5 question, 4(b), is a 5-mark recall item at Bloom L2 whereas CO5 targets L5 (Evaluate). The CO is nominally covered but not at the intended cognitive level.",
     "evidence_question_ids": ["Q-2026D-4B"], "evidence_topic_ids": ["T-11", "T-12", "T-13"],
     "suggested_action": "Raise 4(b) to an evaluation of a concurrency-control scenario and increase it to 8-10 marks."},
    {"finding_id": "FND-009", "analysis_id": "AN-001", "paper_id": "QP-2026-DRAFT-01",
     "category": "co_coverage", "severity": "medium", "rule_id": "R-CO-OVERWEIGHT",
     "title": "CO1 receives 31% of the paper against a course weight of 15%",
     "detail": "Three questions target CO1, two of which overlap in content.",
     "evidence_question_ids": ["Q-2026D-1A", "Q-2026D-1B", "Q-2026D-3A"], "evidence_topic_ids": [],
     "suggested_action": "Reduce CO1 to roughly 9-12 marks."},
]

recommendations = [
    {"recommendation_id": "REC-001", "analysis_id": "AN-001", "type": "replace_question",
     "target_question_id": "Q-2026D-3A", "priority": 1, "expected_quality_gain": 14,
     "addresses_finding_ids": ["FND-001", "FND-005"],
     "proposed_text": "A frequently executed report joins orders (2.4 million rows) with customers (5,200 rows) and filters on order_date within the last 30 days. Assess a composite index on (order_date, customer_id), a covering index and a partial index. Recommend one and justify your recommendation in terms of selectivity and maintenance cost.",
     "proposed_marks": 6, "proposed_co_id": "CO6", "proposed_bloom_id": "L5",
     "status": "pending", "accepted_by": None},
    {"recommendation_id": "REC-002", "analysis_id": "AN-001", "type": "rewrite_question",
     "target_question_id": "Q-2026D-2B", "priority": 2, "expected_quality_gain": 9,
     "addresses_finding_ids": ["FND-003"],
     "proposed_text": "For each department, list the department name together with the number of employees whose salary is above the median salary of that department. Order the result by that count in descending order.",
     "proposed_marks": 7, "proposed_co_id": "CO3", "proposed_bloom_id": "L3",
     "status": "pending", "accepted_by": None},
    {"recommendation_id": "REC-003", "analysis_id": "AN-001", "type": "raise_bloom_level",
     "target_question_id": "Q-2026D-4B", "priority": 3, "expected_quality_gain": 8,
     "addresses_finding_ids": ["FND-002", "FND-008"],
     "proposed_text": "Given the interleaved schedule S below over transactions T1, T2 and T3, determine whether S is conflict serialisable. If it is not, evaluate whether strict two-phase locking or timestamp ordering would have prevented the anomaly, and justify which you would deploy for this workload.",
     "proposed_marks": 9, "proposed_co_id": "CO5", "proposed_bloom_id": "L5",
     "status": "pending", "accepted_by": None},
    {"recommendation_id": "REC-004", "analysis_id": "AN-001", "type": "tag_question",
     "target_question_id": "Q-2026D-5", "priority": 4, "expected_quality_gain": 4,
     "addresses_finding_ids": ["FND-007"],
     "proposed_text": None, "proposed_marks": 5, "proposed_co_id": "CO5", "proposed_bloom_id": "L2",
     "status": "pending", "accepted_by": None},
    {"recommendation_id": "REC-005", "analysis_id": "AN-001", "type": "rewrite_question",
     "target_question_id": "Q-2026D-4A", "priority": 5, "expected_quality_gain": 7,
     "addresses_finding_ids": ["FND-004"],
     "proposed_text": "Using the schema Sales(sale_id, branch_id, product_id, qty, sale_date), write a single SQL statement that returns the branches whose average monthly revenue in 2025 exceeded the overall company average, showing the branch name and the difference.",
     "proposed_marks": 7, "proposed_co_id": "CO3", "proposed_bloom_id": "L3",
     "status": "pending", "accepted_by": None},
]

# ---------------------------------------------------------------- students & marks
first = ["Arif", "Nabila", "Sabbir", "Tasnim", "Rakib", "Mehjabin", "Fahim", "Sumaiya", "Nayeem",
         "Ishrat", "Zahid", "Farhana", "Imran", "Nusaiba", "Shakib", "Anika", "Rifat", "Maliha",
         "Tahmid", "Rubaiya", "Sajid", "Nusrat", "Adnan", "Samiha", "Hasib", "Jarin", "Mahin",
         "Raisa", "Sifat", "Oishi"]
last = ["Hossain", "Rahman", "Ahmed", "Akter", "Islam", "Chowdhury", "Karim", "Sultana", "Uddin",
        "Jahan", "Hasan", "Begum", "Ali", "Noor", "Mahmud", "Tabassum", "Sarker", "Haque",
        "Rashid", "Ferdous", "Alam", "Khatun", "Bhuiyan", "Mim", "Reza", "Nahar", "Talukder",
        "Anjum", "Kabir", "Das"]
students = []
for i in range(30):
    sid = f"20{2}10{i+1:02d}"
    students.append({"student_id": f"S-{i+1:03d}", "roll": f"210105{i+1:03d}",
                     "name": f"{first[i]} {last[i]}", "program_id": "PROG-BSC-CSE",
                     "section": "A", "batch": "2021", "is_active": True})

# item response model: each question has its own difficulty (base) and its own
# discrimination loading on student ability. A low loading produces a question that
# everyone scores similarly on, i.e. a genuinely poor discriminator.
item_params = {
    "Q-2025F-1A": {"base": 0.860, "loading": 0.14},   # too easy, weak discriminator
    "Q-2025F-1B": {"base": 0.725, "loading": 0.62},
    "Q-2025F-2":  {"base": 0.700, "loading": 0.70},
    "Q-2025F-3":  {"base": 0.520, "loading": 0.60},   # CO4, hard
    "Q-2025F-4":  {"base": 0.572, "loading": 0.24},   # CO5, ambiguous -> poor discriminator
    "Q-2025F-5":  {"base": 0.660, "loading": 0.78},   # CO6, best discriminator
    "Q-2025F-6":  {"base": 0.498, "loading": 0.55},   # CO4, hard
}
final_qs = [q for q in questions if q["paper_id"] == "QP-2025-FIN-01"]

student_marks = []
mid = 1
for s in students:
    ability = min(1.9, max(-1.9, random.gauss(0.0, 1.0)))   # standardised ability
    for q in final_qs:
        pr = item_params[q["question_id"]]
        frac = pr["base"] + pr["loading"] * ability * 0.30 + random.gauss(0, 0.105)
        frac = min(1.0, max(0.0, frac))
        obtained = round(q["marks"] * frac * 2) / 2
        student_marks.append({
            "mark_id": f"MK-{mid:04d}", "student_id": s["student_id"],
            "paper_id": "QP-2025-FIN-01", "question_id": q["question_id"],
            "co_id": q["co_id"], "max_marks": q["marks"], "obtained_marks": obtained,
            "percent": round(obtained / q["marks"] * 100, 1),
            "evaluator_id": "F-002", "entered_at": "2025-06-14T11:20:00+06:00"})
        mid += 1

# ---------------------------------------------------------------- attainment (computed)
def co_stats(co_id):
    qs = [q for q in final_qs if q["co_id"] == co_id]
    qids = {q["question_id"] for q in qs}
    total = sum(q["marks"] for q in qs)
    per_student = {}
    for m in student_marks:
        if m["question_id"] in qids:
            per_student.setdefault(m["student_id"], 0.0)
            per_student[m["student_id"]] += m["obtained_marks"]
    pcts = [v / total * 100 for v in per_student.values()]
    attained = [p for p in pcts if p >= 60]
    return total, qids, pcts, len(attained)

co_attainment = []
for co in course_outcomes:
    total, qids, pcts, n_att = co_stats(co["co_id"])
    if total == 0:
        continue
    class_pct = round(n_att / len(students) * 100, 1)
    avg = round(statistics.mean(pcts), 1)
    lvl = 3 if class_pct >= 70 else 2 if class_pct >= 60 else 1 if class_pct >= 50 else 0
    co_attainment.append({
        "attainment_id": f"ATT-{co['co_id']}", "course_id": "C-CSE3103",
        "offering_id": "OFF-2025-SP", "paper_id": "QP-2025-FIN-01", "co_id": co["co_id"],
        "question_ids": sorted(qids), "max_marks": total,
        "students_evaluated": len(students), "students_attained": n_att,
        "class_attainment_percent": class_pct, "class_average_percent": avg,
        "median_percent": round(statistics.median(pcts), 1),
        "std_dev": round(statistics.pstdev(pcts), 1),
        "threshold_student_percent": 60, "threshold_class_percent": 60,
        "attainment_level": lvl,
        "status": "attained" if class_pct >= 60 else "not_attained",
        "severity": "none" if class_pct >= 60 else ("critical" if class_pct < 45 else "high"),
        "is_weak": class_pct < 60})

po_attainment = []
for po in program_outcomes:
    rows = [m for m in co_po_map if m["po_id"] == po["po_id"]]
    if not rows:
        continue
    num = den = 0.0
    contribs = []
    for r in rows:
        att = next((a for a in co_attainment if a["co_id"] == r["co_id"]), None)
        if not att:
            continue
        num += att["class_attainment_percent"] * r["strength"]
        den += 3 * r["strength"]
        contribs.append({"co_id": r["co_id"], "strength": r["strength"],
                         "co_attainment_percent": att["class_attainment_percent"]})
    if den == 0:
        continue
    val = round(num / (den / 3) / len(rows) if False else num / sum(3 * r["strength"] for r in rows) * 3, 1)
    po_attainment.append({
        "po_attainment_id": f"POATT-{po['po_id']}", "po_id": po["po_id"],
        "course_id": "C-CSE3103", "offering_id": "OFF-2025-SP",
        "contributing_cos": contribs,
        "weighted_attainment_percent": val,
        "threshold_percent": 60,
        "status": "attained" if val >= 60 else "not_attained",
        "is_weak": val < 60})

weak = [a for a in co_attainment if a["is_weak"]]
attainment_insights = [{
    "insight_id": "INS-001", "course_id": "C-CSE3103", "offering_id": "OFF-2025-SP",
    "generated_at": "2026-09-06T09:21:40+06:00", "model": "claude-sonnet-4-6",
    "headline": f"{len(weak)} of {len(co_attainment)} course outcomes fell below the 60% attainment threshold, led by CO4.",
    "weak_co_ids": [a["co_id"] for a in weak],
    "narrative": "CO4 (analysis of functional dependencies and normalisation) is the weakest outcome. Both CO4 questions, 3 and 6, sit at Bloom level 4 and carry 20 of 60 marks, yet fewer than half the class reached the 60% mark on them. Scores on question 3, which required candidate-key discovery before decomposition, were markedly lower than on question 6, which supplied the anomalies. This points to candidate-key determination rather than normalisation itself as the underlying gap.",
    "recommended_actions": [
        "Add a guided tutorial on attribute-closure and candidate-key computation before the normalisation lecture.",
        "Introduce a low-stakes class test on functional dependencies in week 9 to surface the gap earlier.",
        "In the next final, split the CO4 assessment into a 4-mark key-finding part and a 6-mark decomposition part so the failure point becomes visible.",
        "Carry CO4 forward as an action item into the CSE 4101 course file, since it is a prerequisite outcome."],
    "linked_finding_ids": ["FND-001", "FND-008"]
}]

# ---------------------------------------------------------------- rubric & grading
rubrics = [{
    "rubric_id": "RUB-001", "question_id": "Q-2025F-6", "paper_id": "QP-2025-FIN-01",
    "course_id": "C-CSE3103", "co_id": "CO4", "bloom_id": "L4", "total_marks": 20,
    "title": "Normalisation of Enrollment relation to 3NF",
    "created_by": "F-001", "created_at": "2025-05-28T16:00:00+06:00", "version": 2,
    "question_text": "Analyse the relation Enrollment(student_id, course_code, course_title, instructor, grade) for update, insertion and deletion anomalies. Identify the functional dependencies and normalise it to 3NF, justifying each decomposition step."
}]

rubric_criteria = [
    {"criterion_id": "RC-1", "rubric_id": "RUB-001", "code": "R1", "sequence": 1,
     "title": "Anomaly identification", "max_marks": 4,
     "descriptor": "All three anomaly types named and illustrated with a concrete tuple from the given relation.",
     "band_descriptors": {"4": "All three anomalies with correct concrete examples.",
                          "3": "All three named, examples partly correct.",
                          "2": "Two anomalies identified.",
                          "1": "One anomaly identified or examples missing.",
                          "0": "No anomaly correctly identified."}},
    {"criterion_id": "RC-2", "rubric_id": "RUB-001", "code": "R2", "sequence": 2,
     "title": "Functional dependency identification", "max_marks": 5,
     "descriptor": "Complete and minimal FD set derived from the semantics of the relation.",
     "band_descriptors": {"5": "Complete minimal FD set, no spurious dependencies.",
                          "4": "Complete set with one redundant FD.",
                          "3": "Main FDs present, one missing.",
                          "2": "Partial set, key dependency missing.",
                          "1": "Only trivial dependencies stated.",
                          "0": "No usable FD set."}},
    {"criterion_id": "RC-3", "rubric_id": "RUB-001", "code": "R3", "sequence": 3,
     "title": "Decomposition correctness", "max_marks": 6,
     "descriptor": "Resulting relations are in 3NF with correct primary and foreign keys.",
     "band_descriptors": {"6": "All resulting relations in 3NF, keys correct.",
                          "4-5": "Correct 3NF, minor key or naming error.",
                          "2-3": "Partial decomposition, one relation still violating 3NF.",
                          "1": "Decomposition attempted but incorrect.",
                          "0": "No decomposition."},
     "ambiguity_note": "The rubric does not state whether an alternative but equally valid decomposition earns full marks. This is the wording that caused divergence on ANS-05."},
    {"criterion_id": "RC-4", "rubric_id": "RUB-001", "code": "R4", "sequence": 4,
     "title": "Justification and lossless-join argument", "max_marks": 5,
     "descriptor": "Each step justified and the lossless-join property demonstrated.",
     "band_descriptors": {"5": "Every step justified plus a correct lossless-join argument.",
                          "3-4": "Steps justified, lossless-join asserted without proof.",
                          "1-2": "Minimal justification.",
                          "0": "No justification."},
     "ambiguity_note": "Does not say whether a correct final answer with no justification scores zero here or is compensated under R3."},
]

answer_scripts = [
    ("ANS-01", "S-004", "Tasnim Akter",
     "Update anomaly: if the title of CSE 3103 changes it must be edited in every row for that course. Insertion anomaly: a newly announced course with no enrolled student cannot be stored because student_id is part of the key. Deletion anomaly: removing the last enrolment for a course erases the course title and instructor. FDs: student_id, course_code -> grade; course_code -> course_title; course_code -> instructor. The relation is in 2NF but course_code -> course_title is a transitive dependency on a non-prime attribute, so it violates 3NF. Decomposition: Course(course_code, course_title, instructor) and Enrollment(student_id, course_code, grade) with course_code as a foreign key. The common attribute course_code is a key of Course, therefore the join is lossless, and both FDs are preserved."),
    ("ANS-02", "S-011", "Zahid Hasan",
     "There are update and deletion anomalies. If a course title changes we have to update many rows, and deleting a student may delete course information. FDs are course_code -> course_title and course_code -> instructor, and student_id with course_code gives grade. So we break it into two tables, one for courses and one for enrolments. This removes the repetition."),
    ("ANS-03", "S-017", "Rifat Sarker",
     "FDs: {student_id, course_code} -> grade; course_code -> course_title, instructor. Candidate key is {student_id, course_code}. Transitive dependency exists, so decompose: R1(course_code, course_title, instructor), R2(student_id, course_code, grade). Both are in 3NF."),
    ("ANS-04", "S-023", "Adnan Bhuiyan",
     "The table has redundancy because the course title repeats. Functional dependency means one attribute determines another. Here course_code determines course_title. We should make separate tables for course and student so that data is not repeated. Then it will be normalised."),
    ("ANS-05", "S-026", "Jarin Nahar",
     "Anomalies: update (title repeated per row), insertion (cannot record a course before anyone enrols), deletion (last enrolment removal loses the course). FDs: course_code -> course_title; course_code -> instructor; {student_id, course_code} -> grade. Rather than one course table I decompose into three: Course(course_code, course_title), Teaching(course_code, instructor) and Enrollment(student_id, course_code, grade). Every relation is in 3NF, all joins are lossless because course_code is a key in both Course and Teaching, and all dependencies are preserved. Splitting instructor out also allows the schema to be extended to multiple instructors per course later."),
    ("ANS-06", "S-029", "Sifat Kabir",
     "Normalisation removes redundancy from a table. 1NF means atomic values, 2NF removes partial dependency and 3NF removes transitive dependency. The given table should be converted to 3NF by making separate tables."),
]
answer_scripts = [{"script_id": s, "student_id": sid, "student_name": nm,
                   "question_id": "Q-2025F-6", "rubric_id": "RUB-001", "paper_id": "QP-2025-FIN-01",
                   "answer_text": txt, "word_count": len(txt.split()),
                   "is_typed": True, "submitted_at": "2025-06-02T13:40:00+06:00"}
                  for s, sid, nm, txt in answer_scripts]

# grader1 = F-002 (Dr. Nusrat Jahan), grader2 = F-003 (Md. Tanvir Hasan)
scores_raw = {
    "ANS-01": {"F-002": [4, 5, 5, 4], "F-003": [4, 4, 5, 4]},
    "ANS-02": {"F-002": [3, 3, 4, 2], "F-003": [3, 4, 4, 2]},
    "ANS-03": {"F-002": [3, 4, 6, 0], "F-003": [2, 2, 2, 0]},
    "ANS-04": {"F-002": [2, 3, 3, 1], "F-003": [2, 2, 3, 1]},
    "ANS-05": {"F-002": [4, 5, 5, 3], "F-003": [3, 4, 2, 2]},
    "ANS-06": {"F-002": [1, 2, 2, 0], "F-003": [2, 2, 2, 0]},
}
crit_codes = ["RC-1", "RC-2", "RC-3", "RC-4"]
grading_sessions = [
    {"session_id": "GS-001", "rubric_id": "RUB-001", "grader_id": "F-002",
     "graded_at": "2025-06-09T10:00:00+06:00", "scripts_graded": 6, "mode": "blind_first_marking"},
    {"session_id": "GS-002", "rubric_id": "RUB-001", "grader_id": "F-003",
     "graded_at": "2025-06-09T15:30:00+06:00", "scripts_graded": 6, "mode": "blind_second_marking"},
]

grader_scores, gid = [], 1
for sc, per in scores_raw.items():
    for grader, vals in per.items():
        sess = "GS-001" if grader == "F-002" else "GS-002"
        for code, v in zip(crit_codes, vals):
            grader_scores.append({
                "score_id": f"GSC-{gid:03d}", "session_id": sess, "script_id": sc,
                "rubric_id": "RUB-001", "criterion_id": code, "grader_id": grader,
                "awarded_marks": v,
                "max_marks": next(c["max_marks"] for c in rubric_criteria if c["criterion_id"] == code)})
            gid += 1

script_totals = []
for sc, per in scores_raw.items():
    t1, t2 = sum(per["F-002"]), sum(per["F-003"])
    script_totals.append({
        "script_id": sc, "rubric_id": "RUB-001", "total_marks": 20,
        "grader1_id": "F-002", "grader1_total": t1,
        "grader2_id": "F-003", "grader2_total": t2,
        "difference": abs(t1 - t2),
        "difference_percent": round(abs(t1 - t2) / 20 * 100, 1),
        "mean_total": round((t1 + t2) / 2, 1),
        "is_divergent": abs(t1 - t2) >= 4,
        "status": "escalated" if abs(t1 - t2) >= 4 else "agreed"})

diffs = [s["difference"] for s in script_totals]
grading_consistency = [{
    "report_id": "GCR-001", "rubric_id": "RUB-001", "question_id": "Q-2025F-6",
    "generated_at": "2026-09-06T09:24:05+06:00", "model": "claude-sonnet-4-6",
    "scripts_double_marked": 6,
    "mean_absolute_difference": round(statistics.mean(diffs), 2),
    "max_difference": max(diffs),
    "pearson_r": 0.71, "krippendorff_alpha": 0.58, "agreement_band": "moderate",
    "divergent_script_ids": [s["script_id"] for s in script_totals if s["is_divergent"]],
    "criterion_level_disagreement": [
        {"criterion_id": "RC-1", "code": "R1", "mean_abs_diff": 0.67, "risk": "low"},
        {"criterion_id": "RC-2", "code": "R2", "mean_abs_diff": 0.83, "risk": "low"},
        {"criterion_id": "RC-3", "code": "R3", "mean_abs_diff": 1.67, "risk": "high",
         "note": "Largest single source of disagreement. Triggered by answers that reach a correct 3NF result by an unlisted route."},
        {"criterion_id": "RC-4", "code": "R4", "mean_abs_diff": 0.33, "risk": "low"}],
    "summary": "Two of six double-marked scripts diverge beyond the four-mark departmental threshold. Both divergences originate in criterion R3, and in both cases the students reached a defensible 3NF result by a route the rubric does not enumerate.",
    "rubric_repair_suggestions": [
        "Add to R3: an alternative decomposition that is lossless, dependency preserving and in 3NF receives full marks.",
        "Add to R4: a correct final schema with no justification is capped at 1 of 5 rather than 0, so that R3 and R4 are not double-penalised.",
        "Add a worked exemplar answer at the 6-mark band for R3 to anchor both markers."]
}]

grading_divergences = [
    {"divergence_id": "DIV-001", "report_id": "GCR-001", "script_id": "ANS-03",
     "student_id": "S-017", "grader1_total": 13, "grader2_total": 6, "difference": 7,
     "difference_percent": 35.0, "severity": "critical",
     "primary_criterion_id": "RC-3",
     "criterion_gaps": [{"criterion_id": "RC-1", "gap": 1}, {"criterion_id": "RC-2", "gap": 2},
                        {"criterion_id": "RC-3", "gap": 4}, {"criterion_id": "RC-4", "gap": 0}],
     "ai_diagnosis": "The script is terse but technically correct: the candidate key, the transitive dependency and both 3NF relations are all right. Grader 1 awarded full marks under R3 for the correct end state. Grader 2 marked down heavily because the anomalies were never named and no working was shown, effectively penalising the same omission twice, once under R1 and again under R3. The rubric does not say whether R3 rewards the result or the reasoning.",
     "ai_suggested_total": 11.5, "ai_confidence": 0.74,
     "rule_at_fault": "RC-3 descriptor is silent on unshown working.",
     "resolution_status": "pending_third_examiner", "resolved_total": None},
    {"divergence_id": "DIV-002", "report_id": "GCR-001", "script_id": "ANS-05",
     "student_id": "S-026", "grader1_total": 17, "grader2_total": 11, "difference": 6,
     "difference_percent": 30.0, "severity": "high",
     "primary_criterion_id": "RC-3",
     "criterion_gaps": [{"criterion_id": "RC-1", "gap": 1}, {"criterion_id": "RC-2", "gap": 1},
                        {"criterion_id": "RC-3", "gap": 3}, {"criterion_id": "RC-4", "gap": 1}],
     "ai_diagnosis": "The student decomposed into three relations rather than the two shown in the model answer. The decomposition is lossless, dependency preserving and in 3NF, so it satisfies the stated requirement. Grader 1 accepted it; grader 2 treated any departure from the model answer as an error. This is a rubric gap rather than a marking error: R3 lists a single expected decomposition and gives no instruction for valid alternatives.",
     "ai_suggested_total": 16.0, "ai_confidence": 0.81,
     "rule_at_fault": "RC-3 assumes one canonical decomposition.",
     "resolution_status": "pending_third_examiner", "resolved_total": None},
]

# ---------------------------------------------------------------- ops tables
_co4 = next(a["class_attainment_percent"] for a in co_attainment if a["co_id"] == "CO4")
audit_log = [
    ("AL-001", "2026-09-06T09:12:44+06:00", "F-004", "upload_paper", "QP-2026-DRAFT-01", "CSE3103_Final_Spring2026_DRAFT.pdf uploaded (412 KB, 2 pages)."),
    ("AL-002", "2026-09-06T09:12:47+06:00", "system", "extraction_started", "EXT-RUN-001", "Structured extraction started."),
    ("AL-003", "2026-09-06T09:13:09+06:00", "system", "extraction_finished", "EXT-RUN-001", "9 questions detected, 3 below the confidence threshold. Human confirmation required."),
    ("AL-004", "2026-09-06T09:15:02+06:00", "F-004", "correct_extraction", "EXR-006", "marks 1 -> 10."),
    ("AL-005", "2026-09-06T09:15:31+06:00", "F-004", "correct_extraction", "EXR-004", "co_id CO1 -> CO3."),
    ("AL-006", "2026-09-06T09:16:10+06:00", "F-004", "correct_extraction", "EXR-007", "Split merged parts 4(a) and 4(b)."),
    ("AL-007", "2026-09-06T09:16:22+06:00", "F-004", "confirm_extraction", "EXT-RUN-001", "All 9 rows confirmed by faculty. Analysis unlocked."),
    ("AL-008", "2026-09-06T09:17:22+06:00", "system", "analysis_completed", "AN-001", "Quality score 54/100. 9 findings raised, 2 critical or high on coverage."),
    ("AL-009", "2026-09-06T09:21:40+06:00", "system", "attainment_computed", "OFF-2025-SP", f"CO4 below threshold at {_co4}%."),
    ("AL-010", "2026-09-06T09:24:05+06:00", "system", "consistency_report", "GCR-001", "2 of 6 scripts diverge beyond threshold."),
]
audit_log = [{"log_id": a, "timestamp": b, "actor_id": c, "action": d, "entity_id": e, "detail": f}
             for a, b, c, d, e, f in audit_log]

llm_calls = [
    {"call_id": "LLM-001", "run_id": "EXT-RUN-001", "purpose": "question_structuring",
     "model": "claude-sonnet-4-6", "input_tokens": 3120, "output_tokens": 1440,
     "latency_ms": 21980, "cached": False, "status": "success", "cost_usd": 0.0312},
    {"call_id": "LLM-002", "run_id": "AN-001", "purpose": "co_bloom_tagging",
     "model": "claude-sonnet-4-6", "input_tokens": 2410, "output_tokens": 980,
     "latency_ms": 9120, "cached": False, "status": "success", "cost_usd": 0.0208},
    {"call_id": "LLM-003", "run_id": "AN-001", "purpose": "duplicate_verification",
     "model": "claude-sonnet-4-6", "input_tokens": 1890, "output_tokens": 760,
     "latency_ms": 7340, "cached": True, "status": "success_cached", "cost_usd": 0.0},
    {"call_id": "LLM-004", "run_id": "AN-001", "purpose": "recommendation_drafting",
     "model": "claude-sonnet-4-6", "input_tokens": 2760, "output_tokens": 1310,
     "latency_ms": 11450, "cached": False, "status": "success", "cost_usd": 0.0287},
    {"call_id": "LLM-005", "run_id": "GCR-001", "purpose": "divergence_diagnosis",
     "model": "claude-sonnet-4-6", "input_tokens": 3980, "output_tokens": 1120,
     "latency_ms": 12870, "cached": True, "status": "success_cached", "cost_usd": 0.0},
]

quota = [{
    "quota_id": "Q-DEMO-001", "provider": "anthropic", "key_label": "demo_primary",
    "window": "per_minute", "limit_requests": 50, "used_requests": 12,
    "limit_input_tokens": 40000, "used_input_tokens": 14160,
    "reserve_key_label": "demo_backup", "mock_mode_available": True,
    "cache_hit_rate": 0.40,
    "note": "Freeze all live calls 30 minutes before judging. Cached analysis covers the full demo path."
}]

offline_cache = [{
    "cache_id": "CACHE-SEED-001", "course_id": "C-CSE3103", "paper_id": "QP-2026-DRAFT-01",
    "analysis_id": "AN-001", "generated_at": "2026-09-06T09:17:22+06:00",
    "expires_at": "2026-09-07T23:59:59+06:00", "is_offline_fallback": True,
    "covers": ["extraction", "paper_analysis", "findings", "recommendations",
               "co_attainment", "grading_consistency"],
    "payload": {
        "quality_score": 54, "quality_band": "needs_revision",
        "computed_total_marks": draft_total, "declared_total_marks": 60,
        "co_coverage": co_cov, "untagged_marks": untagged_marks,
        "bloom_summary": paper_analysis[0]["bloom_summary"],
        "finding_ids": [f["finding_id"] for f in findings],
        "duplicate_pair_ids": ["SIM-001", "SIM-002", "SIM-003", "SIM-004"],
        "weak_co_ids": [a["co_id"] for a in co_attainment if a["is_weak"]],
        "divergent_script_ids": [s["script_id"] for s in script_totals if s["is_divergent"]]},
    "note": "Loaded automatically when the API is unreachable so the demo still renders results."
}]

demo_script = [
    {"step": 1, "beat": "problem", "duration_sec": 25,
     "action": "Open the CSE 3103 course file. Show the six COs and the CO-PO matrix already on record.",
     "tables_used": ["courses", "course_outcomes", "co_po_map"], "expected_screen": "Course overview"},
    {"step": 2, "beat": "input", "duration_sec": 20,
     "action": "Upload CSE3103_Final_Spring2026_DRAFT.pdf.",
     "tables_used": ["question_papers", "extraction_runs"], "expected_screen": "Upload and extraction progress"},
    {"step": 3, "beat": "human_in_the_loop", "duration_sec": 40,
     "action": "Extraction-confirm table appears with three low-confidence rows highlighted. Edit EXR-006 marks from 1 to 10, retag EXR-004 to CO3, split EXR-007. Press Confirm.",
     "tables_used": ["extracted_questions_raw", "extraction_corrections"],
     "expected_screen": "Confirm table", "is_key_moment": True,
     "why": "Proves the faculty member stays in control and the AI only proposes."},
    {"step": 4, "beat": "what_the_ai_does", "duration_sec": 35,
     "action": "Run analysis. Coverage heatmap shows CO6 at zero, Bloom bar shows 48% lower order, duplicate panel lists three pairs with the 2024 and 2025 sources side by side.",
     "tables_used": ["paper_analysis", "findings", "similarity_pairs"], "expected_screen": "Analysis dashboard"},
    {"step": 5, "beat": "useful_result", "duration_sec": 35,
     "action": "Accept REC-001. The uncovered CO6 slot is filled with a generated evaluation question, quality score moves from 54 to 68 and the marks total reconciles to 60.",
     "tables_used": ["recommendations"], "expected_screen": "Recommendation accept"},
    {"step": 6, "beat": "second_journey", "duration_sec": 30,
     "action": f"Switch to the attainment view for Spring 2025. CO4 shows red at {_co4}% with the AI diagnosis pointing at candidate-key determination.",
     "tables_used": ["co_attainment", "po_attainment", "attainment_insights"], "expected_screen": "Attainment report"},
    {"step": 7, "beat": "third_journey", "duration_sec": 30,
     "action": "Open the grading consistency report. ANS-03 and ANS-05 flagged, with the diagnosis that criterion R3 is the shared root cause and a proposed rubric fix.",
     "tables_used": ["grading_consistency", "grading_divergences", "rubric_criteria"], "expected_screen": "Consistency report"},
    {"step": 8, "beat": "close", "duration_sec": 15,
     "action": "Export the OBE attainment sheet and the revised paper. Mention the offline cache and that nothing was hard-coded.",
     "tables_used": ["offline_cache"], "expected_screen": "Export"},
]

manifest = {
    "dataset_name": "AUST CSE Carnival 8.0 - AI Build Hackathon seed dataset",
    "version": "1.0.0",
    "generated_at": datetime.now().isoformat(timespec="seconds"),
    "seed_course": "CSE 3103 Database Management Systems",
    "design_note": "Every defect in this dataset is deliberate so that each analysis feature has something real to detect during the demo.",
    "planted_flaws": [
        {"id": "PF-01", "where": "QP-2026-DRAFT-01", "flaw": "CO6 receives zero marks", "detected_by": "FND-001"},
        {"id": "PF-02", "where": "QP-2026-DRAFT-01", "flaw": "48.3% lower-order marks against a 40% cap", "detected_by": "FND-002"},
        {"id": "PF-03", "where": "Q-2026D-2B vs Q-2024M-3A", "flaw": "0.94 cross-paper duplicate", "detected_by": "FND-003 / SIM-001"},
        {"id": "PF-04", "where": "Q-2026D-4A vs Q-2025F-1B", "flaw": "0.87 cross-paper duplicate", "detected_by": "FND-004 / SIM-002"},
        {"id": "PF-05", "where": "Q-2026D-3A vs Q-2026D-1A", "flaw": "0.81 intra-paper redundancy", "detected_by": "FND-005 / SIM-003"},
        {"id": "PF-06", "where": "QP-2026-DRAFT-01", "flaw": "Declared 60 marks, questions total 58", "detected_by": "FND-006"},
        {"id": "PF-07", "where": "Q-2026D-5", "flaw": "Question carries no CO tag", "detected_by": "FND-007"},
        {"id": "PF-08", "where": "Q-2026D-4B", "flaw": "CO5 assessed at Bloom L2 against a target of L5", "detected_by": "FND-008"},
        {"id": "PF-09", "where": "EXR-006", "flaw": "OCR read 10 marks as 1 (the on-stage edit)", "detected_by": "confidence 0.42"},
        {"id": "PF-10", "where": "EXR-004", "flaw": "Wrong CO suggested for an SQL question", "detected_by": "confidence 0.55"},
        {"id": "PF-11", "where": "EXR-007", "flaw": "Parts 4(a) and 4(b) merged into one row", "detected_by": "confidence 0.51"},
        {"id": "PF-12", "where": "student_marks", "flaw": "CO4 attainment below threshold", "detected_by": "co_attainment"},
        {"id": "PF-13", "where": "ANS-03", "flaw": "7-mark grader divergence caused by rubric criterion R3", "detected_by": "DIV-001"},
        {"id": "PF-14", "where": "ANS-05", "flaw": "6-mark grader divergence on a valid alternative decomposition", "detected_by": "DIV-002"},
    ],
    "tables": []
}

# ---------------------------------------------------------------- write
tables = [
    ("departments.json", departments), ("programs.json", programs),
    ("program_outcomes.json", program_outcomes), ("bloom_levels.json", bloom_levels),
    ("faculty.json", faculty), ("courses.json", courses),
    ("course_offerings.json", course_offerings), ("course_outcomes.json", course_outcomes),
    ("co_po_map.json", co_po_map), ("syllabus_topics.json", syllabus_topics),
    ("assessment_plan.json", assessment_plan), ("policy.json", policy),
    ("question_papers.json", question_papers), ("questions.json", questions),
    ("extraction_runs.json", extraction_runs),
    ("extracted_questions_raw.json", extracted_questions_raw),
    ("extraction_corrections.json", extraction_corrections),
    ("similarity_pairs.json", similarity_pairs), ("paper_analysis.json", paper_analysis),
    ("findings.json", findings), ("recommendations.json", recommendations),
    ("students.json", students), ("student_marks.json", student_marks),
    ("co_attainment.json", co_attainment), ("po_attainment.json", po_attainment),
    ("attainment_insights.json", attainment_insights),
    ("rubrics.json", rubrics), ("rubric_criteria.json", rubric_criteria),
    ("answer_scripts.json", answer_scripts), ("grading_sessions.json", grading_sessions),
    ("grader_scores.json", grader_scores), ("script_totals.json", script_totals),
    ("grading_consistency.json", grading_consistency),
    ("grading_divergences.json", grading_divergences),
    ("audit_log.json", audit_log), ("llm_calls.json", llm_calls),
    ("api_quota.json", quota), ("offline_cache.json", offline_cache),
    ("demo_script.json", demo_script),
]
print("Writing tables:")
for n, o in tables:
    dump(n, o)
    manifest["tables"].append({"file": n, "rows": len(o) if isinstance(o, list) else 1})
dump("_manifest.json", manifest)

print("\nSanity checks")
print(f"  draft total marks           : {draft_total} (declared 60, mismatch {60-draft_total})")
print(f"  lower / middle / higher     : {lower} / {middle} / {higher}  -> {round(lower/draft_total*100,1)}% lower, {round(higher/draft_total*100,1)}% higher")
print("  CO coverage in draft        : " + ", ".join(f"{c['co_id']}={c['marks']}({c['status']})" for c in co_cov))
print(f"  untagged marks              : {untagged_marks}")
print("  CO attainment (2025 final)  : " + ", ".join(f"{a['co_id']}={a['class_attainment_percent']}%{'*' if a['is_weak'] else ''}" for a in co_attainment))
print("  PO attainment               : " + ", ".join(f"{p['po_id']}={p['weighted_attainment_percent']}%" for p in po_attainment))
print("  grader divergences          : " + ", ".join(f"{s['script_id']}:{s['grader1_total']}v{s['grader2_total']}(d{s['difference']})" for s in script_totals))
print(f"  student_marks rows          : {len(student_marks)}")
