from io import BytesIO

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

def upload_experience(client, **kwargs):
    data = {"title": kwargs.get("title", "Test Title"), "user_notes": kwargs.get("user_notes", "Test notes"), "location_name": kwargs.get("location_name", "Test Location")}
    data.update(kwargs)
    resp = client.post("/experiences/upload", files=image_file(kwargs.get("original_filename", "photo.png")), data=data)
    assert resp.status_code == 201
    return resp.json()

def test_search_pending_experience_by_filename(client):
    db = SessionLocal()
    try:
        record = Experience(
            title="string",
            original_filename="Nebula Fee Reciept.jpeg",
            relative_path="experiences/search-regression.jpeg",
            mime_type="image/jpeg",
            user_notes="string",
        )
        db.add(record)
        db.commit()
        experience_id = record.id
    finally:
        db.close()

    for query in ("Nebula", "Nebula Fee Reciept"):
        response = client.post("/experiences/search", json={"query": query, "limit": 10})
        assert response.status_code == 200
        assert any(item["id"] == experience_id for item in response.json()["results"])

def test_search_by_title(client):
    record = upload_experience(client, title="Special Hiking Trip")
    results = client.post("/experiences/search", json={"query": "hiking", "limit": 10}).json()["results"]
    assert any(r["id"] == record["id"] for r in results)

def test_search_by_notes(client):
    record = upload_experience(client, user_notes="This is a unique note for search.")
    results = client.post("/experiences/search", json={"query": "unique note", "limit": 10}).json()["results"]
    assert any(r["id"] == record["id"] for r in results)

def test_search_no_match(client):
    upload_experience(client, title="Completely unrelated title")
    results = client.post("/experiences/search", json={"query": "no_such_term_should_match", "limit": 10}).json()["results"]
    assert results == []
