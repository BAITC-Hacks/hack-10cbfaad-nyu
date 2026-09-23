import json
import os
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.main import create_app
from app.models import Product


class StubEktClient:
    def __init__(self) -> None:
        self.details: dict[int, dict[str, Any]] = {}
        self.pages: dict[int, dict[str, Any]] = {}
        self.detail_error: Exception | None = None
        self.list_error: Exception | None = None

    def get_product(self, product_id: int) -> dict[str, Any]:
        if self.detail_error:
            raise self.detail_error
        return self.details[product_id]

    def list_products(self, page: int) -> dict[str, Any]:
        if self.list_error:
            raise self.list_error
        return self.pages[page]


@pytest.fixture(scope="session")
def fixture_product() -> dict[str, Any]:
    path = Path(__file__).parents[1] / "fixtures" / "product_515291_raw.json"
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def engine():
    database_url = os.getenv("TEST_DATABASE_URL")
    if database_url:
        test_engine = create_engine(database_url, pool_pre_ping=True)
    else:
        test_engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    Base.metadata.create_all(test_engine)
    yield test_engine
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


@pytest.fixture()
def application(engine):
    settings = Settings(
        product_database_url="sqlite+pysqlite:///:memory:",
        internal_service_token="test-token",
        ekt_api_base_url="https://ekt.test/api",
        ekt_api_username="api-user",
        ekt_api_password="api-password",
    )
    app = create_app(settings, engine=engine)
    stub = StubEktClient()
    app.state.ekt_client = stub
    app.state.stub_ekt = stub
    return app


@pytest.fixture()
def client(application):
    with TestClient(application) as test_client:
        yield test_client


@pytest.fixture()
def ekt(application) -> StubEktClient:
    return application.state.stub_ekt


@pytest.fixture(autouse=True)
def db(application):
    with application.state.session_factory() as session:
        session.execute(delete(Product))
        session.commit()
        yield session
        session.rollback()
        session.execute(delete(Product))
        session.commit()


@pytest.fixture()
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer test-token",
        "X-Request-ID": "7cc94329-30cc-4603-90dc-894d5f48ccb0",
    }
