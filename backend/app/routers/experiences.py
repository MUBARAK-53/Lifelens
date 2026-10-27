from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.experience import (
    ExperienceResponse,
    ExperienceSearchRequest,
    ExperienceSearchResponse,
    ExperienceUpdate,
)
from app.services.experience_service import (
    validate_and_store_upload,
    get_experience,
    list_experiences,
    update_experience,
    safe_delete,
    analyze_experience,
    experience_search_filter,
)

router = APIRouter(prefix="/experiences", tags=["Experiences"])


@router.post("/upload", response_model=ExperienceResponse, status_code=201)
def upload_experience(
    image: UploadFile = File(...),
    title: Optional[str] = Form(None),
    user_notes: Optional[str] = Form(None),
    captured_at: Optional[datetime] = Form(None),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    location_name: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """Upload a new experience image with optional metadata."""
    return validate_and_store_upload(
        db=db,
        image=image,
        title=title,
        user_notes=user_notes,
        captured_at=captured_at,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name
    )


@router.post("/search", response_model=ExperienceSearchResponse)
def search_experiences_endpoint(
    payload: ExperienceSearchRequest,
    db: Session = Depends(get_db)
):
    """Perform natural language or keyword search on experience records."""
    results = experience_search_filter(db=db, query=payload.query, limit=payload.limit)
    return {
        "query": payload.query,
        "results": results,
        "summary": None,
        "summary_source": "database"
    }


@router.get("/", response_model=List[ExperienceResponse])
def get_all_experiences(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all stored experience records."""
    return list_experiences(db=db, skip=skip, limit=limit)


@router.get("/{experience_id}", response_model=ExperienceResponse)
def get_single_experience(experience_id: int, db: Session = Depends(get_db)):
    """Read a specific experience record by ID."""
    return get_experience(db=db, experience_id=experience_id)


@router.patch("/{experience_id}", response_model=ExperienceResponse)
def patch_experience(
    experience_id: int, 
    update_data: ExperienceUpdate, 
    db: Session = Depends(get_db)
):
    """Update metadata or notes for an experience record."""
    return update_experience(
        db=db, 
        experience_id=experience_id, 
        update_data=update_data.dict(exclude_unset=True)
    )


@router.delete("/{experience_id}")
def delete_experience_endpoint(experience_id: int, db: Session = Depends(get_db)):
    """Delete an experience record and its associated image file from disk."""
    return safe_delete(db=db, experience_id=experience_id)


@router.post("/{experience_id}/analyze", response_model=ExperienceResponse)
def trigger_analysis(experience_id: int, db: Session = Depends(get_db)):
    """
    Trigger or retry vision analysis for a specific experience record.
    """
    return analyze_experience(db=db, experience_id=experience_id)