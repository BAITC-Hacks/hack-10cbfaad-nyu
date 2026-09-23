import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    product_service_url: str = os.getenv("PRODUCT_SERVICE_URL", "http://product-service:8001")
    internal_service_token: str = os.getenv("INTERNAL_SERVICE_TOKEN", "change-me")
    redis_url: str = os.getenv("REDIS_URL", "")
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock").lower()
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    max_attachment_mb: int = int(os.getenv("MAX_ATTACHMENT_MB", "15"))
    conversation_ttl_seconds: int = int(os.getenv("CONVERSATION_TTL_SECONDS", "86400"))
    knowledge_dir: str = os.getenv("KNOWLEDGE_DIR", "knowledge")


settings = Settings()
