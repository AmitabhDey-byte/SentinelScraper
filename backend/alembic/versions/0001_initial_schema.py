"""Create SentinelScrape persistence schema.

Revision ID: 0001_initial_schema
Revises:
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "collectors",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collector_id", sa.String(length=128), nullable=False, unique=True),
        sa.Column("site_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("collector_id"),
    )
    op.create_table(
        "runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collector_id_fk", sa.Integer(), nullable=False),
        sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("row_count", sa.Integer(), nullable=False),
        sa.Column("raw_json_ref", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["collector_id_fk"], ["collectors.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_runs_collector_run_at", "runs", ["collector_id_fk", "run_at"], unique=False)

    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collector_id_fk", sa.Integer(), nullable=False),
        sa.Column("external_key", sa.String(length=512), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["collector_id_fk"], ["collectors.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_products_collector_external_key", "products", ["collector_id_fk", "external_key"], unique=True)

    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id_fk", sa.Integer(), nullable=False),
        sa.Column("price", sa.Float(), nullable=True),
        sa.Column("stock_status", sa.String(length=128), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id_fk"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_price_history_product_observed_at", "price_history", ["product_id_fk", "observed_at"], unique=False)

    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("collector_id_fk", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("dropped_fields", sa.JSON(), nullable=False),
        sa.Column("recovered_fields", sa.JSON(), nullable=False),
        sa.Column("rows_prev", sa.Integer(), nullable=False),
        sa.Column("rows_curr", sa.Integer(), nullable=False),
        sa.Column("healed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("narration_text", sa.Text(), nullable=True),
        sa.Column("narration_source", sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(["collector_id_fk"], ["collectors.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_incidents_collector_detected_at", "incidents", ["collector_id_fk", "detected_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_incidents_collector_detected_at", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_price_history_product_observed_at", table_name="price_history")
    op.drop_table("price_history")
    op.drop_index("ix_products_collector_external_key", table_name="products")
    op.drop_table("products")
    op.drop_index("ix_runs_collector_run_at", table_name="runs")
    op.drop_table("runs")
    op.drop_table("collectors")
