import os
import shutil
from datetime import datetime
from pathlib import Path
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from app.models.experience import Experience
from app.services.gemma_services import analyze_image_with_gemma
from app.core.config import UPLOAD_DIR


def validate_and_store_upload(
    db: Session,
    image: UploadFile,
    title: str | None = None,
    user_notes: str | None = None,
    captured_at: datetime | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    location_name: str | None = None,
) -> Experience:
    """Validates and saves an uploaded experience image, creating a database record."""
    upload_path = Path(UPLOAD_DIR if UPLOAD_DIR else "uploads")
    upload_path.mkdir(parents=True, exist_ok=True)
    
    original_filename = image.filename or "upload.jpg"
    file_extension = Path(original_filename).suffix or ".jpg"
    unique_filename = f"{os.urandom(16).hex()}{file_extension}"
    file_path = upload_path / unique_filename
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(image.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not save uploaded experience: {str(e)}")

    db_experience = Experience(
        title=title or original_filename,
        original_filename=original_filename,
        relative_path=str(file_path),
        mime_type=image.content_type or "image/jpeg",
        user_notes=user_notes,
        captured_at=captured_at,
        latitude=latitude,
        longitude=longitude,
        location_name=location_name,
        analysis_status="pending"
    )
    
    db.add(db_experience)
    db.commit()
    db.refresh(db_experience)
    
    return db_experience


# Alias for backward compatibility
create_experience = validate_and_store_upload


def get_experience(db: Session, experience_id: int) -> Experience:
    experience = db.query(Experience).filter(Experience.id == experience_id).first()
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found.")
    return experience


def list_experiences(db: Session, skip: int = 0, limit: int = 100):
    return db.query(Experience).offset(skip).limit(limit).all()


def update_experience(db: Session, experience_id: int, update_data: dict) -> Experience:
    experience = get_experience(db, experience_id)
    for key, value in update_data.items():
        if value is not None:
            setattr(experience, key, value)
    db.commit()
    db.refresh(experience)
    return experience


def safe_delete(db: Session, experience_id: int):
    """Safely deletes an experience record and its associated file from disk."""
    experience = get_experience(db, experience_id)
    if experience.relative_path and os.path.exists(experience.relative_path):
        try:
            os.remove(experience.relative_path)
        except Exception:
            pass
    db.delete(experience)
    db.commit()
    return {"ok": True}


# Alias for backward compatibility
delete_experience = safe_delete


def analyze_experience(db: Session, experience_id: int) -> Experience:
    """
    Triggers vision analysis on an experience record using gemma_services
    with safe, fresh client creation.
    """
    experience = get_experience(db, experience_id)
    
    full_path = Path(experience.relative_path)
    if not full_path.exists():
        upload_path = Path(UPLOAD_DIR if UPLOAD_DIR else "uploads")
        full_path = upload_path / Path(experience.relative_path).name

    if not full_path.exists():
        experience.analysis_status = "failed"
        experience.analysis_error = f"File not found on disk at {full_path}"
        db.commit()
        db.refresh(experience)
        return experience

    try:
        result = analyze_image_with_gemma(
            file_path=str(full_path), 
            user_notes=experience.user_notes,
            mime_type=experience.mime_type,
        )
        
        experience.ai_description = result.get("ai_description")
        experience.extracted_tags = result.get("extracted_tags", [])
        experience.analysis_status = result.get("analysis_status", "completed")
        experience.analysis_error = result.get("analysis_error")

    except Exception as e:
        experience.analysis_status = "failed"
        experience.analysis_error = str(e)

    db.commit()
    db.refresh(experience)
    return experience


def experience_search_filter(db: Session, query: str, limit: int = 10):
    """Filters or searches experiences by query string."""
    search_term = f"%{query}%"
    return db.query(Experience).filter(
        (Experience.title.ilike(search_term)) |
        (Experience.user_notes.ilike(search_term)) |
        (Experience.ai_description.ilike(search_term))
    ).limit(limit).all()


# Alias for backward compatibility
search_experiences = experience_search_filter


def chat_context(db: Session, query: str | None = None, limit: int = 5):
    """Returns recent or relevant experiences formatted for chat context injection."""
    if query:
        return search_experiences(db, query, limit=limit)
    return db.query(Experience).order_by(Experience.created_at.desc()).limit(limit).all()