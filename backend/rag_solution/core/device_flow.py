"""Device Authorization Flow utilities and models.

This module provides utilities for implementing OAuth 2.0 Device Authorization Flow
(RFC 8628) with IBM OIDC provider, building on the existing authentication infrastructure.
"""

import secrets
import string
from datetime import datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

from pydantic import BaseModel, Field, HttpUrl


class DeviceFlowConfig(BaseModel):
    """Configuration for device authorization flow.

    This builds on the existing IBM OIDC configuration in the application.
    """

    client_id: str = Field(..., description="IBM OIDC client ID")
    client_secret: str = Field(..., description="IBM OIDC client secret")
    device_auth_url: HttpUrl = Field(..., description="IBM device authorization endpoint")
    token_url: HttpUrl = Field(..., description="IBM token endpoint")
    default_interval: int = Field(default=5, ge=1, le=60, description="Default polling interval in seconds")
    max_interval: int = Field(default=60, ge=1, le=300, description="Maximum polling interval in seconds")
    default_expires_in: int = Field(
        default=600, ge=60, le=1800, description="Default device code expiration in seconds"
    )

    @classmethod
    def from_env(cls) -> "DeviceFlowConfig":
        """Create configuration from environment variables.

        Uses the same environment variables as the existing OIDC implementation.
        """
        import os

        return cls(
            client_id=os.getenv("IBM_CLIENT_ID", ""),
            client_secret=os.getenv("IBM_CLIENT_SECRET", ""),
            device_auth_url=HttpUrl(
                os.getenv(
                    "OIDC_DEVICE_AUTH_URL",
                    "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/device_authorization",
                )
            ),
            token_url=HttpUrl(
                os.getenv("OIDC_TOKEN_URL", "https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/token")
            ),
            default_interval=int(os.getenv("DEVICE_FLOW_INTERVAL", "5")),
            max_interval=int(os.getenv("DEVICE_FLOW_MAX_INTERVAL", "60")),
            default_expires_in=int(os.getenv("DEVICE_FLOW_EXPIRES_IN", "600")),
        )


class DeviceFlowRecord(BaseModel):
    """Device flow authorization record."""

    device_code: str = Field(..., description="Device code for polling")
    user_code: str = Field(..., description="User-friendly code for display")
    verification_uri: str = Field(..., description="URI for user to visit")
    verification_uri_complete: str | None = Field(None, description="Complete URI with embedded user code")
    expires_at: datetime = Field(..., description="When the device code expires")
    interval: int = Field(default=5, description="Recommended polling interval in seconds")
    status: str = Field(default="pending", description="Authorization status: pending, authorized, expired, denied")
    user_id: str | None = Field(None, description="User ID after authorization")

    def is_expired(self) -> bool:
        """Check if the device code has expired."""
        return datetime.now() >= self.expires_at

    def time_remaining(self) -> int:
        """Get remaining time in seconds before expiration."""
        if self.is_expired():
            return 0
        return int((self.expires_at - datetime.now()).total_seconds())


class DeviceFlowStorage:
    """In-memory storage for device flow records.

    In production, this could be replaced with Redis or database storage.
    For this implementation, we use simple in-memory storage with automatic cleanup.
    """

    def __init__(self) -> None:
        self._records: dict[str, DeviceFlowRecord] = {}

    def store_record(self, record: DeviceFlowRecord) -> None:
        """Store a device flow record."""
        self._records[record.device_code] = record

    def get_record(self, device_code: str) -> DeviceFlowRecord | None:
        """Get a device flow record by device code."""
        record = self._records.get(device_code)
        if record and record.is_expired():
            # Auto-cleanup expired records
            del self._records[device_code]
            return None
        return record

    def update_record(self, record: DeviceFlowRecord) -> None:
        """Update an existing device flow record."""
        if record.device_code in self._records:
            self._records[record.device_code] = record

    def delete_record(self, device_code: str) -> None:
        """Delete a device flow record."""
        self._records.pop(device_code, None)

    def get_all_records(self) -> list[DeviceFlowRecord]:
        """Get all non-expired records."""
        self.cleanup_expired()
        return list(self._records.values())

    def cleanup_expired(self) -> None:
        """Remove all expired records."""
        now = datetime.now()
        expired_codes = [code for code, record in self._records.items() if record.expires_at <= now]
        for code in expired_codes:
            del self._records[code]


# Global storage instance (in production, use dependency injection)
_device_flow_storage = DeviceFlowStorage()


