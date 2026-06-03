from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class EasementPage(BaseModel):
    pageNumber: int
    lines: List[str]
    confidence: float


class EasementDoc(BaseModel):
    id: Optional[str] = None
    filename: str
    pages: List[EasementPage]
    lines: List[str]
    pageCount: int
    createdAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
