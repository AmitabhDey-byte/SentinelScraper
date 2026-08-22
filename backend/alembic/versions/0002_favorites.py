"""Add per-user saved products.

Revision ID: 0002_favorites
Revises: 0001_initial_schema
"""

from alembic import op
import sqlalchemy as sa


revision = "0002_favorites"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "favorites",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("product_id_fk", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id_fk"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_favorites_user_product", "favorites", ["user_id", "product_id_fk"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_favorites_user_product", table_name="favorites")
    op.drop_table("favorites")
