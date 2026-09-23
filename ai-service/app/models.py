from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatRequest(BaseModel):
    conversation_id: UUID | None = None
    message: str = Field(default="", max_length=4000)
    attachment_ids: list[UUID] = Field(default_factory=list)
    locale: str = "ru-RU"

    @field_validator("message")
    @classmethod
    def message_or_attachments(cls, value: str) -> str:
        return value.strip()


class ProductCard(BaseModel):
    id: int
    article: str | None = None
    name: str
    price: dict[str, Any] | None = None
    availability: dict[str, Any] | None = None
    image_url: str | None = None
    product_url: str | None = None


class ChatAction(BaseModel):
    type: Literal["PROPOSE_CART_ADD"]
    proposal_id: UUID
    product_id: int
    quantity: int = Field(ge=1)
    label: str


class ChatError(BaseModel):
    code: str
    message: str
    retryable: bool
    source: str


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    text: str
    products: list[ProductCard] = Field(default_factory=list)
    actions: list[ChatAction] = Field(default_factory=list)
    errors: list[ChatError] = Field(default_factory=list)


class AttachmentResponse(BaseModel):
    attachment_id: UUID
    file_name: str
    mime_type: str
    size_bytes: int
    status: Literal["ready"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
