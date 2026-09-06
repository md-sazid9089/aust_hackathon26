"""add must_change_password to profiles

Revision ID: c3e5f7a9b1d2
Revises: b2d4f6a8c0e2
Create Date: 2026-09-06 15:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c3e5f7a9b1d2"
down_revision: str | None = "b2d4f6a8c0e2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(
            sa.Column("must_change_password", sa.Boolean(), server_default=sa.text("false"), nullable=False)
        )


def downgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.drop_column("must_change_password")
