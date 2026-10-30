
import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.conversation import Conversation
from app.schemas.chat import ChatRequest, ChatResponse, MemoryReference
from app.services.gemma_services import generate_response
from app.services.memory_service import search_memories
from app.services.experience_service import chat_context, search_experiences


router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)


@router.post("/", response_model=ChatResponse)
def chat_with_lifelens(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    try:
        # 1. Retrieve previous conversation history
        history_rows = db.scalars(
            select(Conversation)
            .where(Conversation.session_id == request.session_id)
            .order_by(Conversation.id.desc())
            .limit(20)
        ).all()

        history_rows = list(reversed(history_rows))

        history = [
            {"role": item.role, "content": item.content}
            for item in history_rows
        ]

        # 2. Search saved memories
        relevant_memories = search_memories(
            db,
            request.message,
            limit=5,
        )

        memory_context = [
            {
                "title": item.title,
                "content": item.content,
            }
            for item in relevant_memories
        ]

        # 3. Search uploaded experiences
        relevant_experiences = search_experiences(
            db,
            request.message,
            limit=5,
        )

        experience_context = chat_context(relevant_experiences)

        # 4. Generate references for retrieved records
        references = []

        for item in relevant_memories:
            references.append(
                MemoryReference(
                    source_type="memory",
                    id=item.id,
                    title=item.title,
                    captured_at=item.created_at,
                    location_name=None,
                    relative_path=None,
                )
            )

        for item in relevant_experiences:
            references.append(
                MemoryReference(
                    source_type="experience",
                    id=item.id,
                    title=item.title,
                    captured_at=item.captured_at,
                    location_name=item.location_name,
                    relative_path=item.relative_path,
                )
            )

        # 5. Generate grounded AI response
        reply = generate_response(
            message=request.message,
            history=history,
            memories=memory_context,
            experiences=experience_context,
        )

        # 6. Save conversation
        db.add_all(
            [
                Conversation(
                    session_id=request.session_id,
                    role="user",
                    content=request.message,
                ),
                Conversation(
                    session_id=request.session_id,
                    role="assistant",
                    content=reply,
                ),
            ]
        )

        db.commit()

        # 7. Return answer with source references
        return ChatResponse(
            session_id=request.session_id,
            reply=reply,
            references=references,
        )

    except Exception as exc:
        db.rollback()
        logger.exception(
            "LifeLens chat failed for session_id=%s",
            request.session_id,
        )
        raise HTTPException(
            status_code=502,
            detail=f"Chat failed: {exc}",
        ) from exc


@router.get("/{session_id}/history")
def get_chat_history(
    session_id: str,
    db: Session = Depends(get_db),
):
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.session_id == session_id)
        .order_by(Conversation.id.asc())
        .limit(200)
    ).all()

    return [
        {
            "role": item.role,
            "content": item.content,
            "created_at": item.created_at,
        }
        for item in rows
    ]
