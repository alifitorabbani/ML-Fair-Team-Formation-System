import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import init_db, get_db
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.models.models import Base
import asyncio


TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_auth.db"

engine = create_async_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    async def create_tables():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(create_tables())
    yield
    asyncio.run(engine.dispose())


@pytest.mark.asyncio
async def test_admin_login():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/login", json={"email": "rebanialifito@gmail.com"})
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "admin"
        assert "token" in data


@pytest.mark.asyncio
async def test_admin_wrong_email():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/login", json={"email": "wrongadmin@gmail.com"})
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_user_login_not_found():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/api/login", json={"email": "nonexistent@example.com"})
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_admin_access_without_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/dashboard")
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_access_with_invalid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/admin/dashboard", headers={"X-User-Token": "invalid"})
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_admin_access_with_valid_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        login_response = await client.post("/api/login", json={"email": "rebanialifito@gmail.com"})
        token = login_response.json()["token"]
        response = await client.get("/api/admin/dashboard", headers={"X-User-Token": token})
        assert response.status_code == 200


@pytest.mark.asyncio
async def test_initial_system_state():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/system-state")
        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "DRAFT"
