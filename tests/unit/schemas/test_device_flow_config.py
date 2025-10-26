"""Atomic tests for device flow configuration and utilities.

These tests verify device flow configuration parsing, validation,
and utility functions without external dependencies.
"""

from datetime import datetime, timedelta

import pytest


@pytest.mark.atomic
class TestDeviceFlowConfiguration:
    """Test device flow configuration and validation logic."""

    def test_device_flow_config_validation(self):
        """Test device flow configuration validation."""
        from backend.rag_solution.core.config import DeviceFlowConfig

        # Valid configuration
        config = DeviceFlowConfig(
            client_id="test-client-id",
            client_secret="test-secret",
            device_auth_url="https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/device_authorization",
            token_url="https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/token",
            default_interval=5,
            default_expires_in=600,
        )

        assert config.client_id == "test-client-id"
        assert config.default_interval == 5
        assert config.default_expires_in == 600
        assert str(config.device_auth_url).endswith("device_authorization")

    def test_device_flow_config_from_env(self, monkeypatch):
        """Test device flow configuration from environment variables."""
        from backend.rag_solution.core.config import DeviceFlowConfig

        # Set environment variables
        monkeypatch.setenv("IBM_CLIENT_ID", "env-client-id")
        monkeypatch.setenv("IBM_CLIENT_SECRET", "env-secret")
        monkeypatch.setenv("OIDC_DEVICE_AUTH_URL", "https://test.com/device_auth")
        monkeypatch.setenv("OIDC_TOKEN_URL", "https://test.com/token")

        config = DeviceFlowConfig.from_env()

        assert config.client_id == "env-client-id"
        assert config.client_secret == "env-secret"
        assert str(config.device_auth_url) == "https://test.com/device_auth"

    def test_device_flow_config_validation_errors(self):
        """Test device flow configuration validation errors."""
        from backend.rag_solution.core.config import DeviceFlowConfig
        from pydantic import ValidationError

        # Missing required fields
        with pytest.raises(ValidationError) as exc_info:
            DeviceFlowConfig(
                client_id="test-client-id"
                # Missing required fields
            )

        error_details = exc_info.value.errors()
        required_fields = [error["loc"][0] for error in error_details if error["type"] == "missing"]
        assert "client_secret" in required_fields

        # Invalid URLs
        with pytest.raises(ValidationError):
            DeviceFlowConfig(
                client_id="test-client-id",
                client_secret="test-secret",
                device_auth_url="invalid-url",
                token_url="https://valid.com/token",
            )

    def test_device_flow_intervals_validation(self):
        """Test device flow polling interval validation."""
        from backend.rag_solution.core.config import DeviceFlowConfig
        from pydantic import ValidationError

        # Valid intervals
        config = DeviceFlowConfig(
            client_id="test-id",
            client_secret="test-secret",
            device_auth_url="https://test.com/device_auth",
            token_url="https://test.com/token",
            default_interval=5,
            max_interval=60,
            default_expires_in=600,
        )

        assert config.default_interval == 5
        assert config.max_interval == 60

        # Invalid intervals
        with pytest.raises(ValidationError):
            DeviceFlowConfig(
                client_id="test-id",
                client_secret="test-secret",
                device_auth_url="https://test.com/device_auth",
                token_url="https://test.com/token",
                default_interval=0,  # Too small
                default_expires_in=600,
            )


