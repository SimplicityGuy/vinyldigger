"""Initial database schema

Revision ID: initial
Revises:
Create Date: 2025-01-10 12:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "initial"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE apiservice AS ENUM ('DISCOGS', 'EBAY')")
    op.execute("CREATE TYPE oauthprovider AS ENUM ('DISCOGS', 'EBAY')")
    op.execute("CREATE TYPE searchplatform AS ENUM ('DISCOGS', 'EBAY', 'BOTH')")
    op.execute("CREATE TYPE searchstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')")

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    # Create app_config table
    op.create_table(
        "app_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider", postgresql.ENUM("DISCOGS", "EBAY", name="oauthprovider", create_type=False), nullable=False
        ),
        sa.Column("consumer_key", sa.String(length=500), nullable=False),
        sa.Column("consumer_secret", sa.String(length=500), nullable=False),
        sa.Column("callback_url", sa.String(length=500), nullable=True),
        sa.Column("redirect_uri", sa.String(length=500), nullable=True),
        sa.Column("scope", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider"),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service", postgresql.ENUM("DISCOGS", "EBAY", name="apiservice", create_type=False), nullable=False),
        sa.Column("encrypted_key", sa.String(length=500), nullable=False),
        sa.Column("encrypted_secret", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "service"),
    )

    # Create oauth_tokens table
    op.create_table(
        "oauth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider", postgresql.ENUM("DISCOGS", "EBAY", name="oauthprovider", create_type=False), nullable=False
        ),
        sa.Column("access_token", sa.String(length=500), nullable=False),
        sa.Column("access_token_secret", sa.String(length=500), nullable=True),
        sa.Column("refresh_token", sa.String(length=500), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_user_id", sa.String(length=255), nullable=True),
        sa.Column("provider_username", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "provider"),
    )

    # Create saved_searches table
    op.create_table(
        "saved_searches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("query", sa.String(length=500), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("DISCOGS", "EBAY", "BOTH", name="searchplatform", create_type=False),
            nullable=False,
        ),
        sa.Column("filters", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("min_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("max_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("check_interval_hours", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("min_record_condition", sa.String(length=10), nullable=True),
        sa.Column("min_sleeve_condition", sa.String(length=10), nullable=True),
        sa.Column("seller_location_preference", sa.String(length=10), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_saved_searches_next_run_at"), "saved_searches", ["next_run_at"], unique=False)
    op.create_index(op.f("ix_saved_searches_user_id"), "saved_searches", ["user_id"], unique=False)

    # Create search_results table
    op.create_table(
        "search_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("DISCOGS", "EBAY", "BOTH", name="searchplatform", create_type=False),
            nullable=False,
        ),
        sa.Column("platform_item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("artist", sa.String(length=255), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("condition", sa.String(length=50), nullable=True),
        sa.Column("media_condition", sa.String(length=50), nullable=True),
        sa.Column("sleeve_condition", sa.String(length=50), nullable=True),
        sa.Column("seller", sa.String(length=255), nullable=True),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("image_url", sa.String(length=1000), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("in_collection", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("in_wantlist", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("found_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_id"],
            ["saved_searches.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("search_id", "platform", "platform_item_id"),
    )
    op.create_index(op.f("ix_search_results_found_at"), "search_results", ["found_at"], unique=False)
    op.create_index(op.f("ix_search_results_price"), "search_results", ["price"], unique=False)
    op.create_index(op.f("ix_search_results_search_id"), "search_results", ["search_id"], unique=False)

    # Create search_runs table
    op.create_table(
        "search_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("PENDING", "RUNNING", "COMPLETED", "FAILED", name="searchstatus", create_type=False),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("results_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_id"],
            ["saved_searches.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_search_runs_search_id"), "search_runs", ["search_id"], unique=False)
    op.create_index(op.f("ix_search_runs_started_at"), "search_runs", ["started_at"], unique=False)

    # Create collections table
    op.create_table(
        "collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("DISCOGS", "EBAY", "BOTH", name="searchplatform", create_type=False),
            nullable=False,
        ),
        sa.Column("platform_collection_id", sa.String(length=255), nullable=True),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "platform"),
    )

    # Create collection_items table
    op.create_table(
        "collection_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("collection_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("artist", sa.String(length=255), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(length=50), nullable=True),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("catalog_number", sa.String(length=255), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["collections.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_id", "platform_item_id"),
    )
    op.create_index(op.f("ix_collection_items_collection_id"), "collection_items", ["collection_id"], unique=False)

    # Create want_lists table
    op.create_table(
        "want_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("DISCOGS", "EBAY", "BOTH", name="searchplatform", create_type=False),
            nullable=False,
        ),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "platform"),
    )

    # Create want_list_items table
    op.create_table(
        "want_list_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("want_list_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform_item_id", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("artist", sa.String(length=255), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("format", sa.String(length=50), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["want_list_id"],
            ["want_lists.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("want_list_id", "platform_item_id"),
    )
    op.create_index(op.f("ix_want_list_items_want_list_id"), "want_list_items", ["want_list_id"], unique=False)

    # Create price_history table
    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["result_id"],
            ["search_results.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_history_observed_at"), "price_history", ["observed_at"], unique=False)
    op.create_index(op.f("ix_price_history_result_id"), "price_history", ["result_id"], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f("ix_price_history_result_id"), table_name="price_history")
    op.drop_index(op.f("ix_price_history_observed_at"), table_name="price_history")
    op.drop_table("price_history")

    op.drop_index(op.f("ix_want_list_items_want_list_id"), table_name="want_list_items")
    op.drop_table("want_list_items")
    op.drop_table("want_lists")

    op.drop_index(op.f("ix_collection_items_collection_id"), table_name="collection_items")
    op.drop_table("collection_items")
    op.drop_table("collections")

    op.drop_index(op.f("ix_search_runs_started_at"), table_name="search_runs")
    op.drop_index(op.f("ix_search_runs_search_id"), table_name="search_runs")
    op.drop_table("search_runs")

    op.drop_index(op.f("ix_search_results_search_id"), table_name="search_results")
    op.drop_index(op.f("ix_search_results_price"), table_name="search_results")
    op.drop_index(op.f("ix_search_results_found_at"), table_name="search_results")
    op.drop_table("search_results")

    op.drop_index(op.f("ix_saved_searches_user_id"), table_name="saved_searches")
    op.drop_index(op.f("ix_saved_searches_next_run_at"), table_name="saved_searches")
    op.drop_table("saved_searches")

    op.drop_table("oauth_tokens")
    op.drop_table("api_keys")
    op.drop_table("app_config")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS searchstatus")
    op.execute("DROP TYPE IF EXISTS searchplatform")
    op.execute("DROP TYPE IF EXISTS oauthprovider")
    op.execute("DROP TYPE IF EXISTS apiservice")
