
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.memory import MemoryCreate, MemoryResponse, MemoryUpdate
from app.services.memory_service import (
    create_memory,
    list_memories,
    search_memories,
    get_memory,
    update_memory,
    delete_memory,
)


router = APIRouter(prefix="/memories", tags=["Memories"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=MemoryResponse, status_code=201)
def save_memory(
    request: MemoryCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_memory(
            db=db,
            title=request.title,
            content=request.content,
            category=request.category,
        )
    except Exception as exc:
        db.rollback()
        logger.exception("Could not save memory")
        raise HTTPException(status_code=500, detail=f"Could not save memory: {exc}") from exc


@router.get("/", response_model=list[MemoryResponse])
def get_memories(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_memories(db, limit=limit)


@router.get("/search", response_model=list[MemoryResponse])
def find_memories(
    q: str = Query(min_length=1, max_length=500),
    db: Session = Depends(get_db),
):
    return search_memories(db, query=q, limit=20)


@router.get("/{memory_id}", response_model=MemoryResponse)
def read_memory(memory_id: int, db: Session = Depends(get_db)):
    memory = get_memory(db, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return memory


@router.patch("/{memory_id}", response_model=MemoryResponse)
def edit_memory(memory_id: int, request: MemoryUpdate, db: Session = Depends(get_db)):
    memory = get_memory(db, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found.")
    try:
        return update_memory(db, memory, request.model_dump(exclude_unset=True))
    except Exception as exc:
        db.rollback()
        logger.exception("Could not update memory id=%s", memory_id)
        raise HTTPException(status_code=500, detail=f"Could not update memory: {exc}") from exc


@router.delete("/{memory_id}", status_code=204)
def remove_memory(memory_id: int, db: Session = Depends(get_db)):
    memory = get_memory(db, memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found.")
    try:
        delete_memory(db, memory)
    except Exception as exc:
        db.rollback()
        logger.exception("Could not delete memory id=%s", memory_id)
        raise HTTPException(status_code=500, detail=f"Could not delete memory: {exc}") from exc
