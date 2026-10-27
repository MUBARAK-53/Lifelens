
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MemoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=20000)
    category: str = Field(default="general", max_length=100)


class MemoryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1, max_length=20000)
    category: str | None = Field(default=None, min_length=1, max_length=100)


class MemoryResponse(BaseModel):
    id: int
    title: str
    content: str
    category: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
