import json
import logging
from uuid import uuid4, UUID
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient
from backend.rag_solution.schemas.collection_schema import CollectionInput
from main import app

logger = logging.getLogger(__name__)

client = TestClient(app)

@pytest.fixture
def user_data() -> Dict[str, Any]:
    return {"ibm_id": f"test_ibm_id_{uuid4()}", "email": f"test{uuid4()}@example.com", "name": "Test User"}

# Update other fixtures and tests as necessary.