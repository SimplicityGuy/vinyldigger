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
    op.execute("CREATE TYPE apiservice AS ENUM ('discogs', 'ebay')")
    op.execute("CREATE TYPE oauthprovider AS ENUM ('discogs', 'ebay')")
    op.execute("CREATE TYPE oauthenvironment AS ENUM ('production', 'sandbox')")
    op.execute("CREATE TYPE searchplatform AS ENUM ('discogs', 'ebay', 'both')")
    op.execute("CREATE TYPE searchstatus AS ENUM ('PENDING', 'RUNNING', 'COMPLETED', 'FAILED')")
    op.execute(
        "CREATE TYPE recommendationtype AS ENUM "
        "('BEST_PRICE', 'MULTI_ITEM_DEAL', 'CONDITION_VALUE', 'LOCATION_PREFERENCE', 'HIGH_FEEDBACK')"
    )
    op.execute("CREATE TYPE dealscore AS ENUM ('EXCELLENT', 'VERY_GOOD', 'GOOD', 'FAIR', 'POOR')")
    op.execute("CREATE TYPE matchconfidence AS ENUM ('EXACT', 'HIGH', 'MEDIUM', 'LOW', 'UNCERTAIN')")

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
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)

    # Create app_config table
    op.create_table(
        "app_config",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider", postgresql.ENUM("discogs", "ebay", name="oauthprovider", create_type=False), nullable=False
        ),
        sa.Column(
            "environment",
            postgresql.ENUM("production", "sandbox", name="oauthenvironment", create_type=False),
            nullable=False,
            server_default="production",
        ),
        sa.Column("consumer_key", sa.String(length=500), nullable=False),
        sa.Column("consumer_secret", sa.String(length=500), nullable=False),
        sa.Column("callback_url", sa.String(length=500), nullable=True),
        sa.Column("redirect_uri", sa.String(length=500), nullable=True),
        sa.Column("scope", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "environment", name="uq_app_config_provider_environment"),
    )

    # Create api_keys table
    op.create_table(
        "api_keys",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("service", postgresql.ENUM("discogs", "ebay", name="apiservice", create_type=False), nullable=False),
        sa.Column("encrypted_key", sa.String(length=500), nullable=False),
        sa.Column("encrypted_secret", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        # Note: Unique constraint removed per later migration
    )

    # Create oauth_tokens table
    op.create_table(
        "oauth_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "provider", postgresql.ENUM("discogs", "ebay", name="oauthprovider", create_type=False), nullable=False
        ),
        sa.Column("access_token", sa.String(length=5000), nullable=False),
        sa.Column("access_token_secret", sa.String(length=5000), nullable=True),
        sa.Column("refresh_token", sa.String(length=5000), nullable=True),
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
        sa.UniqueConstraint("user_id", "provider", name="unique_user_provider"),
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
            postgresql.ENUM("discogs", "ebay", "both", name="searchplatform", create_type=False),
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
    # Note: ix_saved_searches_user_id index removed per later migration

    # Create search_results table
    op.create_table(
        "search_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("discogs", "ebay", "both", name="searchplatform", create_type=False),
            nullable=False,
        ),
        sa.Column("item_id", sa.String(length=255), nullable=False),
        sa.Column("item_data", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("is_in_collection", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_in_wantlist", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(
            ["search_id"],
            ["saved_searches.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        # Note: Unique constraint removed per later migration
    )
    # Note: ix_search_results_search_id index removed per later migration

    # Note: search_runs table removed per later migration

    # Create collections table
    op.create_table(
        "collections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("discogs", "ebay", "both", name="searchplatform", create_type=False),
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
        sa.Column("item_id", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("collection_id", "item_id"),
    )
    # Note: ix_collection_items_collection_id index removed per later migration

    # Create want_lists table
    op.create_table(
        "want_lists",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("discogs", "ebay", "both", name="searchplatform", create_type=False),
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
        sa.Column("item_id", sa.String(length=255), nullable=False),
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
        sa.UniqueConstraint("want_list_id", "item_id"),
    )
    # Note: ix_want_list_items_want_list_id index removed per later migration

    # Create price_history table
    op.create_table(
        "price_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("item_id", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False, server_default="USD"),
        sa.Column("condition", sa.String(length=50), nullable=True),
        sa.Column("sleeve_condition", sa.String(length=50), nullable=True),
        sa.Column("seller_location", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_price_history_item_id"), "price_history", ["item_id"], unique=False)

    # Create item_matches table
    op.create_table(
        "item_matches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("canonical_title", sa.String(length=500), nullable=False),
        sa.Column("canonical_artist", sa.String(length=255), nullable=False),
        sa.Column("canonical_year", sa.Integer(), nullable=True),
        sa.Column("canonical_format", sa.String(length=50), nullable=True),
        sa.Column("catalog_number", sa.String(length=255), nullable=True),
        sa.Column("discogs_release_id", sa.String(length=255), nullable=True),
        sa.Column("match_fingerprint", sa.String(length=500), nullable=False),
        sa.Column("total_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("avg_confidence_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_item_matches_match_fingerprint"), "item_matches", ["match_fingerprint"], unique=False)

    # Create sellers table
    op.create_table(
        "sellers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "platform",
            postgresql.ENUM("discogs", "ebay", "both", name="searchplatform", create_type=False),
            nullable=False,
        ),
        sa.Column("platform_seller_id", sa.String(length=255), nullable=False),
        sa.Column("seller_name", sa.String(length=255), nullable=False),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("country_code", sa.String(length=3), nullable=True),
        sa.Column("feedback_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("total_feedback_count", sa.Integer(), nullable=True),
        sa.Column("positive_feedback_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("ships_internationally", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("estimated_shipping_cost", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("seller_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create search_result_analyses table
    op.create_table(
        "search_result_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_results", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_sellers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("multi_item_sellers", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("min_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("max_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("avg_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("wantlist_matches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collection_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("new_discoveries", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("analysis_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analysis_version", sa.String(length=50), nullable=False, server_default="'1.0'"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["search_id"], ["saved_searches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create deal_recommendations table
    op.create_table(
        "deal_recommendations",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "recommendation_type",
            postgresql.ENUM(
                "BEST_PRICE",
                "MULTI_ITEM_DEAL",
                "CONDITION_VALUE",
                "LOCATION_PREFERENCE",
                "HIGH_FEEDBACK",
                name="recommendationtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "deal_score",
            postgresql.ENUM("EXCELLENT", "VERY_GOOD", "GOOD", "FAIR", "POOR", name="dealscore", create_type=False),
            nullable=False,
        ),
        sa.Column("score_value", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("wantlist_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("estimated_shipping", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("total_cost", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("potential_savings", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("savings_vs_individual", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=False),
        sa.Column("recommendation_reason", sa.String(length=500), nullable=False),
        sa.Column("item_ids", postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["analysis_id"], ["search_result_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create item_match_results table
    op.create_table(
        "item_match_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_match_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "confidence",
            postgresql.ENUM("EXACT", "HIGH", "MEDIUM", "LOW", "UNCERTAIN", name="matchconfidence", create_type=False),
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("title_similarity", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("artist_similarity", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("year_match", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("catalog_match", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("format_match", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("requires_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("reviewed_by_user", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("user_confirmed", sa.Boolean(), nullable=True),
        sa.Column("match_metadata", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["item_match_id"], ["item_matches.id"]),
        sa.ForeignKeyConstraint(["search_result_id"], ["search_results.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create seller_analyses table
    op.create_table(
        "seller_analyses",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_analysis_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wantlist_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("collection_duplicates", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_value", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("avg_item_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("estimated_shipping", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("price_competitiveness", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("inventory_depth_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("seller_reputation_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("location_preference_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("overall_score", sa.Numeric(precision=5, scale=2), nullable=False, server_default="0.0"),
        sa.Column("recommendation_rank", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["search_analysis_id"], ["search_result_analyses.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create seller_inventory table
    op.create_table(
        "seller_inventory",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("search_result_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_title", sa.String(length=500), nullable=False),
        sa.Column("item_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("item_condition", sa.String(length=50), nullable=True),
        sa.Column("is_in_wantlist", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("wantlist_priority", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["seller_id"], ["sellers.id"]),
        sa.ForeignKeyConstraint(["search_result_id"], ["search_results.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add new columns to search_results table
    op.add_column("search_results", sa.Column("seller_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("search_results", sa.Column("item_match_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("search_results", sa.Column("item_price", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column("search_results", sa.Column("item_condition", sa.String(length=50), nullable=True))
    op.add_column("search_results", sa.Column("matching_score", sa.Numeric(precision=5, scale=2), nullable=True))

    # Add foreign key constraints
    op.create_foreign_key("fk_search_results_seller_id", "search_results", "sellers", ["seller_id"], ["id"])
    op.create_foreign_key(
        "fk_search_results_item_match_id", "search_results", "item_matches", ["item_match_id"], ["id"]
    )


def downgrade() -> None:
    # Drop new tables and columns in reverse order
    op.drop_constraint("fk_search_results_item_match_id", "search_results", type_="foreignkey")
    op.drop_constraint("fk_search_results_seller_id", "search_results", type_="foreignkey")
    op.drop_column("search_results", "matching_score")
    op.drop_column("search_results", "item_condition")
    op.drop_column("search_results", "item_price")
    op.drop_column("search_results", "item_match_id")
    op.drop_column("search_results", "seller_id")

    op.drop_table("seller_inventory")
    op.drop_table("seller_analyses")
    op.drop_table("item_match_results")
    op.drop_table("deal_recommendations")
    op.drop_table("search_result_analyses")
    op.drop_table("sellers")
    op.drop_index(op.f("ix_item_matches_match_fingerprint"), table_name="item_matches")
    op.drop_table("item_matches")

    # Drop existing tables
    op.drop_index(op.f("ix_price_history_item_id"), table_name="price_history")
    op.drop_table("price_history")

    # Note: want_list_items index was removed
    op.drop_table("want_list_items")
    op.drop_table("want_lists")

    # Note: collection_items index was removed
    op.drop_table("collection_items")
    op.drop_table("collections")

    # Note: search_runs table was removed in later migrations

    # Note: search_results index was removed
    op.drop_table("search_results")

    # Note: saved_searches user_id index was removed
    op.drop_index(op.f("ix_saved_searches_next_run_at"), table_name="saved_searches")
    op.drop_table("saved_searches")

    op.drop_table("oauth_tokens")
    op.drop_table("api_keys")
    op.drop_table("app_config")

    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS matchconfidence")
    op.execute("DROP TYPE IF EXISTS dealscore")
    op.execute("DROP TYPE IF EXISTS recommendationtype")
    op.execute("DROP TYPE IF EXISTS searchstatus")
    op.execute("DROP TYPE IF EXISTS searchplatform")
    op.execute("DROP TYPE IF EXISTS oauthenvironment")
    op.execute("DROP TYPE IF EXISTS oauthprovider")
    op.execute("DROP TYPE IF EXISTS apiservice")
