from __future__ import annotations

import enum


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover
        return self.value


class AppRole(StrEnum):
    faculty = "faculty"
    admin = "admin"


class Permission(StrEnum):
    """Dashboards (`dashboard:*`) and actions a role may use. Persisted in `role_permissions`."""

    dashboard_courses = "dashboard:courses"
    dashboard_course_workspace = "dashboard:course_workspace"
    dashboard_exam_audit = "dashboard:exam_audit"
    dashboard_attainment = "dashboard:attainment"
    dashboard_syllabus_check = "dashboard:syllabus_check"
    dashboard_calibration = "dashboard:calibration"
    dashboard_overview = "dashboard:overview"
    dashboard_admin = "dashboard:admin"
    dashboard_admin_department = "dashboard:admin_department"
    courses_write = "courses:write"
    artefacts_write = "artefacts:write"
    runs_start = "runs:start"
    findings_decide = "findings:decide"
    demo_seed = "demo:seed"
    admin_users = "admin:users"
    admin_runs = "admin:runs"
    admin_usage = "admin:usage"


# Role → permissions. Faculty own and decide; admins are read-only oversight (SEC-009).
ROLE_PERMISSIONS: dict[AppRole, frozenset[Permission]] = {
    AppRole.faculty: frozenset(
        {
            Permission.dashboard_courses,
            Permission.dashboard_course_workspace,
            Permission.dashboard_exam_audit,
            Permission.dashboard_attainment,
            Permission.dashboard_syllabus_check,
            Permission.dashboard_calibration,
            Permission.dashboard_overview,
            Permission.courses_write,
            Permission.artefacts_write,
            Permission.runs_start,
            Permission.findings_decide,
            Permission.demo_seed,
        }
    ),
    AppRole.admin: frozenset(
        {
            Permission.dashboard_courses,
            Permission.dashboard_course_workspace,
            Permission.dashboard_exam_audit,
            Permission.dashboard_attainment,
            Permission.dashboard_syllabus_check,
            Permission.dashboard_calibration,
            Permission.dashboard_overview,
            Permission.dashboard_admin,
            Permission.dashboard_admin_department,
            Permission.admin_users,
            Permission.admin_runs,
            Permission.admin_usage,
        }
    ),
}


class ArtefactKind(StrEnum):
    syllabus = "syllabus"
    question_paper = "question_paper"
    marks_sheet = "marks_sheet"
    rubric = "rubric"
    answer_set = "answer_set"


# Kinds whose extraction pipeline exists in this build.
SUPPORTED_ARTEFACT_KINDS = set(ArtefactKind)

# Which artefact kind each run-input role must reference.
ROLE_KINDS: dict[str, ArtefactKind] = {
    "draft": ArtefactKind.question_paper,
    "past": ArtefactKind.question_paper,
    "paper": ArtefactKind.question_paper,
    "marks": ArtefactKind.marks_sheet,
    "syllabus": ArtefactKind.syllabus,
    "rubric": ArtefactKind.rubric,
    "answer_set": ArtefactKind.answer_set,
}


class ExtractionStatus(StrEnum):
    pending = "pending"
    extracting = "extracting"
    done = "done"
    failed = "failed"


class TextLang(StrEnum):
    en = "en"
    bn = "bn"
    mixed = "mixed"
    unknown = "unknown"


class BloomLevel(StrEnum):
    remember = "remember"
    understand = "understand"
    apply = "apply"
    analyze = "analyze"
    evaluate = "evaluate"
    create = "create"


BLOOM_ORDER: dict[BloomLevel, int] = {b: i + 1 for i, b in enumerate(BloomLevel)}
LOWER_ORDER_BLOOM = {BloomLevel.remember, BloomLevel.understand}
HIGHER_ORDER_BLOOM = {BloomLevel.analyze, BloomLevel.evaluate, BloomLevel.create}


class MapSource(StrEnum):
    ai = "ai"
    faculty = "faculty"


class RunModule(StrEnum):
    exam_audit = "exam_audit"
    attainment = "attainment"
    syllabus_check = "syllabus_check"
    calibration = "calibration"


IMPLEMENTED_MODULES = set(RunModule)


class RunStatus(StrEnum):
    queued = "queued"
    analyzing = "analyzing"
    completed = "completed"
    partial = "partial"
    failed = "failed"


TERMINAL_RUN_STATUSES = {RunStatus.completed, RunStatus.partial, RunStatus.failed}


class FindingSeverity(StrEnum):
    info = "info"
    low = "low"
    medium = "medium"
    high = "high"


SEVERITY_ORDER: dict[str, int] = {"info": 0, "low": 1, "medium": 2, "high": 3}


class FindingStatus(StrEnum):
    open = "open"
    accepted = "accepted"
    dismissed = "dismissed"


class TargetKind(StrEnum):
    question = "question"
    course_outcome = "course_outcome"
    program_outcome = "program_outcome"
    topic = "topic"
    answer = "answer"
    criterion = "criterion"
    course = "course"
    none = "none"


class FindingType(StrEnum):
    coverage_gap = "coverage_gap"
    overweight = "overweight"
    bloom_imbalance = "bloom_imbalance"
    duplicate = "duplicate"
    fairness = "fairness"
    marks_total_mismatch = "marks_total_mismatch"
    untagged_question = "untagged_question"
    suggestion = "suggestion"
    co_underperformance = "co_underperformance"
    po_underperformance = "po_underperformance"
    action = "action"
    overlap = "overlap"
    prerequisite_gap = "prerequisite_gap"
    missing_topic = "missing_topic"
    repositioning = "repositioning"
    divergence = "divergence"
    prescore_note = "prescore_note"
    rubric_clarification = "rubric_clarification"


class UsagePurpose(StrEnum):
    extraction = "extraction"
    exam_audit = "exam_audit"
    attainment = "attainment"
    syllabus_check = "syllabus_check"
    calibration = "calibration"
    suggestion = "suggestion"
    embedding = "embedding"
    assistant = "assistant"
