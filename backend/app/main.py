
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import Base, engine
from app.models import conversation, experience, memory
from app.routers import chat, experiences, memories


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables for local development.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="LifeLens AI API",
    description=(
        "A personal AI assistant powered by Gemma, "
        "with persistent conversations and saved memories."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(chat.router)
app.include_router(memories.router)
app.include_router(experiences.router)


@app.get("/")
def root():
    return {
        "message": "Welcome to LifeLens AI",
        "status": "running",
        "ai_model": "Gemma",
    }


@app.get("/health")
def health():
    return {"status": "ok"}
