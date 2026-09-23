from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app


def test_chat_requires_message_or_attachment():
    response = TestClient(app).post("/internal/v1/chat/messages", json={"message": "", "attachment_ids": []})
    assert response.status_code == 400


def test_chat_mock_provider_returns_fixed_shape():
    response = TestClient(app).post("/internal/v1/chat/messages", json={"message": "Привет"})
    assert response.status_code == 200
    payload = response.json()
    UUID(payload["conversation_id"])
    UUID(payload["message_id"])
    assert isinstance(payload["products"], list)
    assert isinstance(payload["actions"], list)
    assert isinstance(payload["errors"], list)
