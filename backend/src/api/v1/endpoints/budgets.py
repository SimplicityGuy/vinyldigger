"""Budget management API endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.api.v1.schemas.search_orchestration import (
    SearchBudget as SearchBudgetSchema,
)
from src.api.v1.schemas.search_orchestration import (
    SearchBudgetCreate,
    SearchBudgetSummary,
    SearchBudgetUpdate,
)
from src.core.database import get_db
from src.models.search_budget import SearchBudget
from src.models.user import User
from src.services.budget_service import BudgetService

router = APIRouter()
budget_service = BudgetService()


@router.get("/", response_model=SearchBudgetSchema | None)
async def get_current_budget(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchBudget | None:
    """Get the current active budget for the user."""
    budget = await budget_service.get_user_budget(db, current_user.id)
    return budget


@router.post("/", response_model=SearchBudgetSchema, status_code=status.HTTP_201_CREATED)
async def create_budget(
    budget_data: SearchBudgetCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchBudget:
    """Create a new budget for the user."""
    try:
        budget = await budget_service.create_budget(db, current_user.id, budget_data.model_dump())
        await db.commit()
        return budget
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create budget: {str(e)}") from e


@router.put("/{budget_id}", response_model=SearchBudgetSchema)
async def update_budget(
    budget_id: UUID,
    budget_data: SearchBudgetUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchBudget:
    """Update an existing budget."""
    try:
        budget = await budget_service.update_budget(
            db, budget_id, current_user.id, budget_data.model_dump(exclude_unset=True)
        )

        if not budget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found or not accessible")

        await db.commit()
        return budget
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update budget: {str(e)}") from e


@router.get("/summary", response_model=SearchBudgetSummary)
async def get_budget_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchBudgetSummary:
    """Get comprehensive budget summary for dashboard."""
    try:
        summary = await budget_service.get_budget_summary(db, current_user.id)
        return SearchBudgetSummary(**summary)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get budget summary: {str(e)}"
        ) from e


@router.get("/analytics", response_model=dict[str, Any])
async def get_spending_analytics(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get spending analytics for the user."""
    try:
        analytics = await budget_service.get_spending_analytics(db, current_user.id, days)
        return analytics
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get spending analytics: {str(e)}"
        ) from e


@router.get("/alerts", response_model=list[dict[str, Any]])
async def get_budget_alerts(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get budget alerts for the user."""
    try:
        alerts = await budget_service.get_budget_alerts(db, current_user.id)
        return alerts
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get budget alerts: {str(e)}"
        ) from e


@router.post("/reset", response_model=SearchBudgetSchema)
async def reset_monthly_budget(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchBudget:
    """Reset budget for new month (normally called by scheduler)."""
    try:
        budget = await budget_service.reset_monthly_budget(db, current_user.id)

        if not budget:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No active budget found to reset")

        await db.commit()
        return budget
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to reset budget: {str(e)}"
        ) from e