def get_device_flow_storage() -> DeviceFlowStorage:
    """Get the device flow storage instance."""
    return _device_flow_storage


def generate_device_code() -> str:
    """Generate a secure device code for internal use."""
    # Generate 32-character alphanumeric string
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def generate_user_code() -> str:
    """Generate a user-friendly code for display.

    Returns a code in format XXXX-XXXX using uppercase letters and numbers,
    avoiding potentially confusing characters.
    """
    # Use only uppercase letters and digits, excluding confusing characters
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # No I,O,0,1 to avoid confusion

    # Generate 8 characters in XXXX-XXXX format
    code_chars = [secrets.choice(alphabet) for _ in range(8)]
    return f"{code_chars[0]}{code_chars[1]}{code_chars[2]}{code_chars[3]}-{code_chars[4]}{code_chars[5]}{code_chars[6]}{code_chars[7]}"


def validate_device_code(device_code: str | None) -> bool:
    """Validate device code format."""
    if not device_code or not isinstance(device_code, str):
        return False
    if len(device_code) < 20:
        return False
    return device_code.replace("-", "").replace("_", "").isalnum()


def validate_user_code(user_code: str | None) -> bool:
    """Validate user code format (XXXX-XXXX)."""
    if not user_code or not isinstance(user_code, str):
        return False
    if len(user_code) != 9:  # XXXX-XXXX format
        return False
    if user_code[4] != "-":
        return False

    # Check each part is alphanumeric and uppercase
    parts = user_code.split("-")
    if len(parts) != 2:
        return False

    for part in parts:
        if len(part) != 4 or not part.isalnum():
            return False
        # Check that all alphabetic characters are uppercase
        if not all(c.isupper() or c.isdigit() for c in part):
            return False

    return True


def calculate_next_polling_interval(base_interval: int, attempt: int, max_interval: int = 60) -> int:
    """Calculate next polling interval with exponential backoff.

    Args:
        base_interval: Base polling interval in seconds
        attempt: Current attempt number (0-based)
        max_interval: Maximum interval to respect

    Returns:
        Next polling interval in seconds
    """
    if attempt <= 1:
        return base_interval

    # Exponential backoff: base_interval * 2^(attempt-1)
    interval = int(base_interval * (2 ** (attempt - 1)))
    return min(interval, max_interval)


def parse_device_flow_error(error_code: str) -> dict[str, Any]:
    """Parse device flow error codes into user-friendly information.

    Based on RFC 8628 error codes.
    """
    error_info = {
        "authorization_pending": {
            "code": "authorization_pending",
            "message": "User has not yet completed authorization",
            "retry": True,
        },
        "slow_down": {"code": "slow_down", "message": "Polling too frequently, slow down", "retry": True},
        "expired_token": {"code": "expired_token", "message": "Device code has expired", "retry": False},
        "access_denied": {"code": "access_denied", "message": "User denied the authorization request", "retry": False},
        "invalid_grant": {"code": "invalid_grant", "message": "Invalid device code or grant", "retry": False},
    }

    return error_info.get(error_code, {"code": error_code, "message": f"Unknown error: {error_code}", "retry": False})


def build_verification_uri_complete(base_uri: str, user_code: str) -> str:
    """Build complete verification URI with embedded user code.

    Args:
        base_uri: Base verification URI
        user_code: User code to embed

    Returns:
        Complete URI with user_code parameter
    """
    parsed = urlparse(base_uri)
    query_params = parse_qs(parsed.query)
    query_params["user_code"] = [user_code]

    # Reconstruct URL with new query parameters
    new_query = urlencode(query_params, doseq=True)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"


def calculate_device_flow_timeout(expires_in: int, interval: int, buffer_seconds: int = 0) -> dict[str, Any]:
    """Calculate device flow timeout information.

    Args:
        expires_in: Device code expiration time in seconds
        interval: Polling interval in seconds
        buffer_seconds: Buffer time to subtract from total timeout

    Returns:
        Dictionary with timeout information
    """
    total_timeout = expires_in - buffer_seconds
    max_attempts = total_timeout // interval if interval > 0 else 0
    expires_at = datetime.now() + timedelta(seconds=expires_in)

    return {
        "total_timeout": total_timeout,
        "max_attempts": max_attempts,
        "expires_at": expires_at,
        "interval": interval,
        "buffer_seconds": buffer_seconds,
    }
