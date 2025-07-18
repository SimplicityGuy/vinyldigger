"""Search template management service for search orchestration."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.search_template import SearchTemplate

logger = get_logger(__name__)


class TemplateService:
    """Service for managing search templates."""

    async def get_user_templates(self, db: AsyncSession, user_id: UUID) -> list[SearchTemplate]:
        """Get all templates created by or available to a user."""
        result = await db.execute(
            select(SearchTemplate)
            .where((SearchTemplate.created_by == user_id) | (SearchTemplate.is_public.is_(True)))
            .order_by(SearchTemplate.usage_count.desc(), SearchTemplate.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_template_by_id(
        self, db: AsyncSession, template_id: UUID, user_id: UUID | None = None
    ) -> SearchTemplate | None:
        """Get a template by ID with optional user access check."""
        query = select(SearchTemplate).where(SearchTemplate.id == template_id)

        if user_id:
            # Only return if user owns it or it's public
            query = query.where((SearchTemplate.created_by == user_id) | (SearchTemplate.is_public.is_(True)))

        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def create_template(self, db: AsyncSession, user_id: UUID, template_data: dict[str, Any]) -> SearchTemplate:
        """Create a new search template."""
        template = SearchTemplate(
            created_by=user_id,
            name=template_data["name"],
            description=template_data["description"],
            category=template_data["category"],
            template_data=template_data["template_data"],
            parameters=template_data.get("parameters", {}),
            is_public=template_data.get("is_public", False),
            usage_count=0,
        )

        db.add(template)
        await db.flush()

        logger.info(f"Created template {template.id} '{template.name}' by user {user_id}")
        return template

    async def update_template(
        self, db: AsyncSession, template_id: UUID, user_id: UUID, update_data: dict[str, Any]
    ) -> SearchTemplate | None:
        """Update an existing template (user must own it)."""
        result = await db.execute(
            select(SearchTemplate).where(
                SearchTemplate.id == template_id,
                SearchTemplate.created_by == user_id,
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            return None

        for field, value in update_data.items():
            if value is not None and hasattr(template, field):
                setattr(template, field, value)

        await db.flush()
        logger.info(f"Updated template {template_id}")
        return template

    async def delete_template(self, db: AsyncSession, template_id: UUID, user_id: UUID) -> bool:
        """Delete a template (user must own it)."""
        result = await db.execute(
            select(SearchTemplate).where(
                SearchTemplate.id == template_id,
                SearchTemplate.created_by == user_id,
            )
        )
        template = result.scalar_one_or_none()

        if not template:
            return False

        await db.delete(template)
        await db.flush()

        logger.info(f"Deleted template {template_id}")
        return True

    async def get_templates_by_category(
        self, db: AsyncSession, category: str, user_id: UUID | None = None
    ) -> list[SearchTemplate]:
        """Get all templates in a specific category."""
        query = select(SearchTemplate).where(SearchTemplate.category == category)

        if user_id:
            # Include user's templates and public templates
            query = query.where((SearchTemplate.created_by == user_id) | (SearchTemplate.is_public.is_(True)))
        else:
            # Only public templates
            query = query.where(SearchTemplate.is_public.is_(True))

        query = query.order_by(SearchTemplate.usage_count.desc(), SearchTemplate.created_at.desc())

        result = await db.execute(query)
        return list(result.scalars().all())

    async def get_popular_templates(
        self, db: AsyncSession, limit: int = 10, user_id: UUID | None = None
    ) -> list[SearchTemplate]:
        """Get most popular templates."""
        query = select(SearchTemplate).where(SearchTemplate.usage_count > 0)

        if user_id:
            # Include user's templates and public templates
            query = query.where((SearchTemplate.created_by == user_id) | (SearchTemplate.is_public.is_(True)))
        else:
            # Only public templates
            query = query.where(SearchTemplate.is_public.is_(True))

        query = query.order_by(SearchTemplate.usage_count.desc()).limit(limit)

        result = await db.execute(query)
        return list(result.scalars().all())

    async def increment_usage_count(self, db: AsyncSession, template_id: UUID) -> None:
        """Increment usage count for a template."""
        result = await db.execute(select(SearchTemplate).where(SearchTemplate.id == template_id))
        template = result.scalar_one_or_none()

        if template:
            template.usage_count += 1
            await db.flush()
            logger.info(f"Incremented usage count for template {template_id}")

    async def preview_template(
        self, db: AsyncSession, template_id: UUID, parameters: dict[str, Any], user_id: UUID | None = None
    ) -> dict[str, Any]:
        """Preview what a search would look like with given parameters."""
        template = await self.get_template_by_id(db, template_id, user_id)

        if not template:
            raise ValueError(f"Template {template_id} not found or not accessible")

        # Validate required parameters
        for param_name, param_config in template.parameters.items():
            if param_config.get("required", False) and param_name not in parameters:
                raise ValueError(f"Required parameter '{param_name}' not provided")

        # Substitute parameters in template data
        from src.services.search_orchestrator import SearchOrchestrator

        orchestrator = SearchOrchestrator()

        preview_data = orchestrator._substitute_template_parameters(
            template.template_data, parameters, template.parameters
        )

        return {
            "name": preview_data.get("name", f"Search from {template.name}"),
            "query": preview_data.get("query", ""),
            "platform": preview_data.get("platform", "both"),
            "filters": preview_data.get("filters", {}),
            "min_price": preview_data.get("min_price"),
            "max_price": preview_data.get("max_price"),
            "check_interval_hours": preview_data.get("check_interval_hours", 24),
            "min_record_condition": preview_data.get("min_record_condition"),
            "min_sleeve_condition": preview_data.get("min_sleeve_condition"),
            "seller_location_preference": preview_data.get("seller_location_preference"),
        }

    async def get_template_categories(self, db: AsyncSession, user_id: UUID | None = None) -> list[str]:
        """Get all available template categories."""
        query = select(SearchTemplate.category).distinct()

        if user_id:
            # Include user's templates and public templates
            query = query.where((SearchTemplate.created_by == user_id) | (SearchTemplate.is_public.is_(True)))
        else:
            # Only public templates
            query = query.where(SearchTemplate.is_public.is_(True))

        result = await db.execute(query)
        return [row[0] for row in result.all()]

    async def search_templates(self, db: AsyncSession, query: str, user_id: UUID | None = None) -> list[SearchTemplate]:
        """Search templates by name, description, or category."""
        search_filter = (
            SearchTemplate.name.ilike(f"%{query}%")
            | SearchTemplate.description.ilike(f"%{query}%")
            | SearchTemplate.category.ilike(f"%{query}%")
        )

        db_query = select(SearchTemplate).where(search_filter)

        if user_id:
            # Include user's templates and public templates
            db_query = db_query.where((SearchTemplate.created_by == user_id) | (SearchTemplate.is_public.is_(True)))
        else:
            # Only public templates
            db_query = db_query.where(SearchTemplate.is_public.is_(True))

        db_query = db_query.order_by(SearchTemplate.usage_count.desc(), SearchTemplate.created_at.desc())

        result = await db.execute(db_query)
        return list(result.scalars().all())

    async def validate_template_data(self, template_data: dict[str, Any]) -> dict[str, Any]:
        """Validate template data structure and return any issues."""
        issues = []

        # Check required fields
        required_fields = ["query"]
        for field in required_fields:
            if field not in template_data:
                issues.append(f"Missing required field: {field}")

        # Check field types
        if "min_price" in template_data and template_data["min_price"] is not None:
            try:
                float(template_data["min_price"])
            except (ValueError, TypeError):
                issues.append("min_price must be a valid number")

        if "max_price" in template_data and template_data["max_price"] is not None:
            try:
                float(template_data["max_price"])
            except (ValueError, TypeError):
                issues.append("max_price must be a valid number")

        if "check_interval_hours" in template_data:
            try:
                hours = int(template_data["check_interval_hours"])
                if hours < 1:
                    issues.append("check_interval_hours must be at least 1")
            except (ValueError, TypeError):
                issues.append("check_interval_hours must be a valid integer")

        # Check platform values
        if "platform" in template_data:
            valid_platforms = ["discogs", "ebay", "both"]
            if template_data["platform"] not in valid_platforms:
                issues.append(f"platform must be one of: {valid_platforms}")

        return {
            "valid": len(issues) == 0,
            "issues": issues,
        }
