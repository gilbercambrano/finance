import os
import sys
import subprocess

# Must be set before any app module is imported so database.py creates its engine
# pointing at the test database. CI overrides these via environment variables.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5433/finanzas_test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from httpx import AsyncClient, ASGITransport

_ADMIN_URL = "postgresql+psycopg://postgres:postgres@{}:{}/postgres".format(
    os.environ.get("PGHOST", "localhost"),
    os.environ.get("PGPORT", "5433"),
)
_TEST_DB_URL = os.environ["DATABASE_URL"]


# ---------------------------------------------------------------------------
# Session-scoped: create DB once, run Alembic, drop at the end
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _db_setup():
    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS finanzas_test WITH (FORCE)"))
        conn.execute(text("CREATE DATABASE finanzas_test"))
    admin.dispose()

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
        capture_output=True,
    )

    yield

    admin = create_engine(_ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(text("DROP DATABASE IF EXISTS finanzas_test WITH (FORCE)"))
    admin.dispose()


# ---------------------------------------------------------------------------
# Function-scoped: one transaction per test, always rolled back
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
def db(_db_setup):
    from app.database import engine
    conn = engine.connect()
    txn = conn.begin()
    session = Session(bind=conn, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    txn.rollback()
    conn.close()


def _db_override(session: Session):
    def _get():
        yield session
    return _get


def _transport():
    from app.main import app
    return ASGITransport(app=app)


# ---------------------------------------------------------------------------
# HTTP clients
# ---------------------------------------------------------------------------

@pytest.fixture(scope="function")
async def client(db):
    from app.main import app
    from app.database import get_db
    app.dependency_overrides[get_db] = _db_override(db)
    async with AsyncClient(transport=_transport(), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def _register(c: AsyncClient, email: str, password: str = "Test1234!") -> dict:
    r = await c.post("/api/auth/register", json={
        "email": email,
        "password": password,
        "full_name": email.split("@")[0],
    })
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture(scope="function")
async def auth_client(db):
    from app.main import app
    from app.database import get_db
    app.dependency_overrides[get_db] = _db_override(db)
    async with AsyncClient(transport=_transport(), base_url="http://test") as c:
        await _register(c, "user@test.com")
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def two_auth_clients(db):
    from app.main import app
    from app.database import get_db
    app.dependency_overrides[get_db] = _db_override(db)
    async with (
        AsyncClient(transport=_transport(), base_url="http://test") as ca,
        AsyncClient(transport=_transport(), base_url="http://test") as cb,
    ):
        await _register(ca, "usera@test.com")
        await _register(cb, "userb@test.com")
        yield ca, cb
    app.dependency_overrides.clear()
