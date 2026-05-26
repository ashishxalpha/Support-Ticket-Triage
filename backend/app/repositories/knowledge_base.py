"""
Knowledge Base repository — data access for KB articles and semantic/hybrid search.
"""

from __future__ import annotations

import uuid

from sqlalchemy import and_, func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge_base import KnowledgeBaseArticle


class KnowledgeBaseRepository:
    """Data access for KnowledgeBaseArticle entities."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, article_id: uuid.UUID) -> KnowledgeBaseArticle | None:
        result = await self.db.execute(
            select(KnowledgeBaseArticle).where(KnowledgeBaseArticle.id == article_id)
        )
        return result.scalar_one_or_none()

    async def create(self, article: KnowledgeBaseArticle) -> KnowledgeBaseArticle:
        self.db.add(article)
        await self.db.flush()
        await self.db.refresh(article)
        return article

    async def update(self, article_id: uuid.UUID, **kwargs: object) -> KnowledgeBaseArticle | None:
        await self.db.execute(
            update(KnowledgeBaseArticle).where(KnowledgeBaseArticle.id == article_id).values(**kwargs)
        )
        await self.db.flush()
        return await self.get_by_id(article_id)
        
    async def list_articles(
        self,
        offset: int = 0,
        limit: int = 20,
        only_published: bool = True,
        category: str | None = None,
    ) -> tuple[list[KnowledgeBaseArticle], int]:
        query = select(KnowledgeBaseArticle)
        count_query = select(func.count(KnowledgeBaseArticle.id))

        conditions = []
        if only_published:
            conditions.append(KnowledgeBaseArticle.is_published == True)
        if category:
            conditions.append(KnowledgeBaseArticle.category == category)

        if conditions:
            query = query.where(and_(*conditions))
            count_query = count_query.where(and_(*conditions))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = query.order_by(KnowledgeBaseArticle.created_at.desc())
        result = await self.db.execute(query.offset(offset).limit(limit))
        return list(result.scalars().all()), total

    async def find_similar(
        self,
        embedding: list[float],
        limit: int = 5,
        threshold: float = 0.70,
        only_published: bool = True,
    ) -> list[tuple[KnowledgeBaseArticle, float]]:
        """Find similar KB articles using cosine similarity."""
        distance_expr = KnowledgeBaseArticle.embedding.cosine_distance(embedding)
        similarity_expr = (1 - distance_expr).label("similarity")

        query = (
            select(KnowledgeBaseArticle, similarity_expr)
            .where(KnowledgeBaseArticle.embedding.isnot(None))
            .where((1 - distance_expr) >= threshold)
        )

        if only_published:
            query = query.where(KnowledgeBaseArticle.is_published == True)

        query = query.order_by(distance_expr.asc()).limit(limit)

        result = await self.db.execute(query)
        return [(row[0], float(row[1])) for row in result.all()]

    async def update_embedding(
        self, article_id: uuid.UUID, embedding: list[float]
    ) -> None:
        await self.db.execute(
            update(KnowledgeBaseArticle)
            .where(KnowledgeBaseArticle.id == article_id)
            .values(embedding=embedding)
        )
        await self.db.flush()

    async def update_search_vector(self, article_id: uuid.UUID) -> None:
        """Update the tsvector for lexical search."""
        await self.db.execute(
            text(
                """
                UPDATE knowledge_base_articles
                SET search_vector = to_tsvector('english', title || ' ' || content)
                WHERE id = :id
                """
            ),
            {"id": article_id}
        )
        await self.db.flush()
