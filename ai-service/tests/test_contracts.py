import asyncio
import io
import json
from uuid import UUID

from fastapi.testclient import TestClient

from app.main import app
from app.history import ConversationStore
from app.service import AiService
from app.models import ChatRequest
from app.provider import LlmResult, MockLlmProvider


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


def test_mock_provider_searches_for_plain_product_name():
    result = asyncio.run(
        MockLlmProvider().complete(
            [{"role": "user", "content": "лампочка"}], []
        )
    )

    assert len(result.tool_calls) == 1
    function = result.tool_calls[0]["function"]
    assert function["name"] == "search_products"
    assert json.loads(function["arguments"])["query"] == "лампочка"


def test_mock_provider_removes_search_command_from_query():
    result = asyncio.run(
        MockLlmProvider().complete(
            [{"role": "user", "content": "Найди Legrand DRX250"}], []
        )
    )

    arguments = json.loads(result.tool_calls[0]["function"]["arguments"])
    assert arguments["query"] == "Legrand DRX250"


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
    result = asyncio.run(AiService(provider, FakeProducts(), ConversationStore(), "knowledge").chat(ChatRequest(message="Найди DRX250")))
    assert result.text == "Поиск завершён"
    assert provider.calls == 2


def test_upload_rejects_unsupported_file_type():
    response = TestClient(app).post(
        "/internal/v1/attachments",
        files={"file": ("notes.txt", b"not supported", "text/plain")},
    )
    assert response.status_code == 415


def test_upload_accepts_xlsx_and_returns_attachment_id():
    from openpyxl import Workbook

    workbook = Workbook()
    workbook.active.append(["article", "quantity"])
    workbook.active.append(["DRX250", 4])
    data = io.BytesIO()
    workbook.save(data)
    response = TestClient(app).post(
        "/internal/v1/attachments",
        files={"file": ("specification.xlsx", data.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 201
    payload = response.json()
    UUID(payload["attachment_id"])
    assert payload["status"] == "ready"


def test_propose_cart_add_creates_action_without_cart_call():
    class ProposalProvider:
        def __init__(self):
            self.calls = 0

        async def complete(self, messages, tools):
            self.calls += 1
            if self.calls == 1:
                return LlmResult(tool_calls=[{"function": {"name": "propose_cart_add", "arguments": '{"product_id":515291,"quantity":2}'}}])
            return LlmResult(text="Готов добавить товар после подтверждения")

    result = asyncio.run(AiService(ProposalProvider(), object(), ConversationStore(), "knowledge").chat(ChatRequest(message="Добавь 2 штуки")))
    assert len(result.actions) == 1
    assert result.actions[0].product_id == 515291
    assert result.actions[0].quantity == 2
