from uuid import uuid4
import pytest
from rag_solution.schemas.user_schema import UserOutput, UserInput
from rag_solution.services.user_service import UserService
from sqlalchemy.orm import Session


@pytest.fixture
def test_user(db_session: Session) -> UserOutput:
    """Create a test user for individual tests."""
    user_service = UserService(db_session)
    test_id = uuid4()
    user = user_service.create_user(UserInput(
        email=f"test_{test_id}@example.com",
        ibm_id=f"test_user_{test_id}",
        name="Test User",
        role="user"
    ))
    yield user
    # Optional cleanup if needed