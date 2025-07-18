"""Search template API endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.api.v1.schemas.search_orchestration import (
    SearchTemplate as SearchTemplateSchema,
)
from src.api.v1.schemas.search_orchestration import (
    SearchTemplateCreate,
    SearchTemplatePreview,
    SearchTemplateUpdate,
    SearchTemplateUse,
)
from src.core.database import get_db
from src.models.search import SavedSearch
from src.models.search_template import SearchTemplate
from src.models.user import User
from src.services.search_orchestrator import SearchOrchestrator
from src.services.template_service import TemplateService

router = APIRouter()
template_service = TemplateService()
orchestrator = SearchOrchestrator()


@router.get("/", response_model=list[SearchTemplateSchema])
async def get_templates(
    category: str | None = Query(None, description="Filter by category"),
    search: str | None = Query(None, description="Search in name, description, category"),
    popular: bool = Query(False, description="Get popular templates only"),
    limit: int = Query(50, ge=1, le=100, description="Limit results"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchTemplate]:
    """Get templates available to the user."""
    try:
        if search:
            templates = await template_service.search_templates(db, search, current_user.id)
            return templates[:limit]
        elif category:
            templates = await template_service.get_templates_by_category(db, category, current_user.id)
            return templates[:limit]
        elif popular:
            templates = await template_service.get_popular_templates(db, limit, current_user.id)
            return templates
        else:
            templates = await template_service.get_user_templates(db, current_user.id)
            return templates[:limit]
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get templates: {str(e)}"
        ) from e


@router.get("/categories", response_model=list[str])
async def get_template_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[str]:
    """Get all available template categories."""
    try:
        categories = await template_service.get_template_categories(db, current_user.id)
        return sorted(categories)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to get categories: {str(e)}"
        ) from e


@router.get("/{template_id}", response_model=SearchTemplateSchema)
async def get_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchTemplate:
    """Get a specific template by ID."""
    template = await template_service.get_template_by_id(db, template_id, current_user.id)

    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found or not accessible")

    return template


@router.post("/", response_model=SearchTemplateSchema, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: SearchTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchTemplate:
    """Create a new search template."""
    try:
        # Validate template data
        validation = await template_service.validate_template_data(template_data.template_data)
        if not validation["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid template data: {'; '.join(validation['issues'])}",
            )

        template = await template_service.create_template(db, current_user.id, template_data.model_dump())
        await db.commit()
        return template
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create template: {str(e)}"
        ) from e


@router.put("/{template_id}", response_model=SearchTemplateSchema)
async def update_template(
    template_id: UUID,
    template_data: SearchTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchTemplate:
    """Update an existing template (user must own it)."""
    try:
        # Validate template data if provided
        update_dict = template_data.model_dump(exclude_unset=True)
        if "template_data" in update_dict and update_dict["template_data"]:
            validation = await template_service.validate_template_data(update_dict["template_data"])
            if not validation["valid"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid template data: {'; '.join(validation['issues'])}",
                )

        template = await template_service.update_template(db, template_id, current_user.id, update_dict)

        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found or not accessible")

        await db.commit()
        return template
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update template: {str(e)}"
        ) from e


@router.delete("/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a template (user must own it)."""
    try:
        success = await template_service.delete_template(db, template_id, current_user.id)

        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found or not accessible")

        await db.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete template: {str(e)}"
        ) from e


