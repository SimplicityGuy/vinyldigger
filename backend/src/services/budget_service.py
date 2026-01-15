"""Budget management service for search orchestration."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.search_budget import SearchBudget

logger = get_logger(__name__)


class BudgetService:
    """Service for managing search budgets."""

    async def get_user_budget(self, db: AsyncSession, user_id: UUID) -> SearchBudget | None:
        """Get the current active budget for a user."""
        now = datetime.now(UTC)

        result = await db.execute(
            select(SearchBudget).where(
                SearchBudget.user_id == user_id,
                SearchBudget.is_active.is_(True),
                SearchBudget.period_start <= now,
                SearchBudget.period_end >= now,
            )
        )
        return result.scalar_one_or_none()

    async def create_budget(self, db: AsyncSession, user_id: UUID, budget_data: dict[str, Any]) -> SearchBudget:
        """Create a new budget for a user."""
        # Deactivate any existing active budgets
        await self._deactivate_existing_budgets(db, user_id)

        budget = SearchBudget(
            user_id=user_id,
            monthly_limit=budget_data["monthly_limit"],
            period_start=budget_data["period_start"],
            period_end=budget_data["period_end"],
            is_active=budget_data.get("is_active", True),
            current_spent=Decimal("0.00"),
        )

        db.add(budget)
        await db.flush()

        logger.info(f"Created budget {budget.id} for user {user_id}")
        return budget

    async def update_budget(
        self, db: AsyncSession, budget_id: UUID, user_id: UUID, update_data: dict[str, Any]
    ) -> SearchBudget | None:
        """Update an existing budget."""
        result = await db.execute(
            select(SearchBudget).where(
                SearchBudget.id == budget_id,
                SearchBudget.user_id == user_id,
            )
        )
        budget = result.scalar_one_or_none()

        if not budget:
            return None

        for field, value in update_data.items():
            if value is not None and hasattr(budget, field):
                setattr(budget, field, value)

        await db.flush()
        logger.info(f"Updated budget {budget_id}")
        return budget

    async def get_budget_summary(self, db: AsyncSession, user_id: UUID) -> dict[str, Any]:
        """Get comprehensive budget summary for dashboard."""
        budget = await self.get_user_budget(db, user_id)

        if not budget:
            return {
                "budget": None,
                "remaining_budget": None,
                "spending_this_month": Decimal("0.00"),
                "percentage_used": None,
                "days_remaining": 0,
            }

        remaining_budget = budget.monthly_limit - budget.current_spent
        percentage_used = float((budget.current_spent / budget.monthly_limit) * 100)

        # Calculate days remaining in budget period
        now = datetime.now(UTC)
        days_remaining = (budget.period_end - now).days

        return {
            "budget": budget,
            "remaining_budget": remaining_budget,
            "spending_this_month": budget.current_spent,
            "percentage_used": percentage_used,
            "days_remaining": max(0, days_remaining),
        }

    async def check_budget_available(self, db: AsyncSession, user_id: UUID, amount: Decimal) -> tuple[bool, str | None]:
        """Check if user has sufficient budget for an amount."""
        budget = await self.get_user_budget(db, user_id)

        if not budget:
            return True, None  # No budget set means unlimited

        remaining = budget.monthly_limit - budget.current_spent

        if amount > remaining:
            return False, f"Insufficient budget. Remaining: ${remaining}, Required: ${amount}"

        return True, None

    async def add_spending(self, db: AsyncSession, user_id: UUID, amount: Decimal, description: str = "") -> bool:
        """Add spending to user's current budget."""
        budget = await self.get_user_budget(db, user_id)

        if not budget:
            logger.warning(f"No active budget for user {user_id}, cannot track spending")
            return False

        budget.current_spent += amount
        await db.flush()

        logger.info(f"Added ${amount} spending to budget {budget.id}: {description}")
        return True

    async def reset_monthly_budget(self, db: AsyncSession, user_id: UUID) -> SearchBudget | None:
        """Reset budget for new month (called by scheduler)."""
        budget = await self.get_user_budget(db, user_id)

        if not budget:
            return None

        # Create new budget period
        now = datetime.now(UTC)
        next_month = now.replace(day=1) + timedelta(days=32)
        next_month = next_month.replace(day=1)
        period_end = next_month - timedelta(days=1)

        # Deactivate current budget
        budget.is_active = False

        # Create new budget for next period
        new_budget = SearchBudget(
            user_id=user_id,
            monthly_limit=budget.monthly_limit,  # Keep same limit
            period_start=now,
            period_end=period_end,
            current_spent=Decimal("0.00"),
            is_active=True,
        )

        db.add(new_budget)
        await db.flush()

        logger.info(f"Reset monthly budget for user {user_id}")
        return new_budget

    async def get_spending_analytics(self, db: AsyncSession, user_id: UUID, days: int = 30) -> dict[str, Any]:
        """Get spending analytics for the user."""
        budget = await self.get_user_budget(db, user_id)

        if not budget:
            return {
                "total_spent": Decimal("0.00"),
                "average_daily": Decimal("0.00"),
                "trend": "neutral",
                "projection": Decimal("0.00"),
            }

        # Calculate spending trend and projection
        period_days = (budget.period_end - budget.period_start).days
        days_elapsed = (datetime.now(UTC) - budget.period_start).days

        if days_elapsed > 0:
            daily_average = budget.current_spent / days_elapsed
            projection = daily_average * period_days
        else:
            daily_average = Decimal("0.00")
            projection = Decimal("0.00")

        # Determine trend
        if projection > budget.monthly_limit * Decimal("1.1"):
            trend = "over_budget"
        elif projection > budget.monthly_limit * Decimal("0.9"):
            trend = "on_track"
        else:
            trend = "under_budget"

        return {
            "total_spent": budget.current_spent,
            "average_daily": daily_average,
            "trend": trend,
            "projection": projection,
            "budget_limit": budget.monthly_limit,
            "days_elapsed": days_elapsed,
            "days_remaining": (budget.period_end - datetime.now(UTC)).days,
        }

    async def _deactivate_existing_budgets(self, db: AsyncSession, user_id: UUID) -> None:
        """Deactivate all existing active budgets for a user."""
        result = await db.execute(
            select(SearchBudget).where(
                SearchBudget.user_id == user_id,
                SearchBudget.is_active.is_(True),
            )
        )
        existing_budgets = result.scalars().all()

        for budget in existing_budgets:
            budget.is_active = False

        if existing_budgets:
            await db.flush()
            logger.info(f"Deactivated {len(existing_budgets)} existing budgets for user {user_id}")

    async def get_budget_alerts(self, db: AsyncSession, user_id: UUID) -> list[dict[str, Any]]:
        """Get budget alerts for user."""
        summary = await self.get_budget_summary(db, user_id)
        alerts: list[dict[str, Any]] = []

        if not summary["budget"]:
            return alerts

        percentage_used = summary["percentage_used"]
        days_remaining = summary["days_remaining"]

        # Alert thresholds
        if percentage_used >= 90:
            alerts.append(
                {
                    "type": "budget_critical",
                    "message": f"Budget {percentage_used:.1f}% depleted with {days_remaining} days remaining",
                    "severity": "high",
                }
            )
        elif percentage_used >= 75:
            alerts.append(
                {
                    "type": "budget_warning",
                    "message": f"Budget {percentage_used:.1f}% used",
                    "severity": "medium",
                }
            )

        if days_remaining <= 3 and percentage_used < 50:
            alerts.append(
                {
                    "type": "budget_underutilized",
                    "message": f"Only {percentage_used:.1f}% of budget used with {days_remaining} days left",
                    "severity": "low",
                }
            )

        return alerts
