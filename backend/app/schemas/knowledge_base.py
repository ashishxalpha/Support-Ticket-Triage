"""
Pydantic schemas for Knowledge Base articles.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class KBArticleBase(BaseModel):
    title: str = Field(..., max_length=255)
    content: str
    category: str | None = Field(None, max_length=100)
    is_published: bool = True


class KBArticleCreate(KBArticleBase):
    pass


class KBArticleUpdate(BaseModel):
    title: str | None = Field(None, max_length=255)
    content: str | None = None
    category: str | None = Field(None, max_length=100)
    is_published: bool | None = None


class KBArticleResponse(KBArticleBase):
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
