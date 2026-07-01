import pytest
import asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from pathlib import Path

from src.api.main import app, app_with_socket
from src.db.logging import Base, get_db, SessionLocal


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db():
    """Create in-memory test database."""
    db_url = "sqlite:///:memory:"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(test_db):
    """Create test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_db)
    session = TestingSessionLocal()

    def override_get_db():
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield session
    session.close()
    app.dependency_overrides.clear()


@pytest.fixture
def client(db_session):
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
async def async_client(db_session):
    """Create async FastAPI test client."""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_celery_app(mocker):
    """Mock Celery app."""
    mock_app = mocker.MagicMock()
    mock_app.AsyncResult = mocker.MagicMock(return_value=mocker.MagicMock(
        state="SUCCESS",
        result={"status": "success", "symbol": "EURUSD=X"}
    ))
    return mock_app


@pytest.fixture
def sample_prediction():
    """Sample prediction data."""
    return {
        "symbol": "EURUSD=X",
        "prediction": 1,
        "prediction_class": "BUY",
        "confidence": 0.85,
        "current_price": 1.0950,
        "metadata": {
            "current_price": 1.0950,
            "timestamp": "2026-07-01T12:00:00Z"
        }
    }


@pytest.fixture
def sample_trade():
    """Sample trade data."""
    return {
        "symbol": "EURUSD=X",
        "action": "BUY",
        "price": 1.0950,
        "quantity": 1.0,
        "notes": "Test trade"
    }
