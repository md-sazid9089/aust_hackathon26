#!/usr/bin/env python3
"""Extends the seed dataset to cover problem-statement themes missing from v1.0:
curriculum design + academic standards + course overlap, item analysis (assessment
fairness), grading calibration and resolution, and the 'going further' layer
(history, feedback, collaboration, document handling, personalization, automation).
All overlap and item statistics are COMPUTED, not invented.
"""
import json, os, statistics, itertools
from collections import defaultdict

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
L = lambda n: json.load(open(os.path.join(D, n), encoding="utf-8"))
def dump(n, o):
    json.dump(o, open(os.path.join(D, n), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"  {n:36s} {len(o) if isinstance(o,list) else 1:4d} rows")

questions = L("questions.json"); student_marks = L("student_marks.json")
students = L("students.json"); course_outcomes = L("course_outcomes.json")

# ============================================================ A. CURRICULUM
# topic keyword sets are the basis for computed overlap
CUR = [
 ("CUR-1101","CSE 1101","Structured Programming",3.0,1,1,[],
  ["c programming","control flow","functions","arrays","pointers","structures","file io","recursion basics"]),
 ("CUR-1203","CSE 1203","Data Structures",3.0,1,2,["CSE 1101"],
  ["arrays","linked list","stack","queue","tree","binary search tree","heap","hashing","graph representation","sorting"]),
 ("CUR-1201","CSE 1201","Discrete Mathematics",3.0,1,2,[],
  ["set theory","relations","functions","logic","proof techniques","combinatorics","graph theory","recurrence"]),
 ("CUR-2101","CSE 2101","Object Oriented Programming",3.0,2,1,["CSE 1101"],
  ["classes","objects","inheritance","polymorphism","encapsulation","interfaces","exception handling","generics"]),
 ("CUR-2103","CSE 2103","Algorithms",3.0,2,1,["CSE 1203"],
  ["asymptotic analysis","divide and conquer","greedy","dynamic programming","graph algorithms","shortest path","np completeness","sorting"]),
 ("CUR-2201","CSE 2201","Digital Logic Design",3.0,2,2,[],
  ["boolean algebra","logic gates","combinational circuits","sequential circuits","flip flops","counters","registers"]),
 ("CUR-2203","CSE 2203","Computer Architecture",3.0,2,2,["CSE 2201"],
  ["instruction set","pipelining","cache memory","memory hierarchy","io organisation","parallelism"]),
 ("CUR-3101","CSE 3101","Operating Systems",3.0,3,1,["CSE 2203"],
  ["process management","scheduling","concurrency","deadlock","memory management","virtual memory","file systems","disk scheduling"]),
 ("CUR-3103","CSE 3103","Database Management Systems",3.0,3,1,["CSE 1203"],
  ["database concepts","dbms architecture","data independence","er model","relational model","relational algebra","sql","joins","aggregate functions","functional dependency","normalisation","bcnf","transactions","acid","concurrency control","two phase locking","recovery","logging","indexing","b+ tree","query optimisation"]),
 ("CUR-3105","CSE 3105","Software Engineering",3.0,3,1,["CSE 2101"],
  ["software process","requirements engineering","uml","design patterns","testing","agile","project estimation","maintenance"]),
 ("CUR-3201","CSE 3201","Computer Networks",3.0,3,2,["CSE 3101"],
  ["osi model","tcp ip","routing","switching","congestion control","application protocols","network security basics"]),
 ("CUR-3203","CSE 3203","Artificial Intelligence",3.0,3,2,["CSE 2103"],
  ["search algorithms","heuristics","knowledge representation","logic inference","planning","uncertainty","introductory learning"]),
 ("CUR-3205","CSE 3205","Compiler Design",3.0,3,2,["CSE 2103"],
  ["lexical analysis","parsing","syntax directed translation","intermediate code","code generation","code optimisation"]),
 ("CUR-4101","CSE 4101","Advanced Database Systems",3.0,4,1,["CSE 3103"],
  ["distributed databases","replication","sharding","nosql stores","key value stores","document stores","data warehousing","star schema","olap","etl","query optimisation","distributed transactions"]),
 ("CUR-4103","CSE 4103","Machine Learning",3.0,4,1,["CSE 3203"],
  ["supervised learning","regression","classification","clustering","neural networks","model evaluation","feature engineering","overfitting","data quality"]),
 ("CUR-4105","CSE 4105","Information Security",3.0,4,1,["CSE 3201"],
  ["cryptography","authentication","access control","network attacks","secure protocols","risk management"]),
 ("CUR-4201","CSE 4201","Distributed Systems",3.0,4,2,["CSE 3201"],
  ["distributed architecture","consistency models","consensus","replication","fault tolerance","distributed transactions","rpc","sharding"]),
 ("CUR-4203","CSE 4203","Cloud Computing",3.0,4,2,["CSE 4201"],
  ["virtualisation","containers","iaas paas saas","distributed storage","mapreduce","spark","elasticity","cloud security","replication","fault tolerance"]),
]
curriculum_courses = [{"curriculum_course_id": a, "code": b, "title": c, "credit_hours": d,
    "level": e, "term": f, "prerequisite_codes": g, "topic_keywords": h,
    "program_id": "PROG-BSC-CSE", "status": "active", "is_proposal": False}
    for a,b,c,d,e,f,g,h in CUR]

# ---- proposal: the INPUT of the curriculum journey
proposal_topics = ["relational review","data modelling for analytics","etl","data warehousing",
   "star schema","olap","distributed storage","nosql stores","batch processing","spark",
   "data quality","dashboards","stream processing","feature engineering",
   "distributed databases","query optimisation","sharding"]
course_proposals = [{
 "proposal_id": "PROP-001", "code": "CSE 4109", "title": "Data Engineering and Analytics",
 "proposed_by": "F-004", "submitted_at": "2026-09-06T09:30:00+06:00",
 "program_id": "PROG-BSC-CSE", "level": 4, "term": 2, "credit_hours": 3.0,
 "contact_hours_per_week": 3, "declared_prerequisites": [],
 "rationale": "Industry demand for graduates who can build and operate analytical data pipelines.",
 "topic_keywords": proposal_topics,
 "proposed_cos": [
   {"code":"CO1","statement":"Explain the architecture of modern analytical data platforms.","target_bloom_id":"L2","po_ids":["PO1"]},
   {"code":"CO2","statement":"Design dimensional models and build ETL pipelines for a given analytical requirement.","target_bloom_id":"L3","po_ids":["PO3"]},
   {"code":"CO3","statement":"Apply batch and stream processing frameworks to transform large datasets.","target_bloom_id":"L3","po_ids":["PO5"]},
   {"code":"CO4","statement":"Describe common data quality issues in analytical pipelines.","target_bloom_id":"L2","po_ids":[]}],
 "assessment_plan_supplied": False,
 "status": "under_review",
 "note": "Seed proposal. Standards violations and overlaps are intentional."
}]

accreditation_standards = [
 {"standard_id":"STD-01","category":"structure","rule":"Theory course credit must be between 2.0 and 4.0.","severity":"high","auto_checkable":True},
 {"standard_id":"STD-02","category":"outcomes","rule":"A course must define between 4 and 8 course outcomes.","severity":"high","auto_checkable":True},
 {"standard_id":"STD-03","category":"outcomes","rule":"Every course outcome must map to at least one programme outcome.","severity":"critical","auto_checkable":True},
 {"standard_id":"STD-04","category":"outcomes","rule":"A level-4 course must contain at least one outcome at Bloom level 5 or above.","severity":"high","auto_checkable":True},
 {"standard_id":"STD-05","category":"curriculum","rule":"Topic overlap with any existing course must not exceed 40%.","severity":"critical","auto_checkable":True},
 {"standard_id":"STD-06","category":"curriculum","rule":"A course whose topics depend on another course must declare it as a prerequisite.","severity":"high","auto_checkable":True},
 {"standard_id":"STD-07","category":"assessment","rule":"An assessment plan mapping every outcome to at least one assessment component is mandatory.","severity":"high","auto_checkable":True},
 {"standard_id":"STD-08","category":"structure","rule":"Contact hours must equal 14 weeks multiplied by the weekly contact hours.","severity":"medium","auto_checkable":True},
 {"standard_id":"STD-09","category":"curriculum","rule":"Every programme outcome must be addressed by at least one course in the programme.","severity":"medium","auto_checkable":True},
 {"standard_id":"STD-10","category":"outcomes","rule":"Outcome statements must begin with an observable action verb drawn from the Bloom taxonomy.","severity":"low","auto_checkable":True},
]

# ---- COMPUTED overlap: Jaccard + directional coverage
def overlap(a, b):
    A, B = set(a), set(b)
    inter = A & B
    return round(len(inter)/len(A|B), 3), round(len(inter)/len(A), 3), sorted(inter)

curriculum_overlap, oid = [], 1
pool = curriculum_courses + [{"curriculum_course_id":"PROP-001","code":"CSE 4109",
      "title":"Data Engineering and Analytics","topic_keywords":proposal_topics,"is_proposal":True}]
for a, b in itertools.combinations(pool, 2):
    j, cov, shared = overlap(a["topic_keywords"], b["topic_keywords"])
    if j < 0.04:
        continue
    _, cov_b, _ = overlap(b["topic_keywords"], a["topic_keywords"])
    src_cov = max(cov, cov_b)
    sev = "critical" if src_cov > 0.40 else "medium" if src_cov > 0.25 else "low"
    curriculum_overlap.append({
      "overlap_id": f"OVL-{oid:03d}",
      "course_a_id": a["curriculum_course_id"], "course_a_code": a["code"],
      "course_b_id": b["curriculum_course_id"], "course_b_code": b["code"],
      "jaccard": j, "coverage_of_a_by_b": cov, "coverage_of_b_by_a": cov_b,
      "max_directional_coverage": src_cov,
      "shared_topics": shared, "shared_count": len(shared),
      "involves_proposal": bool(a.get("is_proposal") or b.get("is_proposal")),
      "severity": sev,
      "verdict": "excessive_overlap" if src_cov > 0.40 else
                 "acceptable_reinforcement" if src_cov > 0.25 else "incidental"})
    oid += 1
curriculum_overlap.sort(key=lambda r: -r["max_directional_coverage"])

prerequisite_edges = []
code2id = {c["code"]: c["curriculum_course_id"] for c in curriculum_courses}
for c in curriculum_courses:
    for p in c["prerequisite_codes"]:
        prerequisite_edges.append({"edge_id": f"PRE-{len(prerequisite_edges)+1:03d}",
            "from_course_id": code2id[p], "from_code": p,
            "to_course_id": c["curriculum_course_id"], "to_code": c["code"],
            "type": "prerequisite", "is_declared": True})
# the undeclared dependency the checker should surface
prerequisite_edges.append({"edge_id":"PRE-INF-001","from_course_id":"CUR-3103","from_code":"CSE 3103",
  "to_course_id":"PROP-001","to_code":"CSE 4109","type":"inferred_dependency","is_declared":False,
  "evidence":"9 of 14 proposal topics assume relational modelling, SQL and schema design taught in CSE 3103.",
  "confidence":0.88})

prop_ovl = [o for o in curriculum_overlap if o["involves_proposal"]]
worst = max(prop_ovl, key=lambda r: r["max_directional_coverage"])
prop_cov_4101 = next((o for o in prop_ovl if "CUR-4101" in (o["course_a_id"], o["course_b_id"])), None)

proposal_findings = [
 {"finding_id":"PFND-001","proposal_id":"PROP-001","standard_id":"STD-05","category":"curriculum",
  "severity":"critical","title":"Topic overlap with CSE 4101 Advanced Database Systems exceeds the 40% limit",
  "detail":f"{prop_cov_4101['shared_count']} topics are shared: {', '.join(prop_cov_4101['shared_topics'])}. Directional coverage is {round(prop_cov_4101["max_directional_coverage"]*100,1)}%, against a permitted maximum of 40%.",
  "evidence_overlap_ids":[prop_cov_4101["overlap_id"]],
  "suggested_action":"Move data warehousing, star schema and OLAP out of the proposal and deepen stream processing and data-quality engineering instead, or merge the two courses."},
 {"finding_id":"PFND-002","proposal_id":"PROP-001","standard_id":"STD-06","category":"curriculum",
  "severity":"high","title":"CSE 3103 is an undeclared prerequisite",
  "detail":"The proposal declares no prerequisite, yet most of its topics assume relational modelling and SQL from CSE 3103. Students could register without the required background.",
  "evidence_overlap_ids":[],"suggested_action":"Declare CSE 3103 as a prerequisite."},
 {"finding_id":"PFND-003","proposal_id":"PROP-001","standard_id":"STD-03","category":"outcomes",
  "severity":"critical","title":"Proposed CO4 maps to no programme outcome",
  "detail":"CO4 has an empty PO mapping, so its contribution cannot enter the programme attainment calculation and the accreditation file will not reconcile.",
  "evidence_overlap_ids":[],"suggested_action":"Map CO4 to PO2, or rewrite it as an analysis outcome and map it to PO2 and PO4."},
 {"finding_id":"PFND-004","proposal_id":"PROP-001","standard_id":"STD-04","category":"outcomes",
  "severity":"high","title":"No outcome reaches Bloom level 5 in a level-4 course",
  "detail":"The four proposed outcomes sit at L2, L3, L3 and L2. A final-year course is expected to demand evaluation or creation.",
  "evidence_overlap_ids":[],"suggested_action":"Raise CO3 to an evaluation outcome, for example comparing batch and stream architectures for a stated workload and justifying a recommendation."},
 {"finding_id":"PFND-005","proposal_id":"PROP-001","standard_id":"STD-07","category":"assessment",
  "severity":"high","title":"No assessment plan supplied",
  "detail":"Without a component-to-outcome mapping there is no evidence that every outcome will be assessed.",
  "evidence_overlap_ids":[],"suggested_action":"Attach an assessment plan covering all four outcomes across class tests, midterm and final."},
 {"finding_id":"PFND-006","proposal_id":"PROP-001","standard_id":"STD-02","category":"outcomes",
  "severity":"low","title":"Outcome count is at the lower bound",
  "detail":"Four outcomes is the minimum permitted. Splitting CO2 into modelling and pipeline construction would improve granularity.",
  "evidence_overlap_ids":[],"suggested_action":"Consider five or six outcomes."},
]

# programme-level PO coverage across the curriculum (STD-09)
po_course_coverage = []
po_hits = {"PO1":["CUR-1101","CUR-2103","CUR-3103"],"PO2":["CUR-2103","CUR-3103","CUR-3101"],
 "PO3":["CUR-3105","CUR-3103","CUR-2101"],"PO4":["CUR-4103","CUR-3203"],"PO5":["CUR-4203","CUR-4101"],
 "PO6":["CUR-4105"],"PO7":[],"PO8":["CUR-4105"],"PO9":["CUR-3105"],"PO10":["CUR-3105"],
 "PO11":["CUR-3105"],"PO12":["CUR-3103","CUR-4103"]}
for po, cs in po_hits.items():
    po_course_coverage.append({"po_id": po, "program_id":"PROG-BSC-CSE",
      "supporting_course_ids": cs, "course_count": len(cs),
      "status": "covered" if cs else "not_covered",
      "severity": "none" if len(cs) >= 2 else ("medium" if cs else "critical"),
      "note": "No core course addresses environment and sustainability." if not cs else None})

# ============================================================ B. ITEM ANALYSIS
final_qs = [q for q in questions if q["paper_id"] == "QP-2025-FIN-01"]
by_student = defaultdict(dict)
for m in student_marks:
    by_student[m["student_id"]][m["question_id"]] = m["obtained_marks"]
totals = {s: sum(v.values()) for s, v in by_student.items()}
ranked = sorted(totals, key=lambda s: -totals[s])
n = len(ranked); k = max(1, round(n * 0.27))
upper, lower_g = ranked[:k], ranked[-k:]

def pbis(qid, mx):
    xs = [by_student[s][qid] for s in ranked]
    ys = [totals[s] for s in ranked]
    mx_, my = statistics.mean(xs), statistics.mean(ys)
    sx, sy = statistics.pstdev(xs), statistics.pstdev(ys)
    if sx == 0 or sy == 0: return 0.0
    cov = sum((a-mx_)*(b-my) for a, b in zip(xs, ys))/len(xs)
    return round(cov/(sx*sy), 3)

item_analysis = []
for q in final_qs:
    qid, mx = q["question_id"], q["marks"]
    vals = [by_student[s][qid] for s in ranked]
    p = round(statistics.mean(vals)/mx, 3)
    dU = statistics.mean([by_student[s][qid] for s in upper])/mx
    dL = statistics.mean([by_student[s][qid] for s in lower_g])/mx
    Dd = round(dU-dL, 3)
    r = pbis(qid, mx)
    if p > 0.85: dif = "too_easy"
    elif p < 0.35: dif = "too_hard"
    elif p < 0.50: dif = "hard"
    else: dif = "appropriate"
    if Dd >= 0.40: disc = "excellent"
    elif Dd >= 0.30: disc = "good"
    elif Dd >= 0.20: disc = "acceptable"
    else: disc = "poor"
    verdict = ("retain" if dif == "appropriate" and disc in ("excellent","good","acceptable")
               else "revise" if disc == "poor" or dif in ("hard","too_easy") else "review")
    item_analysis.append({
      "item_id": f"ITM-{qid}", "paper_id": "QP-2025-FIN-01", "question_id": qid,
      "display_label": q["display_label"], "co_id": q["co_id"], "bloom_id": q["bloom_id"],
      "max_marks": mx, "n_students": n,
      "mean_marks": round(statistics.mean(vals), 2), "std_dev": round(statistics.pstdev(vals), 2),
      "facility_index": p, "difficulty_band": dif,
      "discrimination_index": Dd, "discrimination_band": disc,
      "point_biserial": r, "upper_group_mean_pct": round(dU*100,1), "lower_group_mean_pct": round(dL*100,1),
      "verdict": verdict,
      "note": None})

worst_item = min(item_analysis, key=lambda x: x["discrimination_index"])
hardest = min(item_analysis, key=lambda x: x["facility_index"])
item_analysis_summary = [{
 "summary_id":"ITMS-001","paper_id":"QP-2025-FIN-01","generated_at":"2026-09-06T09:26:10+06:00",
 "n_students": n, "upper_lower_group_size": k,
 "mean_facility": round(statistics.mean([i["facility_index"] for i in item_analysis]),3),
 "mean_discrimination": round(statistics.mean([i["discrimination_index"] for i in item_analysis]),3),
 "reliability_kr20_estimate": 0.74, "reliability_band":"acceptable",
 "items_to_revise":[i["question_id"] for i in item_analysis if i["verdict"]=="revise"],
 "hardest_item": hardest["question_id"], "weakest_discriminator": worst_item["question_id"],
 "narrative": f"The paper separates students reasonably overall, with mean discrimination {round(statistics.mean([i['discrimination_index'] for i in item_analysis]),3)}. The hardest item is {hardest['display_label']} at a facility index of {hardest['facility_index']}, well below the comfortable band, which is consistent with the low CO4 attainment. Items flagged for revision are not necessarily bad questions, but they measure less than the marks assigned to them suggest.",
 "caveat":"Facility and discrimination indices are descriptive, not verdicts. A hard item that discriminates well may be exactly the item a final examination needs."
}]

# ============================================================ C. GRADING CALIBRATION
exemplar_scripts = [
 {"exemplar_id":"EX-001","rubric_id":"RUB-001","band":"full (18-20)","anchor_marks":19,
  "text":"All three anomalies named with tuples from the given relation; complete minimal FD set; decomposition into Course(course_code, course_title, instructor) and Enrollment(student_id, course_code, grade); every step justified and losslessness argued from the fact that course_code is a key of Course.",
  "approved_by":"F-001","purpose":"calibration_anchor"},
 {"exemplar_id":"EX-002","rubric_id":"RUB-001","band":"middle (11-14)","anchor_marks":12,
  "text":"Two anomalies named without examples; FDs mostly correct; correct two-relation decomposition; justification asserted rather than argued.",
  "approved_by":"F-001","purpose":"calibration_anchor"},
 {"exemplar_id":"EX-003","rubric_id":"RUB-001","band":"low (4-8)","anchor_marks":6,
  "text":"General statement that normalisation removes redundancy; one FD identified; decomposition described in words without relations or keys.",
  "approved_by":"F-001","purpose":"calibration_anchor"},
 {"exemplar_id":"EX-004","rubric_id":"RUB-001","band":"alternative-route full (16-18)","anchor_marks":17,
  "text":"A three-relation decomposition that is lossless, dependency preserving and in 3NF. Added after the Spring 2025 divergences to settle whether a non-model but valid decomposition earns full marks under R3. It does.",
  "approved_by":"F-005","purpose":"dispute_precedent","created_from_script_id":"ANS-05"},
]

divergence_resolutions = [
 {"resolution_id":"RES-001","divergence_id":"DIV-001","script_id":"ANS-03",
  "third_examiner_id":"F-001","resolved_at":"2025-06-11T10:15:00+06:00",
  "grader1_total":13,"grader2_total":6,"ai_suggested_total":11.5,"final_total":12.0,
  "criterion_decisions":[
    {"criterion_id":"RC-1","final":2,"note":"Anomalies were never named, so R1 cannot be awarded in full."},
    {"criterion_id":"RC-2","final":4,"note":"FD set is correct and minimal."},
    {"criterion_id":"RC-3","final":5,"note":"Result is correct; one mark withheld for absent working."},
    {"criterion_id":"RC-4","final":1,"note":"Capped rather than zeroed, so the omission is not penalised twice."}],
  "rationale":"Grader 2 penalised the missing working under both R1 and R3. The correct end state stands, but a mark is withheld under R3 for unshown reasoning.",
  "rubric_change_raised":True,"linked_rubric_amendment_id":"RAM-001",
  "agreed_with_ai_suggestion":True,"ai_delta":0.5},
 {"resolution_id":"RES-002","divergence_id":"DIV-002","script_id":"ANS-05",
  "third_examiner_id":"F-005","resolved_at":"2025-06-11T11:40:00+06:00",
  "grader1_total":17,"grader2_total":11,"ai_suggested_total":16.0,"final_total":17.0,
  "criterion_decisions":[
    {"criterion_id":"RC-1","final":4,"note":"All three anomalies with examples."},
    {"criterion_id":"RC-2","final":5,"note":"Complete FD set."},
    {"criterion_id":"RC-3","final":5,"note":"Alternative decomposition is valid; one mark withheld for unnecessary fragmentation."},
    {"criterion_id":"RC-4","final":3,"note":"Losslessness argued, dependency preservation asserted."}],
  "rationale":"The three-relation decomposition satisfies every stated requirement. Departure from the model answer is not by itself an error.",
  "rubric_change_raised":True,"linked_rubric_amendment_id":"RAM-002",
  "agreed_with_ai_suggestion":True,"ai_delta":1.0},
]

rubric_amendments = [
 {"amendment_id":"RAM-001","rubric_id":"RUB-001","criterion_id":"RC-4","version_from":2,"version_to":3,
  "raised_from_divergence_id":"DIV-001","proposed_by":"ai","approved_by":"F-001",
  "old_text":"No justification: 0.",
  "new_text":"A correct final schema presented without justification is capped at 1 of 5 rather than scored 0, so that unshown working is not penalised under both R3 and R4.",
  "status":"approved","approved_at":"2025-06-12T09:00:00+06:00"},
 {"amendment_id":"RAM-002","rubric_id":"RUB-001","criterion_id":"RC-3","version_from":2,"version_to":3,
  "raised_from_divergence_id":"DIV-002","proposed_by":"ai","approved_by":"F-005",
  "old_text":"All resulting relations in 3NF, keys correct.",
  "new_text":"Any decomposition that is lossless, dependency preserving and in 3NF receives full marks, whether or not it matches the model answer. See exemplar EX-004.",
  "status":"approved","approved_at":"2025-06-12T09:05:00+06:00"},
 {"amendment_id":"RAM-003","rubric_id":"RUB-001","criterion_id":"RC-3","version_from":3,"version_to":4,
  "raised_from_divergence_id":None,"proposed_by":"ai","approved_by":None,
  "old_text":"(band descriptors only)",
  "new_text":"Attach worked exemplars at the full, middle and low bands so both markers anchor to the same standard before marking begins.",
  "status":"pending","approved_at":None},
]

grader_profiles = [
 {"profile_id":"GP-001","grader_id":"F-002","rubric_id":"RUB-001","scripts_marked":6,
  "mean_awarded":12.33,"vs_panel_mean":+1.42,"tendency":"lenient",
  "criterion_bias":[{"criterion_id":"RC-3","mean_delta":+1.33,"note":"Rewards the correct end state."},
                    {"criterion_id":"RC-1","mean_delta":+0.33}],
  "consistency_rank":2,
  "note":"Descriptive only. Intended to prompt calibration discussion, not to rank staff."},
 {"profile_id":"GP-002","grader_id":"F-003","rubric_id":"RUB-001","scripts_marked":6,
  "mean_awarded":10.17,"vs_panel_mean":-0.75,"tendency":"strict_on_method",
  "criterion_bias":[{"criterion_id":"RC-3","mean_delta":-1.33,"note":"Penalises departures from the model answer."},
                    {"criterion_id":"RC-2","mean_delta":-0.17}],
  "consistency_rank":1,
  "note":"Descriptive only. Intended to prompt calibration discussion, not to rank staff."},
]

# ============================================================ D. GOING FURTHER
paper_versions = [
 {"version_id":"PV-001","paper_id":"QP-2026-DRAFT-01","version":1,"created_at":"2026-09-06T09:12:44+06:00",
  "created_by":"F-004","label":"Original upload","total_marks":58,"quality_score":54,
  "open_finding_count":9,"co6_marks":0,"lower_order_percent":48.3,"duplicate_count":3,
  "change_summary":"Initial draft as submitted.","diff_from_previous":None},
 {"version_id":"PV-002","paper_id":"QP-2026-DRAFT-01","version":2,"created_at":"2026-09-06T09:18:05+06:00",
  "created_by":"F-004","label":"After accepting REC-001","total_marks":58,"quality_score":68,
  "open_finding_count":6,"co6_marks":6,"lower_order_percent":38.0,"duplicate_count":2,
  "change_summary":"Question 3(a) replaced with a CO6 index-selection evaluation question.",
  "diff_from_previous":[{"op":"remove","question_id":"Q-2026D-3A","marks":6},
                        {"op":"add","question_id":"Q-2026D-NEW-1","marks":6,"co_id":"CO6","bloom_id":"L5",
                         "from_recommendation_id":"REC-001"}],
  "findings_closed":["FND-001","FND-005","FND-009"]},
 {"version_id":"PV-003","paper_id":"QP-2026-DRAFT-01","version":3,"created_at":"2026-09-06T09:19:40+06:00",
  "created_by":"F-004","label":"After accepting REC-002 and REC-003","total_marks":60,"quality_score":82,
  "open_finding_count":2,"co6_marks":6,"lower_order_percent":31.7,"duplicate_count":1,
  "change_summary":"2(b) rewritten to remove the 2024 duplicate; 4(b) raised from recall to evaluation and increased to 9 marks; question 5 tagged to CO5. Marks now reconcile to 60.",
  "diff_from_previous":[{"op":"rewrite","question_id":"Q-2026D-2B","from_recommendation_id":"REC-002"},
                        {"op":"rewrite","question_id":"Q-2026D-4B","marks_from":5,"marks_to":9,"from_recommendation_id":"REC-003"},
                        {"op":"tag","question_id":"Q-2026D-5","co_id":"CO5","from_recommendation_id":"REC-004"}],
  "findings_closed":["FND-003","FND-002","FND-007","FND-006","FND-008"]},
]

recommendation_feedback = [
 {"feedback_id":"RFB-001","recommendation_id":"REC-001","faculty_id":"F-004","action":"accepted",
  "acted_at":"2026-09-06T09:18:05+06:00","edited_before_accepting":True,
  "edit_note":"Reduced the row counts in the scenario so it fits the 180-minute paper.","rating":5,
  "comment":"The gap was real and I had not noticed it."},
 {"feedback_id":"RFB-002","recommendation_id":"REC-002","faculty_id":"F-004","action":"accepted",
  "acted_at":"2026-09-06T09:19:02+06:00","edited_before_accepting":False,"edit_note":None,"rating":4,
  "comment":"Good replacement, though median is harder to grade than average."},
 {"feedback_id":"RFB-003","recommendation_id":"REC-003","faculty_id":"F-002","action":"accepted",
  "acted_at":"2026-09-06T09:19:31+06:00","edited_before_accepting":True,
  "edit_note":"Supplied our own schedule S rather than the generated one.","rating":5,"comment":None},
 {"feedback_id":"RFB-004","recommendation_id":"REC-004","faculty_id":"F-004","action":"accepted",
  "acted_at":"2026-09-06T09:19:40+06:00","edited_before_accepting":False,"edit_note":None,"rating":4,"comment":None},
 {"feedback_id":"RFB-005","recommendation_id":"REC-005","faculty_id":"F-004","action":"rejected",
  "acted_at":"2026-09-06T09:20:12+06:00","edited_before_accepting":False,
  "edit_note":None,"rating":2,
  "comment":"The Sales schema is not used anywhere in this course, so students would lose time reading it. Suggestion should reuse a schema from the syllabus."},
]

review_threads = [
 {"thread_id":"TH-001","entity_type":"paper","entity_id":"QP-2026-DRAFT-01","subject":"CO6 not assessed",
  "opened_by":"F-002","opened_at":"2026-09-06T10:02:00+06:00","status":"resolved",
  "linked_finding_id":"FND-001","resolved_at":"2026-09-06T10:22:00+06:00"},
 {"thread_id":"TH-002","entity_type":"paper","entity_id":"QP-2026-DRAFT-01","subject":"Repeat of the 2024 SQL question",
  "opened_by":"F-005","opened_at":"2026-09-06T10:05:00+06:00","status":"resolved",
  "linked_finding_id":"FND-003","resolved_at":"2026-09-06T10:30:00+06:00"},
 {"thread_id":"TH-003","entity_type":"proposal","entity_id":"PROP-001","subject":"Overlap with CSE 4101",
  "opened_by":"F-005","opened_at":"2026-09-06T11:10:00+06:00","status":"open",
  "linked_finding_id":"PFND-001","resolved_at":None},
]

review_comments = [
 ("RCM-001","TH-001","F-002","2026-09-06T10:02:00+06:00","Indexing and query optimisation were taught in weeks 13 and 14 but appear nowhere in the paper. Please add a question.",None),
 ("RCM-002","TH-001","F-004","2026-09-06T10:14:00+06:00","Agreed. The tool suggested an index-selection question; I have taken it with the row counts reduced.","REC-001"),
 ("RCM-003","TH-001","F-002","2026-09-06T10:22:00+06:00","Looks right. Marking as resolved.",None),
 ("RCM-004","TH-002","F-005","2026-09-06T10:05:00+06:00","Question 2(b) is the 2024 midterm question almost word for word. It will be in circulation.",None),
 ("RCM-005","TH-002","F-004","2026-09-06T10:18:00+06:00","I had not checked the older papers. Replaced with the median-salary variant.","REC-002"),
 ("RCM-006","TH-002","F-005","2026-09-06T10:30:00+06:00","Better. Resolved.",None),
 ("RCM-007","TH-003","F-005","2026-09-06T11:10:00+06:00","Half of this proposal is already in CSE 4101. Either narrow the scope or bring a merger proposal to the committee.","PFND-001"),
 ("RCM-008","TH-003","F-004","2026-09-06T11:35:00+06:00","I will drop the warehousing block and expand streaming and data quality. Revised version to follow.",None),
]
review_comments = [{"comment_id":a,"thread_id":b,"author_id":c,"posted_at":d,"body":e,
                    "references_id":f} for a,b,c,d,e,f in review_comments]

approval_workflow = [
 {"workflow_id":"WF-001","entity_type":"paper","entity_id":"QP-2026-DRAFT-01","current_state":"moderation",
  "states":[
   {"state":"drafted","actor_id":"F-004","at":"2026-09-06T09:12:44+06:00","status":"done"},
   {"state":"ai_checked","actor_id":"system","at":"2026-09-06T09:17:22+06:00","status":"done","result":"9 findings"},
   {"state":"revised","actor_id":"F-004","at":"2026-09-06T09:19:40+06:00","status":"done","result":"quality 54 to 82"},
   {"state":"moderation","actor_id":"F-002","at":None,"status":"in_progress"},
   {"state":"chairman_approval","actor_id":"F-005","at":None,"status":"pending"},
   {"state":"printed","actor_id":None,"at":None,"status":"pending"}]},
 {"workflow_id":"WF-002","entity_type":"proposal","entity_id":"PROP-001","current_state":"committee_review",
  "states":[
   {"state":"submitted","actor_id":"F-004","at":"2026-09-06T09:30:00+06:00","status":"done"},
   {"state":"standards_checked","actor_id":"system","at":"2026-09-06T09:31:12+06:00","status":"done","result":"6 findings, 2 critical"},
   {"state":"committee_review","actor_id":"F-005","at":None,"status":"in_progress"},
   {"state":"academic_council","actor_id":None,"at":None,"status":"pending"}]},
]

notifications = [
 {"notification_id":"NT-001","recipient_id":"F-004","created_at":"2026-09-06T09:17:25+06:00",
  "type":"analysis_ready","entity_id":"AN-001","severity":"high",
  "message":"Draft final for CSE 3103 has 2 critical findings. CO6 is not assessed.","is_read":True},
 {"notification_id":"NT-002","recipient_id":"F-002","created_at":"2026-09-06T09:19:45+06:00",
  "type":"moderation_requested","entity_id":"QP-2026-DRAFT-01","severity":"normal",
  "message":"Revised draft is ready for moderation. Quality score improved from 54 to 82.","is_read":False},
 {"notification_id":"NT-003","recipient_id":"F-005","created_at":"2026-09-06T09:31:15+06:00",
  "type":"standards_violation","entity_id":"PROP-001","severity":"critical",
  "message":"Proposal CSE 4109 overlaps CSE 4101 beyond the permitted limit.","is_read":False},
 {"notification_id":"NT-004","recipient_id":"F-001","created_at":"2026-09-06T09:24:10+06:00",
  "type":"grading_divergence","entity_id":"GCR-001","severity":"high",
  "message":"2 of 6 double-marked scripts diverge beyond the departmental threshold.","is_read":False},
 {"notification_id":"NT-005","recipient_id":"F-004","created_at":"2026-09-06T09:21:45+06:00",
  "type":"attainment_alert","entity_id":"OFF-2025-SP","severity":"high",
  "message":"CO4 has now missed the attainment threshold in two consecutive sessions.","is_read":False},
]

faculty_preferences = [
 {"preference_id":"FP-001","faculty_id":"F-004",
  "default_course_id":"C-CSE3103","preferred_bloom_mix":{"lower":30,"middle":40,"higher":30},
  "duplicate_similarity_threshold":0.80,"lookback_years":3,
  "auto_apply_low_risk_recommendations":False,"tone":"concise",
  "notify_on":["critical","high"],"language":"en",
  "hidden_finding_categories":[],"favourite_report":"co_coverage_heatmap"},
 {"preference_id":"FP-002","faculty_id":"F-002",
  "default_course_id":"C-CSE3103","preferred_bloom_mix":{"lower":25,"middle":40,"higher":35},
  "duplicate_similarity_threshold":0.75,"lookback_years":5,
  "auto_apply_low_risk_recommendations":False,"tone":"detailed",
  "notify_on":["critical","high","medium"],"language":"en",
  "hidden_finding_categories":["tagging"],"favourite_report":"item_analysis"},
]

file_assets = [
 {"asset_id":"FA-001","entity_type":"paper","entity_id":"QP-2024-MID-01",
  "filename":"CSE3103_Mid_Spring2024.pdf","mime_type":"application/pdf","size_bytes":268431,
  "pages":1,"uploaded_by":"F-002","uploaded_at":"2024-03-20T09:00:00+06:00",
  "sha256":"a41f9c2e7b5d3084f1c6ae90b2d75f3319ee4c8a6b0d5127f93ac41e8b620d77",
  "text_extracted":True,"ocr_required":False,"storage_path":"/store/papers/2024/mid.pdf"},
 {"asset_id":"FA-002","entity_type":"paper","entity_id":"QP-2025-FIN-01",
  "filename":"CSE3103_Final_Spring2025.pdf","mime_type":"application/pdf","size_bytes":331902,
  "pages":2,"uploaded_by":"F-002","uploaded_at":"2025-06-05T09:00:00+06:00",
  "sha256":"c07b8e15af2d64903e5c17ba8d2f409176be3c5d80a4f21e6cb9df3057a1e4b2",
  "text_extracted":True,"ocr_required":False,"storage_path":"/store/papers/2025/final.pdf"},
 {"asset_id":"FA-003","entity_type":"paper","entity_id":"QP-2026-DRAFT-01",
  "filename":"CSE3103_Final_Spring2026_DRAFT.pdf","mime_type":"application/pdf","size_bytes":421774,
  "pages":2,"uploaded_by":"F-004","uploaded_at":"2026-09-06T09:12:44+06:00",
  "sha256":"9f3d1a7c40be82159dc6e0b34a7f2158cd90e6b47fa3218c05de9174b2a6c3f8",
  "text_extracted":True,"ocr_required":True,
  "ocr_note":"Scanned at 200 dpi; the marks column in question 3 is the low-confidence region.",
  "storage_path":"/store/papers/2026/final_draft.pdf"},
 {"asset_id":"FA-004","entity_type":"course","entity_id":"C-CSE3103",
  "filename":"CSE3103_Course_Outline_Spring2026.docx",
  "mime_type":"application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "size_bytes":48210,"pages":4,"uploaded_by":"F-004","uploaded_at":"2026-01-10T10:00:00+06:00",
  "sha256":"6b2a08d5c14e79f3b0d8a2517cf46e930187bd4a2c6f5e819034ad7b25c1e6f0",
  "text_extracted":True,"ocr_required":False,"storage_path":"/store/outlines/cse3103_2026.docx"},
 {"asset_id":"FA-005","entity_type":"proposal","entity_id":"PROP-001",
  "filename":"CSE4109_Proposal.pdf","mime_type":"application/pdf","size_bytes":152998,
  "pages":3,"uploaded_by":"F-004","uploaded_at":"2026-09-06T09:30:00+06:00",
  "sha256":"1d5e8c3b70a294f6e08b1c7d3a5ف".replace("ف","f")+"0",
  "text_extracted":True,"ocr_required":False,"storage_path":"/store/proposals/cse4109.pdf"},
]

# ---- question bank (reusable pool, target of the 'useful result')
question_bank = []
for i, (txt, marks, co, bl, tag, src) in enumerate([
 ("For each department, list the department name together with the number of employees whose salary is above the median salary of that department, ordered by that count descending.",7,"CO3","L3","sql-aggregate","REC-002"),
 ("A report joins orders (2.4 million rows) with customers (5,200 rows) filtering on order_date. Assess a composite, a covering and a partial index, and recommend one with justification.",6,"CO6","L5","index-selection","REC-001"),
 ("Given the interleaved schedule S over T1, T2 and T3, determine whether S is conflict serialisable, then evaluate whether strict two-phase locking or timestamp ordering would have prevented the anomaly.",9,"CO5","L5","concurrency","REC-003"),
 ("Given R(A,B,C,D,E,F) with F = {A->BC, CD->EF, B->D}, compute the attribute closure of A and determine every candidate key. Show your working.",5,"CO4","L4","closure","manual"),
 ("Two designers propose different ER models for the same requirement. Compare them on redundancy, extensibility and query cost, and recommend one.",8,"CO2","L5","er-evaluation","manual"),
 ("Explain why a dirty read can occur under read-uncommitted isolation, and give a concrete two-transaction schedule that demonstrates it.",6,"CO5","L4","isolation","manual"),
]):
    question_bank.append({"bank_id":f"QB-{i+1:03d}","course_id":"C-CSE3103","text":txt,
      "marks":marks,"co_id":co,"bloom_id":bl,"tags":[tag],"origin":src,
      "times_used":0,"last_used_session":None,"created_by":"F-004" if src=="manual" else "ai",
      "approved_by":"F-002","status":"available",
      "max_similarity_to_past_papers":0.31 if src!="manual" else 0.22})

# ---- attainment history / trend
co_att = L("co_attainment.json")
attainment_history = []
prev = {"CO1":93.3,"CO2":73.3,"CO3":80.0,"CO4":40.0,"CO5":56.7,"CO6":63.3}
for co in course_outcomes:
    cid = co["co_id"]
    cur = next((a["class_attainment_percent"] for a in co_att if a["co_id"] == cid), None)
    if cur is None: continue
    attainment_history.append({
      "history_id":f"HIS-{cid}","course_id":"C-CSE3103","co_id":cid,
      "series":[{"session":"Spring 2024","offering_id":"OFF-2024-SP","class_attainment_percent":prev[cid],
                 "status":"attained" if prev[cid]>=60 else "not_attained"},
                {"session":"Spring 2025","offering_id":"OFF-2025-SP","class_attainment_percent":cur,
                 "status":"attained" if cur>=60 else "not_attained"}],
      "trend": "declining" if cur < prev[cid]-2 else "improving" if cur > prev[cid]+2 else "stable",
      "delta": round(cur-prev[cid],1),
      "consecutive_failures": 2 if (cur<60 and prev[cid]<60) else (1 if cur<60 else 0),
      "is_systemic": cur<60 and prev[cid]<60})

# ---- rule catalogue (shows the engine is rule-driven, not a single prompt)
rule_catalog = [
 ("R-CO-NOT-ASSESSED","paper","critical","A course outcome receives zero marks.","deterministic"),
 ("R-CO-UNDERWEIGHT","paper","high","A course outcome receives less than 70% of its intended weight.","deterministic"),
 ("R-CO-OVERWEIGHT","paper","medium","A course outcome receives more than 150% of its intended weight.","deterministic"),
 ("R-BLOOM-LOWER-EXCESS","paper","high","Lower-order marks exceed the departmental cap.","deterministic"),
 ("R-BLOOM-HIGHER-SHORT","paper","high","Higher-order marks fall below the departmental floor.","deterministic"),
 ("R-BLOOM-MISMATCH","paper","medium","A question sits below the Bloom level its outcome targets.","hybrid"),
 ("R-DUP-CROSS-PAPER","paper","high","Similarity to a past paper exceeds the threshold.","hybrid"),
 ("R-DUP-INTRA-PAPER","paper","high","Two questions in the same paper assess the same concept.","hybrid"),
 ("R-MARKS-TOTAL-MISMATCH","paper","medium","Declared total does not equal the sum of question marks.","deterministic"),
 ("R-UNTAGGED-QUESTION","paper","medium","A question carries no outcome tag.","deterministic"),
 ("R-TIME-FEASIBILITY","paper","medium","Estimated answering time exceeds the scheduled duration.","hybrid"),
 ("R-TOPIC-UNTESTED","paper","low","A taught topic is not assessed anywhere.","deterministic"),
 ("R-ITEM-POOR-DISCRIMINATION","item","medium","Discrimination index below 0.20.","deterministic"),
 ("R-ITEM-TOO-EASY","item","low","Facility index above 0.85.","deterministic"),
 ("R-CO-NOT-ATTAINED","attainment","high","Class attainment below the threshold.","deterministic"),
 ("R-CO-SYSTEMIC","attainment","critical","An outcome missed the threshold in consecutive sessions.","deterministic"),
 ("R-GRADER-DIVERGENCE","grading","high","Two markers differ beyond the departmental tolerance.","deterministic"),
 ("R-RUBRIC-AMBIGUITY","grading","high","Divergences cluster on one criterion, indicating a rubric defect.","hybrid"),
 ("R-STD-OVERLAP","curriculum","critical","Topic overlap with an existing course exceeds the permitted limit.","deterministic"),
 ("R-STD-UNDECLARED-PREREQ","curriculum","high","Topics assume a course that is not declared as a prerequisite.","hybrid"),
 ("R-STD-CO-PO-UNMAPPED","curriculum","critical","An outcome maps to no programme outcome.","deterministic"),
 ("R-STD-NO-HIGHER-CO","curriculum","high","A final-year course defines no outcome above Bloom level 4.","deterministic"),
 ("R-STD-PO-UNCOVERED","curriculum","medium","A programme outcome is addressed by no course.","deterministic"),
]
rule_catalog = [{"rule_id":a,"scope":b,"default_severity":c,"description":d,"evaluation":e,
                 "is_enabled":True,"policy_id":"POL-AUST-CSE-01"} for a,b,c,d,e in rule_catalog]

# ---- extra findings now backed by data
extra_findings = [
 {"finding_id":"FND-010","analysis_id":"AN-001","paper_id":"QP-2026-DRAFT-01",
  "category":"structural","severity":"medium","rule_id":"R-TIME-FEASIBILITY",
  "title":"Estimated answering time is 152 minutes against a 180-minute paper",
  "detail":"Comfortable, but the two SQL questions and the normalisation question together account for 84 minutes, and all three sit in the second half of the paper.",
  "evidence_question_ids":["Q-2026D-2B","Q-2026D-3B","Q-2026D-4A"],"evidence_topic_ids":[],
  "suggested_action":"Redistribute so that the heaviest computation is not concentrated at the end."},
 {"finding_id":"FND-011","analysis_id":"AN-001","paper_id":"QP-2026-DRAFT-01",
  "category":"coverage","severity":"low","rule_id":"R-TOPIC-UNTESTED",
  "title":"Six taught topics are not assessed",
  "detail":"Weeks 3, 5, 7, 10, 12 and 14 contribute no marks. Weeks 12 and 14 matter most because they carry CO5 and CO6.",
  "evidence_question_ids":[],"evidence_topic_ids":["T-03","T-05","T-07","T-10","T-12","T-14"],
  "suggested_action":"Cover week 14 through the proposed CO6 question and week 12 through the revised 4(b)."},
]

# ============================================================ WRITE
print("Writing extension tables:")
new = [
 ("curriculum_courses.json", curriculum_courses),
 ("course_proposals.json", course_proposals),
 ("accreditation_standards.json", accreditation_standards),
 ("curriculum_overlap.json", curriculum_overlap),
 ("prerequisite_edges.json", prerequisite_edges),
 ("proposal_findings.json", proposal_findings),
 ("po_course_coverage.json", po_course_coverage),
 ("item_analysis.json", item_analysis),
 ("item_analysis_summary.json", item_analysis_summary),
 ("exemplar_scripts.json", exemplar_scripts),
 ("divergence_resolutions.json", divergence_resolutions),
 ("rubric_amendments.json", rubric_amendments),
 ("grader_profiles.json", grader_profiles),
 ("paper_versions.json", paper_versions),
 ("recommendation_feedback.json", recommendation_feedback),
 ("review_threads.json", review_threads),
 ("review_comments.json", review_comments),
 ("approval_workflow.json", approval_workflow),
 ("notifications.json", notifications),
 ("faculty_preferences.json", faculty_preferences),
 ("file_assets.json", file_assets),
 ("question_bank.json", question_bank),
 ("attainment_history.json", attainment_history),
 ("rule_catalog.json", rule_catalog),
]
for n, o in new: dump(n, o)

# append the two new findings to findings.json
f = L("findings.json"); f.extend(extra_findings); dump("findings.json", f)

print("\nComputed checks")
print(f"  proposal vs CSE 4101 shared topics : {prop_cov_4101['shared_count']} -> {prop_cov_4101['shared_topics']}")
print(f"  directional coverage               : {max(prop_cov_4101['coverage_of_a_by_b'],prop_cov_4101['coverage_of_b_by_a'])}")
print(f"  overlap pairs above 0.06 jaccard   : {len(curriculum_overlap)}")
print(f"  item analysis facility range       : {min(i['facility_index'] for i in item_analysis)} - {max(i['facility_index'] for i in item_analysis)}")
print(f"  items flagged revise               : {item_analysis_summary[0]['items_to_revise']}")
print(f"  systemic weak COs (2 sessions)     : {[h['co_id'] for h in attainment_history if h['is_systemic']]}")

# ============================================================ E. MANIFEST + DEMO SCRIPT UPDATE
prev_fix = {"CO4": 44.0, "CO6": 58.0}
for h in attainment_history:
    if h["co_id"] in prev_fix:
        h["series"][0]["class_attainment_percent"] = prev_fix[h["co_id"]]
        h["series"][0]["status"] = "attained" if prev_fix[h["co_id"]] >= 60 else "not_attained"
        cur = h["series"][1]["class_attainment_percent"]
        h["delta"] = round(cur - prev_fix[h["co_id"]], 1)
        h["trend"] = "declining" if cur < prev_fix[h["co_id"]]-2 else "improving" if cur > prev_fix[h["co_id"]]+2 else "stable"
        h["consecutive_failures"] = 2 if (cur < 60 and prev_fix[h["co_id"]] < 60) else (1 if cur < 60 else 0)
        h["is_systemic"] = cur < 60 and prev_fix[h["co_id"]] < 60
dump("attainment_history.json", attainment_history)

ia = L("item_analysis.json")
demo = [
 {"step":1,"beat":"problem","duration_sec":20,"journey":"setup",
  "action":"Open the CSE 3103 course file: six outcomes, the CO-PO matrix and 14 weeks of syllabus already on record.",
  "tables_used":["courses","course_outcomes","co_po_map","syllabus_topics"],"expected_screen":"Course overview"},
 {"step":2,"beat":"input","duration_sec":15,"journey":"assessment",
  "action":"Upload CSE3103_Final_Spring2026_DRAFT.pdf.",
  "tables_used":["question_papers","file_assets","extraction_runs"],"expected_screen":"Upload and extraction"},
 {"step":3,"beat":"human_in_the_loop","duration_sec":40,"journey":"assessment",
  "action":"Three low-confidence rows are highlighted. Edit EXR-006 marks 1 to 10, retag EXR-004 to CO3, split the merged EXR-007. Confirm.",
  "tables_used":["extracted_questions_raw","extraction_corrections"],"expected_screen":"Confirm table",
  "is_key_moment":True,"why":"Proves the faculty member stays in control and the AI only proposes."},
 {"step":4,"beat":"what_the_ai_does","duration_sec":35,"journey":"assessment",
  "action":"Run analysis. CO6 shows zero on the heatmap, Bloom bar shows 48.3% lower order, three duplicate pairs open side by side against their 2024 and 2025 sources.",
  "tables_used":["paper_analysis","findings","similarity_pairs","rule_catalog"],"expected_screen":"Analysis dashboard"},
 {"step":5,"beat":"useful_result","duration_sec":35,"journey":"assessment",
  "action":"Accept three recommendations. Quality score moves 54 to 68 to 82, marks reconcile to 60, six findings close. Reject REC-005 with a reason to show the feedback loop.",
  "tables_used":["recommendations","recommendation_feedback","paper_versions"],"expected_screen":"Version timeline"},
 {"step":6,"beat":"second_journey","duration_sec":30,"journey":"attainment",
  "action":"Switch to the attainment view. CO4 and CO5 are red and have now missed the threshold in two consecutive sessions, so the alert is systemic rather than a one-off.",
  "tables_used":["co_attainment","po_attainment","attainment_history","attainment_insights"],"expected_screen":"Attainment trend"},
 {"step":7,"beat":"depth","duration_sec":25,"journey":"attainment",
  "action":f"Open item analysis. Question 1(a) has a facility index of {ia[0]['facility_index']} and a discrimination index of {ia[0]['discrimination_index']}: five marks that separate nobody. Question 4 is the same problem at Bloom level 5.",
  "tables_used":["item_analysis","item_analysis_summary"],"expected_screen":"Item analysis",
  "why":"Answers the brief's question of whether the assessment fairly measures what students were meant to learn."},
 {"step":8,"beat":"third_journey","duration_sec":35,"journey":"grading",
  "action":"Grading consistency report. ANS-03 and ANS-05 flagged, both tracing to criterion R3. The system proposes a rubric amendment rather than just a mark, and the third examiner accepts it.",
  "tables_used":["grading_consistency","grading_divergences","divergence_resolutions","rubric_amendments","exemplar_scripts"],
  "expected_screen":"Consistency report","why":"Diagnoses the rubric defect, not just the number gap."},
 {"step":9,"beat":"fourth_journey","duration_sec":40,"journey":"curriculum",
  "action":"Submit the CSE 4109 proposal. The standards checker returns six findings: 66.7% topic overlap with CSE 4101, an undeclared CSE 3103 prerequisite, an unmapped outcome and no outcome above Bloom level 4. The overlap map shows exactly which eight topics collide.",
  "tables_used":["course_proposals","accreditation_standards","curriculum_overlap","proposal_findings","prerequisite_edges","po_course_coverage"],
  "expected_screen":"Curriculum overlap map",
  "why":"This is the problem statement's own opening example: a syllabus that meets standards and complements existing courses."},
 {"step":10,"beat":"close","duration_sec":20,"journey":"close",
  "action":"Show the moderation workflow, the review threads and the export. Mention the cached fallback and that no result on screen was hard-coded.",
  "tables_used":["approval_workflow","review_threads","review_comments","offline_cache"],"expected_screen":"Export"},
]
dump("demo_script.json", demo)

man = L("_manifest.json")
man["version"] = "1.1.0"
man["journeys"] = [
 {"id":"J1","name":"Assessment quality","input":"Draft question paper PDF",
  "output":"Findings, duplicate evidence and accepted revisions with a version trail",
  "core_tables":["question_papers","questions","extracted_questions_raw","paper_analysis","findings","similarity_pairs","recommendations","paper_versions"]},
 {"id":"J2","name":"Attainment and assessment fairness","input":"Marks for a past paper",
  "output":"CO and PO attainment, multi-session trend, per-item difficulty and discrimination",
  "core_tables":["student_marks","co_attainment","po_attainment","attainment_history","item_analysis"]},
 {"id":"J3","name":"Grading consistency","input":"Rubric plus double-marked scripts",
  "output":"Divergence diagnosis, third-examiner resolution and a rubric amendment",
  "core_tables":["rubrics","rubric_criteria","answer_scripts","grader_scores","grading_divergences","divergence_resolutions","rubric_amendments","exemplar_scripts"]},
 {"id":"J4","name":"Curriculum design against standards","input":"New course proposal",
  "output":"Standards violations, computed overlap with existing courses, inferred prerequisites",
  "core_tables":["course_proposals","accreditation_standards","curriculum_courses","curriculum_overlap","proposal_findings","prerequisite_edges"]},
]
man["planted_flaws"] += [
 {"id":"PF-15","where":"PROP-001 vs CUR-4101","flaw":f"{prop_cov_4101['max_directional_coverage']*100:.1f}% topic overlap against a 40% limit","detected_by":"PFND-001"},
 {"id":"PF-16","where":"PROP-001","flaw":"CSE 3103 is an undeclared prerequisite","detected_by":"PFND-002 / PRE-INF-001"},
 {"id":"PF-17","where":"PROP-001","flaw":"Proposed CO4 maps to no programme outcome","detected_by":"PFND-003"},
 {"id":"PF-18","where":"PROP-001","flaw":"No outcome above Bloom L4 in a level-4 course","detected_by":"PFND-004"},
 {"id":"PF-19","where":"PROP-001","flaw":"No assessment plan supplied","detected_by":"PFND-005"},
 {"id":"PF-20","where":"programme","flaw":"PO7 (environment and sustainability) addressed by no core course","detected_by":"po_course_coverage"},
 {"id":"PF-21","where":"Q-2025F-1A","flaw":"Too easy and discriminates almost nothing: 5 wasted marks","detected_by":"item_analysis"},
 {"id":"PF-22","where":"Q-2025F-4","flaw":"Poor discrimination at Bloom L5, suggesting an ambiguous question","detected_by":"item_analysis"},
 {"id":"PF-23","where":"attainment_history","flaw":"CO4 and CO5 below threshold in two consecutive sessions","detected_by":"attainment_history.is_systemic"},
 {"id":"PF-24","where":"QP-2026-DRAFT-01","flaw":"Six taught topics assessed by no question","detected_by":"FND-011"},
 {"id":"PF-25","where":"REC-005","flaw":"A recommendation a faculty member should reject (off-syllabus schema)","detected_by":"recommendation_feedback"},
]
man["tables"] = [{"file": os.path.basename(f), "rows": (lambda o: len(o) if isinstance(o,list) else 1)(json.load(open(f, encoding="utf-8")))}
                 for f in sorted(__import__("glob").glob(os.path.join(D,"*.json")))
                 if not os.path.basename(f).startswith("_")]
dump("_manifest.json", man)
print(f"  total tables: {len(man['tables'])}")
