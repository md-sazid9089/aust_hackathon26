from __future__ import annotations

import enum


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:  # pragma: no cover
        return self.value


class AppRole(StrEnum):
    faculty = "faculty"
    admin = "admin"


class ArtefactKind(StrEnum):
    syllabus = "syllabus"
    question_paper = "question_paper"
    marks_sheet = "marks_sheet"
    rubric = "rubric"
    answer_set = "answer_set"


# Kinds whose extraction pipeline exists in this build (Tier 0).
SUPPORTED_ARTEFACT_KINDS = {ArtefactKind.syllabus, ArtefactKind.question_paper}


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


IMPLEMENTED_MODULES = {RunModule.exam_audit}


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
