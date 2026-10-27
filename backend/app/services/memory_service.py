import re

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.memory import Memory


def create_memory(db: Session, title: str, content: str, category: str) -> Memory:
    memory = Memory(title=title, content=content, category=category)
    db.add(memory)
    db.commit()
    db.refresh(memory)
    return memory


def list_memories(db: Session, limit: int = 100) -> list[Memory]:
    return list(db.scalars(select(Memory).order_by(Memory.created_at.desc()).limit(limit)).all())


def get_memory(db: Session, memory_id: int) -> Memory | None:
    return db.get(Memory, memory_id)


def update_memory(db: Session, memory: Memory, changes: dict) -> Memory:
    for field, value in changes.items():
        setattr(memory, field, value)
    db.commit()
    db.refresh(memory)
    return memory


def delete_memory(db: Session, memory: Memory) -> None:
    db.delete(memory)
    db.commit()


def _terms(query: str) -> list[str]:
    return list(dict.fromkeys(term.lower() for term in re.findall(r"[\w'-]{3,}", query)))[:8]


def search_memories(db: Session, query: str, limit: int = 5) -> list[Memory]:
    terms = _terms(query)
    if not terms:
        return []
    conditions = []
    for term in terms:
        pattern = f"%{term}%"
        conditions.extend((Memory.title.ilike(pattern), Memory.content.ilike(pattern), Memory.category.ilike(pattern)))
    matches = list(db.scalars(select(Memory).where(or_(*conditions)).limit(100)).all())

    def rank(memory: Memory) -> tuple[int, object]:
        title, content, category = (memory.title or "").lower(), (memory.content or "").lower(), (memory.category or "").lower()
        return sum(3 if term in title else 2 if term in content else 1 if term in category else 0 for term in terms), memory.created_at

    return sorted(matches, key=rank, reverse=True)[:limit]
