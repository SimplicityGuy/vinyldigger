"""Search chain API endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.endpoints.auth import get_current_user
from src.api.v1.schemas.search_orchestration import (
    SearchChain,
    SearchChainCreate,
    SearchChainLink,
    SearchChainLinkCreate,
    SearchChainLinkUpdate,
    SearchChainUpdate,
)
from src.core.database import get_db
from src.models.search_chain import SearchChain as SearchChainModel
from src.models.search_chain import SearchChainLink as SearchChainLinkModel
from src.models.user import User
from src.services.search_orchestrator import SearchOrchestrator

router = APIRouter()
orchestrator = SearchOrchestrator()


@router.get("/", response_model=list[SearchChain])
async def get_user_chains(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchChainModel]:
    """Get all search chains for the user."""
    result = await db.execute(
        select(SearchChainModel)
        .where(SearchChainModel.user_id == current_user.id)
        .order_by(SearchChainModel.created_at.desc())
    )
    return list(result.scalars().all())


@router.get("/{chain_id}", response_model=SearchChain)
async def get_chain(
    chain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchChainModel:
    """Get a specific search chain."""
    result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    return chain


@router.post("/", response_model=SearchChain, status_code=status.HTTP_201_CREATED)
async def create_chain(
    chain_data: SearchChainCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchChainModel:
    """Create a new search chain."""
    try:
        chain = SearchChainModel(
            user_id=current_user.id,
            name=chain_data.name,
            description=chain_data.description,
            is_active=chain_data.is_active,
        )

        db.add(chain)
        await db.flush()
        await db.commit()

        return chain
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create chain: {str(e)}") from e


@router.put("/{chain_id}", response_model=SearchChain)
async def update_chain(
    chain_id: UUID,
    chain_data: SearchChainUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchChainModel:
    """Update an existing search chain."""
    result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    try:
        update_data = chain_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(chain, field):
                setattr(chain, field, value)

        await db.commit()
        return chain
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update chain: {str(e)}") from e


@router.delete("/{chain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain(
    chain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a search chain."""
    result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    try:
        await db.delete(chain)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete chain: {str(e)}"
        ) from e


@router.get("/{chain_id}/links", response_model=list[SearchChainLink])
async def get_chain_links(
    chain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchChainLinkModel]:
    """Get all links in a search chain."""
    # Verify chain exists and belongs to user
    chain_result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = chain_result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    # Get links ordered by index
    result = await db.execute(
        select(SearchChainLinkModel)
        .where(SearchChainLinkModel.chain_id == chain_id)
        .order_by(SearchChainLinkModel.order_index)
    )
    return list(result.scalars().all())


@router.post("/{chain_id}/links", response_model=SearchChainLink, status_code=status.HTTP_201_CREATED)
async def create_chain_link(
    chain_id: UUID,
    link_data: SearchChainLinkCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchChainLinkModel:
    """Add a link to a search chain."""
    # Verify chain exists and belongs to user
    chain_result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = chain_result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    try:
        link = SearchChainLinkModel(
            chain_id=chain_id,
            search_id=link_data.search_id,
            order_index=link_data.order_index,
            trigger_condition=link_data.trigger_condition,
        )

        db.add(link)
        await db.flush()
        await db.commit()

        return link
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to create chain link: {str(e)}"
        ) from e


@router.put("/{chain_id}/links/{link_id}", response_model=SearchChainLink)
async def update_chain_link(
    chain_id: UUID,
    link_id: UUID,
    link_data: SearchChainLinkUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchChainLinkModel:
    """Update a chain link."""
    # Verify chain exists and belongs to user
    chain_result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = chain_result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    # Get the link
    link_result = await db.execute(
        select(SearchChainLinkModel).where(
            SearchChainLinkModel.id == link_id,
            SearchChainLinkModel.chain_id == chain_id,
        )
    )
    link = link_result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain link not found")

    try:
        update_data = link_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if hasattr(link, field):
                setattr(link, field, value)

        await db.commit()
        return link
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to update chain link: {str(e)}"
        ) from e


@router.delete("/{chain_id}/links/{link_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_chain_link(
    chain_id: UUID,
    link_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a chain link."""
    # Verify chain exists and belongs to user
    chain_result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = chain_result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    # Get the link
    link_result = await db.execute(
        select(SearchChainLinkModel).where(
            SearchChainLinkModel.id == link_id,
            SearchChainLinkModel.chain_id == chain_id,
        )
    )
    link = link_result.scalar_one_or_none()

    if not link:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chain link not found")

    try:
        await db.delete(link)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to delete chain link: {str(e)}"
        ) from e


@router.post("/{chain_id}/evaluate", response_model=dict[str, Any])
async def evaluate_chain(
    chain_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Evaluate chain triggers and return searches that would be triggered."""
    # Verify chain exists and belongs to user
    chain_result = await db.execute(
        select(SearchChainModel).where(
            SearchChainModel.id == chain_id,
            SearchChainModel.user_id == current_user.id,
        )
    )
    chain = chain_result.scalar_one_or_none()

    if not chain:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Search chain not found")

    try:
        triggered_searches = await orchestrator.evaluate_chain_triggers(db, chain_id)

        return {
            "chain_id": chain_id,
            "chain_name": chain.name,
            "triggered_searches": triggered_searches,
            "count": len(triggered_searches),
            "message": f"Found {len(triggered_searches)} searches that would be triggered",
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to evaluate chain: {str(e)}"
        ) from e
