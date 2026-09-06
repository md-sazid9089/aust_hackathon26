"""tier 1 artefact data: marks_columns, marks_rows, rubric_criteria, answers

Revision ID: b2d4f6a8c0e2
Revises: a1c3e5f7b9d1
Create Date: 2026-09-06 14:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "b2d4f6a8c0e2"
down_revision: str | None = "a1c3e5f7b9d1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

JSON_COL = sa.JSON().with_variant(JSONB(), "postgresql")
MARKS = sa.Numeric(6, 2)
TS = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "marks_columns",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artefact_id", sa.Uuid(), nullable=False),
        sa.Column("number", sa.Text(), nullable=False),
        sa.Column("max_marks", MARKS, nullable=False),
        sa.Column("co_code", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("max_marks >= 0", name="ck_marks_columns_max"),
        sa.ForeignKeyConstraint(["artefact_id"], ["artefacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artefact_id", "number", name="uq_marks_columns_artefact_number"),
    )
    op.create_table(
        "marks_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artefact_id", sa.Uuid(), nullable=False),
        sa.Column("student_anon_id", sa.Text(), nullable=False),
        sa.Column("scores", JSON_COL, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["artefact_id"], ["artefacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artefact_id", "student_anon_id", name="uq_marks_rows_artefact_student"),
    )
    op.create_index("ix_marks_rows_artefact", "marks_rows", ["artefact_id"])
    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artefact_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("max_score", MARKS, nullable=False),
        sa.Column("levels", JSON_COL, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.CheckConstraint("max_score > 0", name="ck_rubric_criteria_max"),
        sa.ForeignKeyConstraint(["artefact_id"], ["artefacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("artefact_id", "code", name="uq_rubric_criteria_artefact_code"),
    )
    op.create_table(
        "answers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("artefact_id", sa.Uuid(), nullable=False),
        sa.Column("student_anon_id", sa.Text(), nullable=False),
        sa.Column("question_ref", sa.Text(), nullable=True),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("grader_scores", JSON_COL, nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", TS, nullable=False),
        sa.Column("updated_at", TS, nullable=False),
        sa.ForeignKeyConstraint(["artefact_id"], ["artefacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_answers_artefact_order", "answers", ["artefact_id", "sort_order"])


def downgrade() -> None:
    op.drop_index("ix_answers_artefact_order", table_name="answers")
    op.drop_table("answers")
    op.drop_table("rubric_criteria")
    op.drop_index("ix_marks_rows_artefact", table_name="marks_rows")
    op.drop_table("marks_rows")
    op.drop_table("marks_columns")
