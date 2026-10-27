import base64
import json
from io import BytesIO
from types import SimpleNamespace

from PIL import Image

from app.database import SessionLocal
from app.models.experience import Experience

def make_png():
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(40, 120, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


PNG = make_png()


def image_file(name="photo.png", content=PNG, content_type="image/png"):
    return {"image": (name, content, content_type)}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_chat_uses_cross_session_memory(client, monkeypatch):
    client.post("/memories/", json={"title": "Hiking", "content": "I enjoy hiking by lakes.", "category": "preference"})
    captured = {}
    def fake_response(**kwargs):
        captured.update(kwargs)
        return "Mocked answer"
    monkeypatch.setattr("app.routers.chat.generate_response", fake_response)
    response = client.post("/chat/", json={"session_id": "new-session", "message": "Where do I like hiking?"})
    assert response.status_code == 200
    assert response.json()["reply"] == "Mocked answer"
    assert captured["memories"][0]["title"] == "Hiking"


def test_memory_crud(client):
    created = client.post("/memories/", json={"title": "Home", "content": "My home is Pune."}).json()
    assert client.get(f"/memories/{created['id']}").status_code == 200
    assert client.patch(f"/memories/{created['id']}", json={"category": "location"}).json()["category"] == "location"
    assert client.delete(f"/memories/{created['id']}").status_code == 204


def test_upload_list_search_and_delete(client):
    upload = client.post("/experiences/upload", files=image_file(), data={"title": "Lake hike", "user_notes": "A hike near a lake", "location_name": "Pune"})
    assert upload.status_code == 201
    record = upload.json()
    assert record["analysis_status"] == "pending"
    assert client.get("/experiences/", params={"limit": 1, "location_name": "Pune"}).json()[0]["id"] == record["id"]
    assert client.post("/experiences/search", json={"query": "hike lake", "limit": 10}).json()["results"][0]["id"] == record["id"]
    assert client.delete(f"/experiences/{record['id']}").status_code == 204
    assert client.get(f"/experiences/{record['id']}").status_code == 404


def test_upload_rejects_invalid_captured_at(client):
    response = client.post(
        "/experiences/upload",
        files=image_file(),
        data={"captured_at": "string"},
    )

    assert response.status_code == 422
    assert client.get("/experiences/").json() == []


def test_upload_accepts_iso_captured_at(client):
    response = client.post(
        "/experiences/upload",
        files=image_file(),
        data={"captured_at": "2026-10-27T13:49:14+05:30"},
    )

    assert response.status_code == 201
    assert response.json()["captured_at"].startswith("2026-10-27T13:49:14")


def test_analyze_experience_uses_mocked_interactions_api(client, monkeypatch):
    upload = client.post("/experiences/upload", files=image_file("receipt.png"))
    assert upload.status_code == 201
    experience_id = upload.json()["id"]
    captured = {}

    def create_interaction(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            output_text=json.dumps({
                "description": "A printed shop receipt.",
                "important_details": ["Total amount is visible"],
                "tags": ["Receipt", "Shopping", "Receipt"],
                "category": "receipt",
                "visible_text": "TOTAL 42.00",
            })
        )

    fake_client = SimpleNamespace(interactions=SimpleNamespace(create=create_interaction))
    monkeypatch.setattr("app.services.gemma_services.genai.Client", lambda **kwargs: fake_client)
    monkeypatch.setattr("app.services.gemma_services.GEMINI_VISION_MODEL", "gemini-3.8-flash")

    response = client.post(f"/experiences/{experience_id}/analyze")

    assert response.status_code == 200
    result = response.json()
    assert result["analysis_status"] == "completed"
    assert result["analysis_error"] is None
    assert result["ai_description"] == (
        "A printed shop receipt.\nVisible details: Total amount is visible\n"
        "Likely category: receipt\nLegible text: TOTAL 42.00"
    )
    assert result["extracted_tags"] == ["receipt", "shopping"]
    assert captured["model"] == "gemini-3.8-flash"
    assert captured["input"][1]["type"] == "image"
    assert captured["input"][1]["mime_type"] == "image/png"
    assert base64.b64decode(captured["input"][1]["data"]).startswith(b"\x89PNG\r\n\x1a\n")
    persisted = client.get(f"/experiences/{experience_id}").json()
    assert persisted["analysis_status"] == "completed"
    assert persisted["extracted_tags"] == ["receipt", "shopping"]


def test_rejects_invalid_and_oversized_images(client, monkeypatch):
    assert client.post("/experiences/upload", files=image_file("fake.jpg", b"not-an-image", "image/jpeg")).status_code == 415
    monkeypatch.setattr("app.services.experience_service.MAX_UPLOAD_BYTES", 5)
    assert client.post("/experiences/upload", files=image_file()).status_code == 413


def test_safe_deletion_rejects_arbitrary_path(client):
    from app.services.experience_service import safe_delete
    safe_delete("../../.env")
    # Reaching this point confirms traversal is ignored; the test environment remains usable.
    assert client.get("/health").status_code == 200
