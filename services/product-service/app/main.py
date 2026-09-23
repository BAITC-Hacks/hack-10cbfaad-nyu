import logging
import secrets
from contextlib import asynccontextmanager
from uuid import UUID, uuid4

import httpx
from fastapi import Depends, FastAPI, Header, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import Settings, get_settings
from .database import build_engine, build_session_factory, initialize_database, session_scope
from .ekt_client import EktClient
from .errors import ServiceError
from .schemas import (
    AnalogRequest,
    AnalogResponse,
    AvailabilityResponse,
    ProductResponse,
    SearchRequest,
    SearchResponse,
    SyncRequest,
    SyncResponse,
)
from .service import (
    find_analogs,
    get_live_availability,
    get_live_product,
    search_products,
    sync_catalog,
)


logger = logging.getLogger("product-service")


def _request_id(request: Request) -> str:
    return getattr(request.state, "request_id", str(uuid4()))


def _error_response(
    request: Request,
    *,
    status_code: int,
    code: str,
    message: str,
    retryable: bool = False,
    details: dict | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": _request_id(request),
                "retryable": retryable,
                "details": jsonable_encoder(details or {}),
            }
        },
    )


def create_app(
    settings: Settings | None = None,
    *,
    engine: Engine | None = None,
    ekt_transport: httpx.BaseTransport | None = None,
) -> FastAPI:
    current_settings = settings or get_settings()
    logging.basicConfig(
        level=getattr(logging, current_settings.log_level.upper(), logging.INFO)
    )
    current_engine = engine or build_engine(current_settings.product_database_url)
    session_factory = build_session_factory(current_engine)
    ekt_client = EktClient(
        base_url=current_settings.ekt_api_base_url,
        username=current_settings.ekt_api_username,
        password=current_settings.ekt_api_password,
        timeout=current_settings.ekt_http_timeout_seconds,
        transport=ekt_transport,
    )

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialize_database(current_engine)
        yield
        ekt_client.close()
        if engine is None:
            current_engine.dispose()

    application = FastAPI(
        title="Product Service",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.settings = current_settings
    application.state.engine = current_engine
    application.state.session_factory = session_factory
    application.state.ekt_client = ekt_client

    @application.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        supplied = request.headers.get("X-Request-ID")
        try:
            parsed = UUID(supplied) if supplied else None
            valid = parsed is not None and parsed.version == 4
        except ValueError:
            valid = False
        request.state.request_id = supplied if valid else str(uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id
        return response

    @application.exception_handler(ServiceError)
    async def service_error_handler(request: Request, exc: ServiceError):
        return _error_response(
            request,
            status_code=exc.status_code,
            code=exc.code,
            message=exc.message,
            retryable=exc.retryable,
            details=exc.details,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(
            request,
            status_code=422,
            code="VALIDATION_ERROR",
            message="Request validation failed",
            details={"errors": exc.errors()},
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_error_handler(request: Request, exc: StarletteHTTPException):
        code = "PRODUCT_NOT_FOUND" if exc.status_code == 404 else "BAD_REQUEST"
        return _error_response(
            request,
            status_code=exc.status_code,
            code=code,
            message=str(exc.detail),
        )

    @application.exception_handler(Exception)
    async def unexpected_error_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled error request_id=%s path=%s",
            _request_id(request),
            request.url.path,
        )
        return _error_response(
            request,
            status_code=500,
            code="INTERNAL_ERROR",
            message="Unexpected Product Service error",
        )

    def database_session(request: Request):
        yield from session_scope(request.app.state.session_factory)

    def authorize_internal(
        request: Request,
        authorization: str | None = Header(default=None),
        x_internal_service_token: str | None = Header(default=None),
    ) -> None:
        expected = request.app.state.settings.internal_service_token
        bearer = None
        if authorization and authorization.startswith("Bearer "):
            bearer = authorization.removeprefix("Bearer ")
        accepted = any(
            token is not None and secrets.compare_digest(token, expected)
            for token in (bearer, x_internal_service_token)
        )
        if not expected or not accepted:
            raise ServiceError(
                401,
                "UNAUTHORIZED",
                "Internal service authentication failed",
            )

    @application.get("/health")
    def health(request: Request) -> dict[str, str]:
        try:
            with request.app.state.session_factory() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:
            raise ServiceError(
                503,
                "UPSTREAM_CATALOG_UNAVAILABLE",
                "Product database is unavailable",
                retryable=True,
            ) from exc
        return {"status": "healthy"}

    @application.post(
        "/internal/v1/products/search",
        response_model=SearchResponse,
        dependencies=[Depends(authorize_internal)],
    )
    def search(
        body: SearchRequest,
        session: Session = Depends(database_session),
    ) -> dict:
        return search_products(session, body)

    @application.get(
        "/internal/v1/products/{product_id}",
        response_model=ProductResponse,
        dependencies=[Depends(authorize_internal)],
    )
    def product_detail(
        product_id: int,
        request: Request,
        session: Session = Depends(database_session),
    ) -> dict:
        return get_live_product(session, request.app.state.ekt_client, product_id)

    @application.get(
        "/internal/v1/products/{product_id}/availability",
        response_model=AvailabilityResponse,
        dependencies=[Depends(authorize_internal)],
    )
    def availability(
        product_id: int,
        request: Request,
        session: Session = Depends(database_session),
    ) -> dict:
        return get_live_availability(
            session, request.app.state.ekt_client, product_id
        )

    @application.post(
        "/internal/v1/products/{product_id}/analogs",
        response_model=AnalogResponse,
        dependencies=[Depends(authorize_internal)],
    )
    def analogs(
        product_id: int,
        body: AnalogRequest,
        session: Session = Depends(database_session),
    ) -> dict:
        return find_analogs(session, product_id, body)

    @application.post(
        "/internal/v1/catalog/sync",
        response_model=SyncResponse,
        dependencies=[Depends(authorize_internal)],
    )
    def synchronize(
        body: SyncRequest,
        request: Request,
        session: Session = Depends(database_session),
    ) -> dict:
        return sync_catalog(session, request.app.state.ekt_client, body)

    return application


app = create_app()
