"""
Pytest configuration and fixtures
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """FastAPI test client fixture"""
    return TestClient(app)


@pytest.fixture
def sample_env_config():
    """Sample environment configuration for testing"""
    return {
        "AIDP_API_URL": "https://api.aidp.store",
        "AIDP_API_KEY": "test_key",
        "MAX_UPLOAD_SIZE": 10485760,
        "STORAGE_PATH": "/tmp/test_storage",
    }
