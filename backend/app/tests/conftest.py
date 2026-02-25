"""
Shared pytest fixtures for the mnsAI test suite.

This file is processed by pytest before any test module is imported, so the
OPENAI_API_KEY env-var is set early enough to allow the OpenAI singleton
clients inside ocrservice.py / jsonextractservice.py to initialise without
hitting the real API.
"""
import os
import uuid

# -----------------------------------------------------------------------
# Must be set BEFORE any app module is imported so the OpenAI singletons
# (ocr_service, json_extract_service) can be created without a real key.
# -----------------------------------------------------------------------
os.environ.setdefault("OPENAI_API_KEY", "sk-test-00000000000000000000000000000000")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from unittest.mock import MagicMock  # noqa: E402

from app.main import app  # noqa: E402
from app.api.deps import get_current_user, get_db  # noqa: E402
from app.models import User  # noqa: E402

# ---------------------------------------------------------------------------
# Fake user reused across tests
# ---------------------------------------------------------------------------
FAKE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

FAKE_USER = User(
    id=FAKE_USER_ID,
    email="test@example.com",
    is_active=True,
    is_superuser=False,
    hashed_password="hashed_pw",
    full_name="Test User",
)


@pytest.fixture
def client():
    """TestClient with auth + DB dependencies stubbed out."""
    app.dependency_overrides[get_current_user] = lambda: FAKE_USER
    app.dependency_overrides[get_db] = lambda: MagicMock()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
