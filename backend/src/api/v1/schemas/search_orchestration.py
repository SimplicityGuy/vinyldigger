"""Pydantic schemas for search orchestration API."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# Budget Schemas
class SearchBudgetBase(BaseModel):
    monthly_limit: Decimal = Field(..., gt=0, description="Monthly spending limit")
    period_start: datetime = Field(..., description="Budget period start date")
    period_end: datetime = Field(..., description="Budget period end date")
    is_active: bool = Field(default=True, description="Whether budget is active")


class SearchBudgetCreate(SearchBudgetBase):
    pass


class SearchBudgetUpdate(BaseModel):
    monthly_limit: Decimal | None = Field(None, gt=0)
    period_start: datetime | None = None
    period_end: datetime | None = None
    is_active: bool | None = None


class SearchBudget(SearchBudgetBase):
    id: UUID
    user_id: UUID
    current_spent: Decimal = Field(description="Amount spent in current period")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchBudgetSummary(BaseModel):
    """Summary of budget status for dashboard."""

    budget: SearchBudget | None
    remaining_budget: Decimal | None
    spending_this_month: Decimal
    percentage_used: float | None
    days_remaining: int


# Template Schemas
class SearchTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., min_length=1, max_length=100)
    template_data: dict[str, Any] = Field(..., description="Template configuration with placeholders")
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameter definitions")
    is_public: bool = Field(default=False, description="Whether template is publicly available")


class SearchTemplateCreate(SearchTemplateBase):
    pass


class SearchTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1, max_length=500)
    category: str | None = Field(None, min_length=1, max_length=100)
    template_data: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    is_public: bool | None = None


class SearchTemplate(SearchTemplateBase):
    id: UUID
    created_by: UUID | None
    usage_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SearchTemplateUse(BaseModel):
    """Request to create search from template."""

    template_id: UUID
    parameters: dict[str, Any] = Field(default_factory=dict, description="Parameter values")
    name: str | None = Field(None, description="Custom name for created search")


class SearchTemplatePreview(BaseModel):
    """Preview of search that would be created from template."""

    name: str
    query: str
    platform: str
    filters: dict[str, Any]
    min_price: Decimal | None
    max_price: Decimal | None
    check_interval_hours: int


# Chain Schemas
class SearchChainBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None, max_length=500)
    is_active: bool = Field(default=True)


class SearchChainCreate(SearchChainBase):
    pass


class SearchChainUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class SearchChainLinkBase(BaseModel):
    search_id: UUID
    order_index: int = Field(..., ge=0)
    trigger_condition: dict[str, Any] = Field(default_factory=dict)


class SearchChainLinkCreate(SearchChainLinkBase):
    pass


class SearchChainLinkUpdate(BaseModel):
    search_id: UUID | None = None
    order_index: int | None = Field(None, ge=0)
    trigger_condition: dict[str, Any] | None = None


class SearchChainLink(SearchChainLinkBase):
    id: UUID
    chain_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True


class SearchChain(SearchChainBase):
    id: UUID
    user_id: UUID
    links: list[SearchChainLink] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Enhanced Search Schemas
class SavedSearchOrchestrationUpdate(BaseModel):
    """Update orchestration fields for existing search."""

    depends_on_search: UUID | None = None
    trigger_conditions: dict[str, Any] | None = None
    budget_id: UUID | None = None
    estimated_cost_per_result: Decimal | None = Field(None, gt=0)
    optimal_run_times: list[int] | None = Field(None, description="Preferred hours (0-23)")
    avoid_run_times: list[int] | None = Field(None, description="Hours to avoid (0-23)")
    priority_level: int | None = Field(None, ge=1, le=10)


class SearchScheduleSuggestion(BaseModel):
    """Suggested optimal scheduling for a search."""

    current_schedule: str
    suggested_times: list[int]
    reasoning: str
    estimated_improvement: str
