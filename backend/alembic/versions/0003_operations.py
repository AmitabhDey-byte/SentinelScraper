"""Persist self-healing operation evidence.

Revision ID: 0003_operations
Revises: 0002_favorites
"""

from alembic import op
import sqlalchemy as sa


revision = "0003_operations"
down_revision = "0002_favorites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("kind", sa.String(length=48), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("incident_id_fk", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["incident_id_fk"], ["incidents.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_operations_started_at", "operations", ["started_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_operations_started_at", table_name="operations")
    op.drop_table("operations")
