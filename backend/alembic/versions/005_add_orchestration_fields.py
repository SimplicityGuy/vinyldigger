"""Add orchestration fields to SavedSearch

Revision ID: 005_add_orchestration_fields
Revises: 004_add_orchestration_models
Create Date: 2025-01-18

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "005_add_orchestration_fields"
down_revision = "004_add_orchestration_models"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add new columns to saved_searches table
    op.add_column("saved_searches", sa.Column("status", sa.String(length=50), nullable=True))
    op.add_column("saved_searches", sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("saved_searches", sa.Column("chain_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("saved_searches", sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True))

    # Add foreign key constraints
    op.create_foreign_key("fk_saved_searches_chain_id", "saved_searches", "search_chains", ["chain_id"], ["id"])
    op.create_foreign_key(
        "fk_saved_searches_template_id", "saved_searches", "search_templates", ["template_id"], ["id"]
    )

    # Add indexes for better query performance
    op.create_index("ix_saved_searches_status", "saved_searches", ["status"])
    op.create_index("ix_saved_searches_chain_id", "saved_searches", ["chain_id"])
    op.create_index("ix_saved_searches_template_id", "saved_searches", ["template_id"])


def downgrade() -> None:
    # Remove indexes
    op.drop_index("ix_saved_searches_template_id", table_name="saved_searches")
    op.drop_index("ix_saved_searches_chain_id", table_name="saved_searches")
    op.drop_index("ix_saved_searches_status", table_name="saved_searches")

    # Remove foreign key constraints
    op.drop_constraint("fk_saved_searches_template_id", "saved_searches", type_="foreignkey")
    op.drop_constraint("fk_saved_searches_chain_id", "saved_searches", type_="foreignkey")

    # Remove columns
    op.drop_column("saved_searches", "template_id")
    op.drop_column("saved_searches", "chain_id")
    op.drop_column("saved_searches", "results_count")
    op.drop_column("saved_searches", "status")
