"""Search orchestration service for advanced search automation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.search import SavedSearch, SearchResult
from src.models.search_budget import SearchBudget
from src.models.search_chain import SearchChain, SearchChainLink
from src.models.search_template import SearchTemplate

logger = get_logger(__name__)


class SearchOrchestrator:
    """Service for orchestrating advanced search automation."""

    async def evaluate_chain_triggers(self, db: AsyncSession, chain_id: UUID) -> list[UUID]:
        """Evaluate if chain conditions are met and return searches to trigger."""
        logger.info(f"Evaluating chain triggers for chain {chain_id}")

        # Get the chain with all its links
        chain_result = await db.execute(
            select(SearchChain).where(SearchChain.id == chain_id, SearchChain.is_active.is_(True))
        )
        chain = chain_result.scalar_one_or_none()

        if not chain:
            logger.warning(f"Chain {chain_id} not found or inactive")
            return []

        # Get all links ordered by index
        links_result = await db.execute(
            select(SearchChainLink).where(SearchChainLink.chain_id == chain_id).order_by(SearchChainLink.order_index)
        )
        links = links_result.scalars().all()

        searches_to_trigger = []

        for link in links:
            # Get the search for this link
            search_result = await db.execute(select(SavedSearch).where(SavedSearch.id == link.search_id))
            search = search_result.scalar_one_or_none()

            if not search or not search.is_active:
                continue

            # Check if this search should be triggered based on conditions
            should_trigger = await self._evaluate_trigger_conditions(db, search, link.trigger_condition)

            if should_trigger:
                searches_to_trigger.append(search.id)
                logger.info(f"Search {search.id} ({search.name}) triggered by chain conditions")

        return searches_to_trigger

    async def _evaluate_trigger_conditions(
        self, db: AsyncSession, search: SavedSearch, conditions: dict[str, Any]
    ) -> bool:
        """Evaluate if a search meets its trigger conditions."""
        if not conditions:
            # No conditions means always trigger
            return True

        # Check if search has dependencies
        if search.depends_on_search:
            # Get the parent search results
            parent_results = await db.execute(
                select(SearchResult)
                .where(SearchResult.search_id == search.depends_on_search)
                .order_by(SearchResult.created_at.desc())
                .limit(100)  # Check recent results
            )
            parent_results_list = parent_results.scalars().all()

            # Evaluate conditions based on parent search results
            if "min_results" in conditions:
                if len(parent_results_list) < conditions["min_results"]:
                    return False

            if "max_price" in conditions:
                # Check if there are results under the max price
                affordable_results = [
                    r
                    for r in parent_results_list
                    if r.item_price and r.item_price <= Decimal(str(conditions["max_price"]))
                ]
                if not affordable_results:
                    return False

            if "found_in_wantlist" in conditions and conditions["found_in_wantlist"]:
                # Check if any results are in wantlist
                wantlist_results = [r for r in parent_results_list if r.is_in_wantlist]
                if not wantlist_results:
                    return False

        # Additional condition types can be added here
        return True

    async def check_budget_constraints(self, db: AsyncSession, user_id: UUID, estimated_cost: Decimal) -> bool:
        """Check if user has budget remaining for search execution."""
        # Get user's active budget
        budget_result = await db.execute(
            select(SearchBudget).where(
                SearchBudget.user_id == user_id,
                SearchBudget.is_active.is_(True),
                SearchBudget.period_start <= datetime.now(UTC),
                SearchBudget.period_end >= datetime.now(UTC),
            )
        )
        budget = budget_result.scalar_one_or_none()

        if not budget:
            # No budget set means unlimited
            return True

        # Check if adding this cost would exceed the budget
        remaining_budget = budget.monthly_limit - budget.current_spent

        if estimated_cost > remaining_budget:
            logger.info(
                f"Budget constraint: User {user_id} has ${remaining_budget} remaining, estimated cost ${estimated_cost}"
            )
            return False

        return True

    async def update_budget_spending(self, db: AsyncSession, user_id: UUID, actual_cost: Decimal) -> None:
        """Update user's budget spending after search execution."""
        budget_result = await db.execute(
            select(SearchBudget).where(
                SearchBudget.user_id == user_id,
                SearchBudget.is_active.is_(True),
                SearchBudget.period_start <= datetime.now(UTC),
                SearchBudget.period_end >= datetime.now(UTC),
            )
        )
        budget = budget_result.scalar_one_or_none()

        if budget:
            budget.current_spent += actual_cost
            logger.info(f"Updated budget spending for user {user_id}: +${actual_cost}")

    async def get_optimal_schedule_time(self, search: SavedSearch) -> datetime:
        """Calculate optimal execution time based on user preferences and patterns."""
        now = datetime.now(UTC)
        current_hour = now.hour

        # Start with the basic interval
        base_time = now + timedelta(hours=search.check_interval_hours)

        # If optimal run times are specified, try to schedule within those times
        if search.optimal_run_times:
            # Find the next optimal time
            optimal_times = sorted(search.optimal_run_times)

            for optimal_hour in optimal_times:
                if optimal_hour > current_hour:
                    # Schedule for today at this hour
                    optimal_time = now.replace(hour=optimal_hour, minute=0, second=0, microsecond=0)
                    if optimal_time > now:
                        return optimal_time

            # If no time today works, schedule for first optimal time tomorrow
            tomorrow = now + timedelta(days=1)
            optimal_time = tomorrow.replace(hour=optimal_times[0], minute=0, second=0, microsecond=0)
            return optimal_time

        # Avoid run times if specified
        if search.avoid_run_times:
            scheduled_hour = base_time.hour
            if scheduled_hour in search.avoid_run_times:
                # Find next available hour
                for hour_offset in range(1, 24):
                    candidate_time = base_time + timedelta(hours=hour_offset)
                    if candidate_time.hour not in search.avoid_run_times:
                        return candidate_time

        return base_time

    async def create_search_from_template(
        self, db: AsyncSession, template_id: UUID, user_id: UUID, params: dict[str, Any]
    ) -> SavedSearch:
        """Create new search from template with parameter substitution."""
        # Get the template
        template_result = await db.execute(select(SearchTemplate).where(SearchTemplate.id == template_id))
        template = template_result.scalar_one_or_none()

        if not template:
            raise ValueError(f"Template {template_id} not found")

        # Validate required parameters
        for param_name, param_config in template.parameters.items():
            if param_config.get("required", False) and param_name not in params:
                raise ValueError(f"Required parameter '{param_name}' not provided")

        # Substitute parameters in template data
        search_data = self._substitute_template_parameters(template.template_data, params, template.parameters)

        # Create the new search
        new_search = SavedSearch(
            user_id=user_id,
            name=search_data.get("name", f"Search from {template.name}"),
            query=search_data["query"],
            platform=search_data.get("platform", "both"),
            filters=search_data.get("filters", {}),
            min_price=Decimal(str(search_data["min_price"])) if search_data.get("min_price") else None,
            max_price=Decimal(str(search_data["max_price"])) if search_data.get("max_price") else None,
            check_interval_hours=search_data.get("check_interval_hours", 24),
            min_record_condition=search_data.get("min_record_condition"),
            min_sleeve_condition=search_data.get("min_sleeve_condition"),
            seller_location_preference=search_data.get("seller_location_preference"),
            template_id=template_id,  # Track which template was used
        )

        db.add(new_search)
        await db.flush()  # Get the ID

        # Update template usage count
        template.usage_count += 1

        logger.info(f"Created search {new_search.id} from template {template.name}")
        return new_search

    def _substitute_template_parameters(
        self, template_data: dict[str, Any], params: dict[str, Any], param_definitions: dict[str, Any]
    ) -> dict[str, Any]:
        """Substitute parameters in template data with provided values."""
        result = {}

        for key, value in template_data.items():
            if isinstance(value, str) and value.startswith("{") and value.endswith("}"):
                # This is a parameter placeholder
                param_name = value[1:-1]  # Remove { and }

                if param_name in params:
                    result[key] = params[param_name]
                elif param_name in param_definitions and "default" in param_definitions[param_name]:
                    result[key] = param_definitions[param_name]["default"]
                else:
                    # Keep the placeholder if no value provided
                    result[key] = value
            elif isinstance(value, dict):
                # Recursively substitute in nested dictionaries
                result[key] = self._substitute_template_parameters(value, params, param_definitions)
            else:
                result[key] = value

        return result

    async def get_dependent_searches(self, db: AsyncSession, parent_search_id: UUID) -> list[SavedSearch]:
        """Get all searches that depend on the given parent search."""
        result = await db.execute(
            select(SavedSearch).where(
                SavedSearch.depends_on_search == parent_search_id, SavedSearch.is_active.is_(True)
            )
        )
        return list(result.scalars().all())

    async def should_trigger_dependent_search(
        self, db: AsyncSession, dependent_search: SavedSearch, parent_search_id: UUID
    ) -> bool:
        """Check if a dependent search should be triggered based on parent results."""
        return await self._evaluate_trigger_conditions(db, dependent_search, dependent_search.trigger_conditions)
