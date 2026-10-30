from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExperienceUpdate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    user_notes: str | None = Field(default=None, max_length=20000)
    captured_at: datetime | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    location_name: str | None = Field(default=None, max_length=255)


class ExperienceResponse(BaseModel):
    id: int
    title: str | None
    original_filename: str
    relative_path: str
    mime_type: str
    user_notes: str | None
    ai_description: str | None
    extracted_tags: list[str] = Field(default_factory=list)
    analysis_status: str
    analysis_error: str | None
    captured_at: datetime | None
    uploaded_at: datetime
    latitude: float | None
    longitude: float | None
    location_name: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExperienceSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    limit: int = Field(default=10, ge=1, le=50)


class ExperienceSearchResponse(BaseModel):
    query: str
    results: list[ExperienceResponse]
    summary: str | None = None
    summary_source: str = "database"


class MemoryRevealResponse(BaseModel):
    experience: ExperienceResponse
    reflection: str
