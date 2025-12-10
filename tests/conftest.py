import pytest

from fastapi.testclient import TestClient
from fastapi.security.http import (
    HTTPBearer,
    HTTPAuthorizationCredentials,
)
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, MagicMock

from src.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def async_session():
    """Mocked async session"""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture(autouse=True)
def mock_http_bearer(monkeypatch):
    async def fake_http_bearer_call(self, request):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")

    monkeypatch.setattr(HTTPBearer, "__call__", fake_http_bearer_call)
    yield
