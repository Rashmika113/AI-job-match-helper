import pytest
from fastapi.testclient import TestClient

import server
from tests.conftest import FakeEmbedder, FakeLLM


@pytest.fixture
def client(monkeypatch):
    server.app.dependency_overrides[server.get_embedder] = FakeEmbedder
    monkeypatch.setattr(server, "get_llm", lambda *a, **k: FakeLLM())
    yield TestClient(server.app)
    server.app.dependency_overrides.clear()


def test_index_and_static(client):
    assert "AI Job-Match" in client.get("/").text
    assert client.get("/static/app.js").status_code == 200


def test_config_lists_providers(client):
    data = client.get("/api/config").json()
    assert data["providers"][0]["key"] == "groq"
    assert "English" in data["languages"]


def test_samples(client):
    assert "Nimal Perera" in client.get("/api/samples/cv").json()["text"]
    assert client.get("/api/samples/nope").status_code == 404


def test_extract_text_file(client):
    res = client.post("/api/extract", files={"file": ("cv.txt", b"Python\r\n\r\n\r\nSQL")})
    assert res.json()["text"] == "Python\n\nSQL"
    assert client.post("/api/extract", files={"file": ("cv.exe", b"x")}).status_code == 400


def test_match(client, sample_cv, sample_job):
    data = client.post("/api/match", json={"cv_text": sample_cv, "job_text": sample_job}).json()
    assert 0 <= data["score"] <= 100
    assert data["label"].endswith("match")
    assert "Python" in data["matched_required"]
    assert "FastAPI or Flask" in data["missing_required"]
    assert len(data["weakest_requirements"]) == 3


def test_match_rejects_empty(client):
    assert client.post("/api/match", json={"cv_text": " ", "job_text": "x"}).status_code == 400


def test_tips_stream(client, sample_cv, sample_job):
    res = client.post("/api/tips", json={"cv_text": sample_cv, "job_text": sample_job, "provider": "groq"})
    assert res.status_code == 200
    assert res.text.startswith("### Summary")
