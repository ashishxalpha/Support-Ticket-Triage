"""
Knowledge Base API endpoints.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DBSession, require_manager_or_admin
from app.core.exceptions import NotFoundException
from app.models.knowledge_base import KnowledgeBaseArticle
from app.models.user import User
from app.repositories.knowledge_base import KnowledgeBaseRepository
from app.schemas.common import PaginatedResponse
from app.schemas.knowledge_base import KBArticleCreate, KBArticleResponse, KBArticleUpdate

router = APIRouter(prefix="/knowledge-base", tags=["Knowledge Base"])


@router.post("", response_model=KBArticleResponse, status_code=201)
async def create_article(
    data: KBArticleCreate,
    db: DBSession,
    _: User = Depends(require_manager_or_admin),
) -> KBArticleResponse:
    """Create a new Knowledge Base article and enqueue embedding generation."""
    repo = KnowledgeBaseRepository(db)
    article = KnowledgeBaseArticle(
        title=data.title,
        content=data.content,
        category=data.category,
        is_published=data.is_published,
    )
    article = await repo.create(article)

    # Enqueue embedding generation
    try:
        from app.workers.celery_app import celery_app as _celery

        _celery.send_task(
            "app.workers.tasks.triage.generate_kb_embedding",
            args=[str(article.id)],
            queue="triage",
        )
    except Exception:
        pass

    return KBArticleResponse.model_validate(article)


@router.get("", response_model=PaginatedResponse[KBArticleResponse])
async def list_articles(
    db: DBSession,
    current_user: CurrentUser,
    category: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> PaginatedResponse[KBArticleResponse]:
    """List Knowledge Base articles."""
    repo = KnowledgeBaseRepository(db)
    
    # Customers can only see published articles
    only_published = current_user.role.value == "customer"
    
    offset = (page - 1) * page_size
    articles, total = await repo.list_articles(
        offset=offset,
        limit=page_size,
        only_published=only_published,
        category=category,
    )
    
    items = [KBArticleResponse.model_validate(a) for a in articles]
    return PaginatedResponse.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{article_id}", response_model=KBArticleResponse)
async def get_article(
    article_id: uuid.UUID,
    db: DBSession,
    current_user: CurrentUser,
) -> KBArticleResponse:
    """Get a specific Knowledge Base article."""
    repo = KnowledgeBaseRepository(db)
    article = await repo.get_by_id(article_id)
    
    if not article:
        raise NotFoundException("KnowledgeBaseArticle", article_id)
        
    if current_user.role.value == "customer" and not article.is_published:
        raise NotFoundException("KnowledgeBaseArticle", article_id)
        
    return KBArticleResponse.model_validate(article)


@router.patch("/{article_id}", response_model=KBArticleResponse)
async def update_article(
    article_id: uuid.UUID,
    data: KBArticleUpdate,
    db: DBSession,
    _: User = Depends(require_manager_or_admin),
) -> KBArticleResponse:
    """Update a Knowledge Base article and regenerate embedding."""
    repo = KnowledgeBaseRepository(db)
    
    update_data = data.model_dump(exclude_unset=True)
    updated = await repo.update(article_id, **update_data)
    
    if not updated:
        raise NotFoundException("KnowledgeBaseArticle", article_id)
        
    # Re-generate embedding if content or title changed
    if "title" in update_data or "content" in update_data:
        try:
            from app.workers.celery_app import celery_app as _celery

            _celery.send_task(
                "app.workers.tasks.triage.generate_kb_embedding",
                args=[str(updated.id)],
                queue="triage",
            )
        except Exception:
            pass
            
    return KBArticleResponse.model_validate(updated)
