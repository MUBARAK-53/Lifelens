import os
from pathlib import Path

os.environ["DATABASE_URL"] = "sqlite:///./test_lifelens.db"
os.environ["UPLOAD_DIR"] = "test_uploads"
os.environ["GEMINI_API_KEY"] = "test-key"
os.environ["VISION_MODEL"] = ""
os.environ["VISION_MODEL_SUPPORTS_IMAGE_INPUT"] = "false"

import pytest
from fastapi.testclient import TestClient

from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_uploads():
    upload_dir = Path(__file__).resolve().parents[1] / "test_uploads"
    yield
    if upload_dir.exists():
        for path in upload_dir.glob("experiences/*"):
            path.unlink()
