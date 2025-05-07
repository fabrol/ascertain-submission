import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import subprocess
import time
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv
import logging
import httpx
import asyncio

from src.main import app
from src.database import get_db
from src.config import Settings, settings
from src.models.base import Base


class TestSettings(Settings):
    """Test settings override."""

    DATABASE_URL: str = (
        "postgresql://postgres:postgres@localhost:5433/medical_docs_test"  # Same port, different DB name
    )
    ENVIRONMENT: str = "test"
    DEBUG: bool = True


def wait_for_postgres(host, port, user, password, dbname, max_retries=5):
    """Wait for PostgreSQL to be ready."""
    for i in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host, port=port, user=user, password=password, dbname=dbname
            )
            conn.close()
            return True
        except psycopg2.OperationalError:
            if i == max_retries - 1:
                raise
            time.sleep(2)
    return False


# Load environment variables from .env file if it exists
if os.path.exists(".env"):
    load_dotenv()


def pytest_configure(config):
    """Configure pytest with custom settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test (requires external services)",
    )
    config.addinivalue_line("markers", "asyncio: mark test as async test")


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """Setup test database once for all tests."""
    test_settings = TestSettings()

    # Create test database
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        user="postgres",
        password="postgres",
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS medical_docs_test")
    cur.execute("CREATE DATABASE medical_docs_test")
    cur.close()
    conn.close()

    # Create all tables
    engine = create_engine(test_settings.DATABASE_URL)
    Base.metadata.create_all(engine)

    # Override settings
    app.dependency_overrides[settings.__class__] = lambda: test_settings
    yield

    # Clean up
    app.dependency_overrides.clear()
    engine.dispose()

    # Drop test database
    conn = psycopg2.connect(
        host="localhost",
        port=5433,
        user="postgres",
        password="postgres",
        database="postgres",
    )
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    cur.execute("DROP DATABASE IF EXISTS medical_docs_test")
    cur.close()
    conn.close()


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment before each test.

    This fixture:
    - Sets the environment to 'test'
    - Verifies OpenAI API key is configured
    """
    # Set test environment
    os.environ["ENVIRONMENT"] = "test"

    # Fail if OpenAI API key is not configured
    if not os.getenv("OPENAI_API_KEY"):
        pytest.fail("OpenAI API key not configured. Set OPENAI_API_KEY in .env file.")


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for a test.

    This fixture:
    - Creates a new database connection
    - Starts a transaction
    - Yields a session
    - Rolls back changes and cleans up after the test
    """
    test_settings = TestSettings()
    engine = create_engine(test_settings.DATABASE_URL)
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """Create a test client with real database session.

    This fixture:
    - Overrides the database dependency with the test session
    - Creates and yields a test client
    - Cleans up dependency overrides after the test
    """

    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def setup_logging():
    # Configure logging for specific modules
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("src").setLevel(logging.DEBUG)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    # Add console handler if not already present
    if not root_logger.handlers:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)8s] %(message)s (%(filename)s:%(lineno)s)",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root_logger.addHandler(console_handler)


@pytest.fixture(scope="session")
def event_loop():
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()

    yield loop

    pending = asyncio.tasks.all_tasks(loop)
    if pending:
        loop.run_until_complete(asyncio.gather(*pending))
    loop.run_until_complete(asyncio.sleep(1))

    loop.close()
