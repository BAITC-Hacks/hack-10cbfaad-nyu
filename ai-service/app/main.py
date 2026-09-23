from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile

from .config import settings
from .files import AttachmentStore, SUPPORTED
from .history import ConversationStore
from .models import AttachmentResponse, ChatRequest, ChatResponse
from .product_client import ProductClient
from .provider import build_provider
from .service import AiService

app = FastAPI(title="AI Service", version="1.0.0")
history = ConversationStore(settings.redis_url, settings.conversation_ttl_seconds)
attachments = AttachmentStore()
service = AiService(build_provider(settings), ProductClient(settings.product_service_url, settings.internal_service_token), history, settings.knowledge_dir, attachments)


@app.post("/internal/v1/chat/messages", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.message and not request.attachment_ids:
        raise HTTPException(status_code=400, detail={"code": "BAD_REQUEST", "message": "message or attachment_ids is required"})
    return await service.chat(request)


@app.post("/internal/v1/attachments", response_model=AttachmentResponse, status_code=201)
async def upload_attachment(file: UploadFile = File(...)) -> AttachmentResponse:
    if file.content_type not in SUPPORTED:
        raise HTTPException(status_code=415, detail={"code": "UNSUPPORTED_FILE_TYPE"})
    data = await file.read()
    if len(data) > settings.max_attachment_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE"})
    attachment_id = uuid4()
    try:
        attachments.put(attachment_id, file.filename or "attachment", file.content_type, data)
    except Exception as exc:
        raise HTTPException(status_code=422, detail={"code": "FILE_PARSE_FAILED"}) from exc
    return AttachmentResponse(attachment_id=attachment_id, file_name=file.filename or "attachment", mime_type=file.content_type, size_bytes=len(data), status="ready")