@pytest.mark.atomic
class TestDeviceCodeGeneration:
    """Test device code generation and validation utilities."""

    def test_device_code_format(self):
        """Test device code generation format."""
        from backend.rag_solution.core.device_flow import generate_device_code

        device_code = generate_device_code()

        # Should be a string of appropriate length
        assert isinstance(device_code, str)
        assert len(device_code) >= 20
        assert device_code.isalnum()  # Only alphanumeric

    def test_user_code_format(self):
        """Test user-friendly code generation format."""
        from backend.rag_solution.core.device_flow import generate_user_code

        user_code = generate_user_code()

        # Should be in format XXXX-XXXX
        assert isinstance(user_code, str)
        assert len(user_code) == 9  # 4-1-4 format
        assert user_code[4] == "-"
        assert user_code[:4].isalnum()
        assert user_code[5:].isalnum()

    def test_user_code_uniqueness(self):
        """Test that generated user codes are unique."""
        from backend.rag_solution.core.device_flow import generate_user_code

        codes = {generate_user_code() for _ in range(100)}

        # All codes should be unique
        assert len(codes) == 100

    def test_device_code_validation(self):
        """Test device code validation logic."""
        from backend.rag_solution.core.device_flow import validate_device_code

        # Valid device code
        valid_code = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        assert validate_device_code(valid_code) is True

        # Invalid codes
        assert validate_device_code("") is False
        assert validate_device_code("too-short") is False
        assert validate_device_code("contains-special-chars!") is False
        assert validate_device_code(None) is False

    def test_user_code_validation(self):
        """Test user code validation logic."""
        from backend.rag_solution.core.device_flow import validate_user_code

        # Valid user codes
        assert validate_user_code("ABCD-1234") is True
        assert validate_user_code("WXYZ-9876") is True

        # Invalid user codes
        assert validate_user_code("ABCD1234") is False  # Missing hyphen
        assert validate_user_code("ABC-1234") is False  # Wrong length
        assert validate_user_code("ABCD-123") is False  # Wrong length
        assert validate_user_code("abcd-1234") is False  # Lowercase
        assert validate_user_code("") is False
        assert validate_user_code(None) is False


@pytest.mark.atomic
class TestDeviceFlowStorage:
    """Test device flow temporary storage utilities."""

    def test_device_flow_storage_structure(self):
        """Test device flow storage data structure."""
        from backend.rag_solution.core.device_flow import DeviceFlowRecord, DeviceFlowStorage

        # Create storage
        storage = DeviceFlowStorage()
        assert len(storage.get_all_records()) == 0

        # Create record
        record = DeviceFlowRecord(
            device_code="device123",
            user_code="ABCD-1234",
            verification_uri="https://ibm.com/device",
            expires_at=datetime.now() + timedelta(minutes=10),
            interval=5,
            status="pending",
        )

        assert record.device_code == "device123"
        assert record.user_code == "ABCD-1234"
        assert record.status == "pending"
        assert record.is_expired() is False

    def test_device_flow_record_expiration(self):
        """Test device flow record expiration logic."""
        from backend.rag_solution.core.device_flow import DeviceFlowRecord

        # Expired record
        expired_record = DeviceFlowRecord(
            device_code="device123",
            user_code="ABCD-1234",
            verification_uri="https://ibm.com/device",
            expires_at=datetime.now() - timedelta(minutes=1),  # Expired
            interval=5,
            status="pending",
        )

        assert expired_record.is_expired() is True

        # Valid record
        valid_record = DeviceFlowRecord(
            device_code="device456",
            user_code="WXYZ-5678",
            verification_uri="https://ibm.com/device",
            expires_at=datetime.now() + timedelta(minutes=10),
            interval=5,
            status="pending",
        )

        assert valid_record.is_expired() is False

    def test_device_flow_storage_operations(self):
        """Test device flow storage CRUD operations."""
        from backend.rag_solution.core.device_flow import DeviceFlowRecord, DeviceFlowStorage

        storage = DeviceFlowStorage()

        # Store record
        record = DeviceFlowRecord(
            device_code="device789",
            user_code="TEST-1234",
            verification_uri="https://ibm.com/device",
            expires_at=datetime.now() + timedelta(minutes=10),
            interval=5,
            status="pending",
        )

        storage.store_record(record)
        assert len(storage.get_all_records()) == 1

        # Retrieve record
        retrieved = storage.get_record("device789")
        assert retrieved is not None
        assert retrieved.user_code == "TEST-1234"

        # Update record
        retrieved.status = "authorized"
        storage.update_record(retrieved)

        updated = storage.get_record("device789")
        assert updated.status == "authorized"

        # Delete record
        storage.delete_record("device789")
        assert storage.get_record("device789") is None

    def test_device_flow_storage_cleanup(self):
        """Test automatic cleanup of expired records."""
        from backend.rag_solution.core.device_flow import DeviceFlowRecord, DeviceFlowStorage

        storage = DeviceFlowStorage()

        # Add expired record
        expired_record = DeviceFlowRecord(
            device_code="expired123",
            user_code="EXP1-2345",
            verification_uri="https://ibm.com/device",
            expires_at=datetime.now() - timedelta(minutes=1),
            interval=5,
            status="pending",
        )

        # Add valid record
        valid_record = DeviceFlowRecord(
            device_code="valid456",
            user_code="VAL2-6789",
            verification_uri="https://ibm.com/device",
            expires_at=datetime.now() + timedelta(minutes=10),
            interval=5,
            status="pending",
        )

        storage.store_record(expired_record)
        storage.store_record(valid_record)

        # Check that both records are stored (before cleanup)
        assert len(storage._records) == 2

        # Cleanup expired records
        storage.cleanup_expired()

        records = storage.get_all_records()
        assert len(records) == 1
        assert records[0].device_code == "valid456"


