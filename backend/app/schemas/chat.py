
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=10000)
    session_id: str = Field(default="default", min_length=1, max_length=100)


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    references: list["MemoryReference"] = Field(default_factory=list)


class MemoryReference(BaseModel):
    source_type: Literal["memory", "experience"]
    id: int
    title: str
    captured_at: datetime | None = None
    location_name: str | None = None
    relative_path: str | None = None
