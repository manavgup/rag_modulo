"""Domain-specific exceptions for the RAG solution.

These exceptions should be raised by repositories and services to indicate
business logic errors. They should be caught and converted to HTTP responses
only at the router layer.
"""

from typing import Optional, Any, Dict


class DomainError(Exception):
    """Base class for all domain exceptions."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(DomainError):
    """Raised when a requested resource cannot be found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
        identifier: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.identifier = identifier or resource_id
        
        message = f"{resource_type} not found"
        if self.identifier:
            message = f"{message}: {self.identifier}"
        
        super().__init__(message, details)


class AlreadyExistsError(DomainError):
    """Raised when attempting to create a resource that already exists."""
    
    def __init__(
        self,
        resource_type: str,
        field: str,
        value: str,
        details: Optional[Dict[str, Any]] = None
    ):
        self.resource_type = resource_type
        self.field = field
        self.value = value
        
        message = f"{resource_type} with {field}='{value}' already exists"
        super().__init__(message, details)


class ValidationError(DomainError):
    """Raised when business validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.field = field
        if field:
            message = f"Validation error on field '{field}': {message}"
        super().__init__(message, details)


class OperationNotAllowedError(DomainError):
    """Raised when an operation is not allowed based on current state."""
    
    def __init__(self, operation: str, reason: str, details: Optional[Dict[str, Any]] = None):
        self.operation = operation
        self.reason = reason
        message = f"Operation '{operation}' not allowed: {reason}"
        super().__init__(message, details)


class ResourceConflictError(DomainError):
    """Raised when there's a conflict with the current state of a resource."""
    
    def __init__(self, resource_type: str, conflict: str, details: Optional[Dict[str, Any]] = None):
        self.resource_type = resource_type
        self.conflict = conflict
        message = f"{resource_type} conflict: {conflict}"
        super().__init__(message, details)


class ExternalServiceError(DomainError):
    """Raised when an external service call fails."""
    
    def __init__(self, service: str, operation: str, reason: str, details: Optional[Dict[str, Any]] = None):
        self.service = service
        self.operation = operation
        self.reason = reason
        message = f"External service '{service}' failed during '{operation}': {reason}"
        super().__init__(message, details)


class InsufficientPermissionsError(DomainError):
    """Raised when a user doesn't have required permissions."""
    
    def __init__(self, action: str, resource: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.action = action
        self.resource = resource
        message = f"Insufficient permissions for action '{action}'"
        if resource:
            message = f"{message} on resource '{resource}'"
        super().__init__(message, details)


class ConfigurationError(DomainError):
    """Raised when there's a configuration issue."""
    
    def __init__(self, component: str, issue: str, details: Optional[Dict[str, Any]] = None):
        self.component = component
        self.issue = issue
        message = f"Configuration error in '{component}': {issue}"
        super().__init__(message, details)