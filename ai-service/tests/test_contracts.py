from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.history import ConversationStore
from app.service import AiService
from app.models import ChatRequest
from app.provider import LlmResult


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


def test_tool_result_is_returned_to_llm_before_final_answer():
    class FakeProvider:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return LlmResult(tool_calls=[{"id": "call-1", "function": {"name": "search_products", "arguments": '{"query":"DRX250"}'}}])
            assert any(message["role"] == "tool" for message in messages)
            return LlmResult(text="Поиск завершён")

    class FakeProducts:
        async def search_products(self, query, filters=None, limit=5):
            return {"items": []}

    provider = FakeProvider()
    result = __import__("asyncio").run(AiService(provider, FakeProducts(), ConversationStore(), "knowledge").chat(ChatRequest(message="Найди DRX250")))
    assert result.text == "Поиск завершён"
    assert provider.calls == 2
