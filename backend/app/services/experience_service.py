import io
import os
import re
from datetime import date, datetime
from pathlib import Path

from fastapi import HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import String, cast, extract, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import MAX_UPLOAD_BYTES, UPLOAD_DIR
from app.models.experience import Experience
from app.services.gemma_services import analyze_image_with_gemma


ALLOWED_IMAGE_FORMATS = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}


def _experience_upload_dir() -> Path:
    directory = Path(UPLOAD_DIR) / "experiences"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve_experience_file(relative_path: str) -> Path:
    """Resolve new relative paths and retain access to legacy absolute paths."""
    stored_path = Path(relative_path)
    if stored_path.is_absolute():
        return stored_path

    root = Path(UPLOAD_DIR).resolve()
    candidate = (root / stored_path).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("Experience file path escapes the configured upload directory.")
    return candidate


def _validate_image(image: UploadFile) -> tuple[bytes, str, str]:
    raw = image.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Uploaded image exceeds the size limit.")
    if not raw:
        raise HTTPException(status_code=422, detail="Uploaded image is empty.")

    try:
        with Image.open(io.BytesIO(raw)) as opened_image:
            opened_image.verify()
            image_format = opened_image.format
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(status_code=415, detail="Upload must be a valid JPEG, PNG, or WebP image.") from exc

    extension = ALLOWED_IMAGE_FORMATS.get(image_format or "")
    if not extension:
        raise HTTPException(status_code=415, detail="Only JPEG, PNG, and WebP images are supported.")
    mime_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}[image_format]
    return raw, extension, mime_type


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
    """Validate an image, store it under the configured upload root, and create its record."""
    raw, extension, mime_type = _validate_image(image)
    original_filename = image.filename or f"upload{extension}"
    filename = f"{os.urandom(16).hex()}{extension}"
    file_path = _experience_upload_dir() / filename

    try:
        file_path.write_bytes(raw)
        experience = Experience(
            title=title or original_filename,
            original_filename=original_filename,
            relative_path=(Path("experiences") / filename).as_posix(),
            mime_type=mime_type,
            user_notes=user_notes,
            captured_at=captured_at,
            latitude=latitude,
            longitude=longitude,
            location_name=location_name,
            analysis_status="pending",
        )
        db.add(experience)
        db.commit()
        db.refresh(experience)
        return experience
    except Exception as exc:
        if file_path.exists():
            file_path.unlink()
        db.rollback()
        raise HTTPException(status_code=500, detail="Could not save uploaded experience.") from exc


# Alias retained for callers of the original service.
create_experience = validate_and_store_upload


def get_experience(db: Session, experience_id: int) -> Experience:
    experience = db.get(Experience, experience_id)
    if not experience:
        raise HTTPException(status_code=404, detail="Experience not found.")
    return experience


def list_experiences(db: Session, skip: int = 0, limit: int = 100) -> list[Experience]:
    return list(
        db.scalars(
            select(Experience).order_by(Experience.created_at.desc()).offset(skip).limit(limit)
        ).all()
    )


def update_experience(db: Session, experience_id: int, update_data: dict) -> Experience:
    experience = get_experience(db, experience_id)
    for key, value in update_data.items():
        if value is not None:
            setattr(experience, key, value)
    db.commit()
    db.refresh(experience)
    return experience


def safe_delete(db: Session, experience_id: int) -> dict[str, bool]:
    """Delete a record and only a file that resolves inside the upload directory."""
    experience = get_experience(db, experience_id)
    try:
        file_path = _resolve_experience_file(experience.relative_path)
        if file_path.is_file():
            file_path.unlink()
    except ValueError:
        # Preserve the database delete while refusing traversal outside uploads.
        pass
    db.delete(experience)
    db.commit()
    return {"ok": True}


delete_experience = safe_delete


def analyze_experience(db: Session, experience_id: int) -> Experience:
    experience = get_experience(db, experience_id)
    try:
        full_path = _resolve_experience_file(experience.relative_path)
    except ValueError as exc:
        experience.analysis_status = "failed"
        experience.analysis_error = str(exc)
        db.commit()
        db.refresh(experience)
        return experience

    if not full_path.is_file():
        experience.analysis_status = "failed"
        experience.analysis_error = "Experience image is missing from disk."
    else:
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
        except Exception as exc:
            experience.analysis_status = "failed"
            experience.analysis_error = str(exc)
    db.commit()
    db.refresh(experience)
    return experience


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(term.lower() for term in re.findall(r"[\w'-]{2,}", query)))[:8]


def experience_search_filter(db: Session, query: str, limit: int = 10) -> list[Experience]:
    """Keyword retrieval over user-entered and AI-derived experience facts."""
    terms = _terms(query)
    if not terms:
        return []
    conditions = []
    searchable_fields = (
        Experience.title,
        Experience.original_filename,
        Experience.user_notes,
        Experience.ai_description,
        Experience.location_name,
        cast(Experience.extracted_tags, String),
    )
    for term in terms:
        pattern = f"%{term}%"
        conditions.extend(field.ilike(pattern) for field in searchable_fields)
    matches = list(db.scalars(select(Experience).where(or_(*conditions)).limit(100)).all())

    def rank(item: Experience) -> tuple[int, datetime | None]:
        haystacks = [
            item.title or "",
            item.original_filename or "",
            item.user_notes or "",
            item.ai_description or "",
            item.location_name or "",
            " ".join(item.extracted_tags or []),
        ]
        text = " ".join(haystacks).lower()
        return sum(term in text for term in terms), item.captured_at or item.created_at

    return sorted(matches, key=rank, reverse=True)[:limit]


search_experiences = experience_search_filter


def chat_context(experiences: list[Experience]) -> list[dict[str, object]]:
    """Serialize already-retrieved experience records for grounded Gemma context."""
    return [
        {
            "id": item.id,
            "title": item.title,
            "captured_at": item.captured_at.isoformat() if item.captured_at else None,
            "location_name": item.location_name,
            "tags": item.extracted_tags or [],
            "description": item.ai_description or item.user_notes,
        }
        for item in experiences
    ]


def list_timeline(
    db: Session,
    *,
    query: str | None = None,
    year: int | None = None,
    month: int | None = None,
    location: str | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[Experience]:
    statement = select(Experience)
    if query:
        matching_ids = [item.id for item in experience_search_filter(db, query, limit=500)]
        if not matching_ids:
            return []
        statement = statement.where(Experience.id.in_(matching_ids))
    if year is not None:
        statement = statement.where(extract("year", Experience.captured_at) == year)
    if month is not None:
        statement = statement.where(extract("month", Experience.captured_at) == month)
    if location:
        statement = statement.where(Experience.location_name.ilike(f"%{location}%"))
    statement = statement.order_by(
        Experience.captured_at.desc().nullslast(), Experience.created_at.desc()
    ).offset(skip).limit(limit)
    return list(db.scalars(statement).all())


def experiences_on_this_day(db: Session, reference_date: date) -> list[Experience]:
    statement = (
        select(Experience)
        .where(Experience.captured_at.is_not(None))
        .where(extract("month", Experience.captured_at) == reference_date.month)
        .where(extract("day", Experience.captured_at) == reference_date.day)
        .where(extract("year", Experience.captured_at) < reference_date.year)
        .order_by(Experience.captured_at.desc())
    )
    return list(db.scalars(statement).all())


def random_experience(db: Session) -> Experience | None:
    return db.scalar(select(Experience).order_by(func.random()).limit(1))