@pytest.mark.atomic
class TestDeviceFlowUtilities:
    """Test device flow utility functions."""

    def test_polling_backoff_calculation(self):
        """Test exponential backoff calculation for polling."""
        from backend.rag_solution.core.device_flow import calculate_next_polling_interval

        # Initial interval
        assert calculate_next_polling_interval(5, 0) == 5  # First poll

        # Exponential backoff
        assert calculate_next_polling_interval(5, 1) == 5  # Second poll
        assert calculate_next_polling_interval(5, 2) == 10  # Third poll
        assert calculate_next_polling_interval(5, 3) == 20  # Fourth poll

        # Respect maximum
        assert calculate_next_polling_interval(5, 10, max_interval=30) == 30

    def test_device_flow_error_parsing(self):
        """Test parsing of device flow error responses."""
        from backend.rag_solution.core.device_flow import parse_device_flow_error

        # Standard OAuth errors
        assert parse_device_flow_error("authorization_pending") == {
            "code": "authorization_pending",
            "message": "User has not yet completed authorization",
            "retry": True,
        }

        assert parse_device_flow_error("slow_down") == {
            "code": "slow_down",
            "message": "Polling too frequently, slow down",
            "retry": True,
        }

        assert parse_device_flow_error("expired_token") == {
            "code": "expired_token",
            "message": "Device code has expired",
            "retry": False,
        }

        assert parse_device_flow_error("access_denied") == {
            "code": "access_denied",
            "message": "User denied the authorization request",
            "retry": False,
        }

    def test_device_flow_url_construction(self):
        """Test construction of device flow URLs."""
        from backend.rag_solution.core.device_flow import build_verification_uri_complete

        base_uri = "https://prepiam.ice.ibmcloud.com/device"
        user_code = "ABCD-1234"

        complete_uri = build_verification_uri_complete(base_uri, user_code)

        assert complete_uri == "https://prepiam.ice.ibmcloud.com/device?user_code=ABCD-1234"

        # Handle existing query parameters
        base_with_params = "https://prepiam.ice.ibmcloud.com/device?lang=en"
        complete_with_params = build_verification_uri_complete(base_with_params, user_code)

        assert complete_with_params == "https://prepiam.ice.ibmcloud.com/device?lang=en&user_code=ABCD-1234"

    def test_device_flow_timeout_calculation(self):
        """Test calculation of device flow timeouts."""
        from backend.rag_solution.core.device_flow import calculate_device_flow_timeout

        # Standard timeout calculation
        expires_in = 600  # 10 minutes
        interval = 5  # 5 seconds

        timeout_info = calculate_device_flow_timeout(expires_in, interval)

        assert timeout_info["total_timeout"] == 600
        assert timeout_info["max_attempts"] == 120  # 600 / 5
        assert timeout_info["expires_at"] > datetime.now()

        # With buffer
        timeout_with_buffer = calculate_device_flow_timeout(expires_in, interval, buffer_seconds=30)
        assert timeout_with_buffer["total_timeout"] == 570  # 600 - 30
