"""
Knowledge Base models for RAG pipeline context.
"""

from __future__ import annotations

import uuid
from typing import Optional

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, Index, String, Text
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class KnowledgeBaseArticle(BaseModel):
    """Knowledge base article for providing support context in RAG."""

    __tablename__ = "knowledge_base_articles"
    __table_args__ = (
        Index("ix_kb_category", "category"),
        Index("ix_kb_is_published", "is_published"),
        # We need an index on search_vector, but Alembic might struggle with TSVECTOR indexes if not defined properly.
        # We will create it directly in the migration or let SQLAlchemy attempt it.
        Index("ix_kb_search_vector", "search_vector", postgresql_using="gin"),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Vector embedding for semantic search
    embedding = mapped_column(Vector(1536), nullable=True)
    
    # Lexical search vector for hybrid search
    search_vector = mapped_column(TSVECTOR, nullable=True)

    def __repr__(self) -> str:
        return f"<KnowledgeBaseArticle {self.title[:50]}>"