@router.post("/{template_id}/preview", response_model=SearchTemplatePreview)
async def preview_template(
    template_id: UUID,
    parameters: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchTemplatePreview:
    """Preview what a search would look like with given parameters."""
    try:
        preview_data = await template_service.preview_template(db, template_id, parameters, current_user.id)
        return SearchTemplatePreview(**preview_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to preview template: {str(e)}"
        ) from e


@router.post("/{template_id}/use", response_model=dict[str, Any])
async def use_template(
    template_id: UUID,
    template_use: SearchTemplateUse,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Create a new search from a template."""
    try:
        # Create search from template using orchestrator
        search = await orchestrator.create_search_from_template(
            db, template_id, current_user.id, template_use.parameters
        )

        # Override name if provided
        if template_use.name:
            search.name = template_use.name

        # Increment template usage count
        await template_service.increment_usage_count(db, template_id)

        await db.commit()

        return {"search_id": search.id, "message": f"Search '{search.name}' created successfully from template"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to create search from template: {str(e)}"
        ) from e


@router.post("/{template_id}/validate", response_model=dict[str, Any])
async def validate_template_parameters(
    template_id: UUID,
    parameters: dict[str, Any],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Validate parameters for a template without creating a search."""
    try:
        template = await template_service.get_template_by_id(db, template_id, current_user.id)

        if not template:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found or not accessible")

        issues = []

        # Check required parameters
        for param_name, param_config in template.parameters.items():
            if param_config.get("required", False) and param_name not in parameters:
                issues.append(f"Required parameter '{param_name}' not provided")

        # Check parameter types if specified
        for param_name, param_value in parameters.items():
            if param_name in template.parameters:
                param_config = template.parameters[param_name]
                expected_type = param_config.get("type")

                if expected_type == "number" and not isinstance(param_value, int | float):
                    issues.append(f"Parameter '{param_name}' must be a number")
                elif expected_type == "string" and not isinstance(param_value, str):
                    issues.append(f"Parameter '{param_name}' must be a string")
                elif expected_type == "boolean" and not isinstance(param_value, bool):
                    issues.append(f"Parameter '{param_name}' must be a boolean")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "template_name": template.name,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to validate parameters: {str(e)}"
        ) from e


@router.get("/analytics/overview", response_model=dict[str, Any])
async def get_template_analytics(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Get template usage analytics for the current user."""
    # Get user's templates
    templates_result = await db.execute(select(SearchTemplate).where(SearchTemplate.created_by == current_user.id))
    templates = templates_result.scalars().all()

    # Calculate analytics
    total_templates = len(templates)
    total_uses = sum(t.usage_count for t in templates)
    avg_uses_per_template = total_uses / total_templates if total_templates > 0 else 0

    # Most used templates
    most_used = sorted(templates, key=lambda t: t.usage_count, reverse=True)[:5]

    # Category breakdown
    category_stats = {}
    for template in templates:
        if template.category not in category_stats:
            category_stats[template.category] = {"count": 0, "uses": 0}
        category_stats[template.category]["count"] += 1
        category_stats[template.category]["uses"] += template.usage_count

    # Public vs private
    public_templates = [t for t in templates if t.is_public]
    private_templates = [t for t in templates if not t.is_public]

    # Parameter statistics
    total_parameters = sum(len(t.parameters) for t in templates)
    avg_parameters = total_parameters / total_templates if total_templates > 0 else 0

    # Get searches created from templates
    searches_from_templates_result = await db.execute(
        select(SavedSearch).where(SavedSearch.user_id == current_user.id, SavedSearch.template_id.is_not(None))
    )
    searches_from_templates = searches_from_templates_result.scalars().all()

    return {
        "total_templates": total_templates,
        "total_uses": total_uses,
        "avg_uses_per_template": round(avg_uses_per_template, 2),
        "public_templates": len(public_templates),
        "private_templates": len(private_templates),
        "avg_parameters_per_template": round(avg_parameters, 2),
        "searches_from_templates": len(searches_from_templates),
        "most_used_templates": [
            {
                "id": str(t.id),
                "name": t.name,
                "category": t.category,
                "usage_count": t.usage_count,
                "is_public": t.is_public,
            }
            for t in most_used
        ],
        "category_breakdown": category_stats,
        "template_efficiency": {
            "templates_with_uses": len([t for t in templates if t.usage_count > 0]),
            "templates_unused": len([t for t in templates if t.usage_count == 0]),
            "most_productive_category": max(category_stats.items(), key=lambda x: x[1]["uses"])[0]
            if category_stats
            else None,
        },
    }
