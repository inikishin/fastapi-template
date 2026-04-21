"""
Conftest for the FastAPI + SQLAlchemy template.

Import order matters: app_config.db_name is overwritten BEFORE importing
src.main because src/config/postgres/db_config.py creates async_engine at
module import time, and the connection URL is captured on first import.
Overriding the DB name later would still leave the engine pointing at the
production database.
"""

import glob
import io
import json
import os

import pytest
from dotenv import load_dotenv

load_dotenv()

from src.config.settings import app_config  # noqa: E402

_TEST_DB_NAME = app_config.db_test_database_name or f"{app_config.db_name}_test"
app_config.db_name = _TEST_DB_NAME

_TEST_DB_CREDS = {
    "drivername": app_config.db_driver_name,
    "username": app_config.db_user,
    "host": app_config.db_host,
    "port": app_config.db_port,
    "database": _TEST_DB_NAME,
    "password": app_config.db_pass,
}

import psycopg2  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.security.http import HTTPAuthorizationCredentials, HTTPBearer  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.engine import URL  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from unittest.mock import AsyncMock, MagicMock  # noqa: E402

from src.config.postgres.db_config import get_session  # noqa: E402
from src.main import app  # noqa: E402


@pytest.fixture(scope="session")
def drop_create_db():
    """
    Once per pytest session:
    1. Connect to the 'postgres' system DB and recreate the test database.
    2. Run 'alembic upgrade head' on the empty test database.
    3. Execute tests/dump_data/dump_data_setup.sql (DISABLE TRIGGER ALL).
    4. For each tests/dump_data/dumps/dump_<table>.json, load rows into the
       matching table via COPY FROM STDIN.
    5. Execute tests/dump_data/dump_data_after.sql (ENABLE TRIGGER ALL).
    """
    admin_params = {
        "database": "postgres",
        "user": _TEST_DB_CREDS["username"],
        "password": _TEST_DB_CREDS["password"],
        "host": _TEST_DB_CREDS["host"],
        "port": _TEST_DB_CREDS["port"],
    }
    conn = psycopg2.connect(**admin_params)
    conn.autocommit = True
    with conn.cursor() as cursor:
        cursor.execute(f'DROP DATABASE IF EXISTS "{_TEST_DB_NAME}"')
        cursor.execute(f'CREATE DATABASE "{_TEST_DB_NAME}" WITH OWNER "{_TEST_DB_CREDS["username"]}"')
        cursor.execute(f'GRANT ALL PRIVILEGES ON DATABASE "{_TEST_DB_NAME}" TO "{_TEST_DB_CREDS["username"]}"')
    conn.close()

    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")

    test_conn = psycopg2.connect(
        database=_TEST_DB_NAME,
        user=_TEST_DB_CREDS["username"],
        password=_TEST_DB_CREDS["password"],
        host=_TEST_DB_CREDS["host"],
        port=_TEST_DB_CREDS["port"],
    )
    cursor = test_conn.cursor()

    test_conn.autocommit = True
    setup_path = "tests/dump_data/dump_data_setup.sql"
    if os.path.exists(setup_path):
        with open(setup_path, "r", encoding="utf-8") as f:
            cursor.execute(f.read())

    dump_files = sorted(glob.glob("tests/dump_data/dumps/dump_*.json"))
    test_conn.autocommit = False
    for dump_file in dump_files:
        table = os.path.basename(dump_file).removeprefix("dump_").removesuffix(".json")
        with open(dump_file, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if not rows:
            continue
        fields = [field.strip() for field in rows[0]]
        stream = io.StringIO()
        for row in rows:
            stream.write("\t".join(["\\N" if row.get(field) is None else str(row[field]) for field in fields]) + "\n")
        stream.seek(0)
        cursor.copy_from(stream, table, columns=fields)
    test_conn.commit()

    test_conn.autocommit = True
    after_path = "tests/dump_data/dump_data_after.sql"
    if os.path.exists(after_path):
        with open(after_path, "r", encoding="utf-8") as f:
            cursor.execute(f.read())
    cursor.close()
    test_conn.close()
    return True


@pytest.fixture(scope="session")
async def test_engine(drop_create_db):
    """
    Session-scoped async engine bound to the test database and to the session
    event loop. Both async_test_session and the client fixture share it so
    every DB-touching coroutine lives in the same loop — otherwise asyncpg
    raises "Task got Future attached to a different loop".
    """
    database_url = URL.create(**_TEST_DB_CREDS)
    engine = create_async_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=15,
        max_overflow=30,
        pool_timeout=100.0,
    )
    yield engine
    await engine.dispose()


@pytest.fixture(scope="session")
def test_session_maker(test_engine):
    """Session-scoped async_sessionmaker over the test engine."""
    return async_sessionmaker(test_engine, expire_on_commit=False, class_=AsyncSession)


@pytest.fixture(scope="session")
async def async_test_session(test_session_maker):
    """
    Session-scoped AsyncSession bound to the test database seeded with dumps.
    A single session for the whole run: commits from one test are visible to
    the next. For isolated data, create a local fixture with add() and cleanup
    in the yield block.
    """
    async with test_session_maker() as session:
        yield session


@pytest.fixture
def async_session():
    """MagicMock(spec=AsyncSession) for unit tests. Does not hit the database."""
    session = MagicMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    return session


@pytest.fixture(scope="session")
async def client(test_session_maker):
    """
    AsyncClient for API integration tests. Hits the real FastAPI app; `get_session`
    is overridden to serve sessions from the test engine so every DB access
    happens in the same session event loop.
    """

    async def _override_get_session():
        async with test_session_maker() as session:
            yield session

    app.dependency_overrides[get_session] = _override_get_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as ac:
        yield ac

    app.dependency_overrides.pop(get_session, None)


@pytest.fixture(autouse=True)
def mock_http_bearer(request, monkeypatch):
    """
    By default every test gets an automatic Bearer token, so protected
    endpoints are reachable without a real Authorization header.
    Mark a test with @pytest.mark.no_auth_mock to skip this patch and
    exercise the real unauthenticated flow (expected 401/403).
    """
    if request.node.get_closest_marker("no_auth_mock"):
        yield
        return

    async def fake_http_bearer_call(self, request):
        return HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")

    monkeypatch.setattr(HTTPBearer, "__call__", fake_http_bearer_call)
    yield
