# base_test.py

import pytest
import jwt
from fastapi.testclient import TestClient
from unittest.mock import patch
from typing import Dict, Any

from core.config import settings

class BaseTestRouter:
    """Base class for all router tests."""
    
    # Test user data
    TEST_USER = {
        "sub": "test-ibm-id",
        "email": "test@example.com",
        "name": "Test User",
        "uuid": "test-uuid",
        "role": "admin"
    }
    
    TEST_JWT = jwt.encode(TEST_USER, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)

    @pytest.fixture(autouse=True)
    def setup(self, test_client: TestClient, auth_headers: Dict[str, str]):
        """Setup test environment."""
        self.client = test_client
        self.auth_headers = auth_headers
        
        # Mock JWT verification
        def mock_verify(token):
            if token == "mock_token_for_testing" or token == self.TEST_JWT:
                return self.TEST_USER
            raise jwt.InvalidTokenError("Invalid token")

        with patch("auth.oidc.verify_jwt_token", side_effect=mock_verify), \
             patch("core.authentication_middleware.verify_jwt_token", side_effect=mock_verify):
            return

    def make_request(
        self, 
        method: str, 
        url: str, 
        authenticated: bool = True,
        **kwargs
    ) -> Any:
        """Make an HTTP request with optional authentication.
        
        Args:
            method: HTTP method (get, post, put, delete)
            url: Endpoint URL
            authenticated: Whether to include auth headers
            **kwargs: Additional arguments to pass to the request
        """
        if authenticated:
            headers = kwargs.get('headers', {})
            headers.update(self.auth_headers)
            kwargs['headers'] = headers

        request_method = getattr(self.client, method.lower())
        return request_method(url, **kwargs)

    def get(self, url: str, authenticated: bool = True, **kwargs) -> Any:
        """Make a GET request."""
        return self.make_request('GET', url, authenticated, **kwargs)

    def post(self, url: str, authenticated: bool = True, **kwargs) -> Any:
        """Make a POST request."""
        return self.make_request('POST', url, authenticated, **kwargs)

    def put(self, url: str, authenticated: bool = True, **kwargs) -> Any:
        """Make a PUT request."""
        return self.make_request('PUT', url, authenticated, **kwargs)

    def delete(self, url: str, authenticated: bool = True, **kwargs) -> Any:
        """Make a DELETE request."""
        return self.make_request('DELETE', url, authenticated, **kwargs)

    @staticmethod
    def assert_unauthorized(response: Any) -> None:
        """Assert that a response indicates unauthorized access."""
        assert response.status_code in (401, 404)
        
    @staticmethod
    def assert_forbidden(response: Any) -> None:
        """Assert that a response indicates forbidden access."""
        assert response.status_code in (403, 404)
        
    @staticmethod
    def assert_success(response: Any) -> None:
        """Assert that a response indicates success."""
        assert response.status_code in (200, 201, 204)