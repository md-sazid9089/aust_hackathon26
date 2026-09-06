"""local auth: profiles.password_hash/last_login_at + role_permissions

Revision ID: a1c3e5f7b9d1
Revises: 07517be42f00
Create Date: 2026-09-06 13:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1c3e5f7b9d1"
down_revision: str | None = "07517be42f00"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("profiles") as batch:
        batch.add_column(sa.Column("password_hash", sa.Text(), nullable=True))
        batch.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.create_table(
        "role_permissions",
        sa.Column("role", sa.Enum("faculty", "admin", name="app_role", native_enum=False, length=32), nullable=False),
        sa.Column("permission", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("role", "permission"),
    )
    # Rows are synced from app.db.enums.ROLE_PERMISSIONS at API startup.


def downgrade() -> None:
    op.drop_table("role_permissions")
    with op.batch_alter_table("profiles") as batch:
        batch.drop_column("last_login_at")
        batch.drop_column("password_hash")
