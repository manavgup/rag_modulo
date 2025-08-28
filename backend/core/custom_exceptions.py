"""Custom exceptions for the application with strong typing."""

from typing import Optional, Any, Dict, Union
from pydantic import ValidationError as PydanticValidationError


class BaseCustomException(Exception):
    """Base class for custom exceptions."""
    
    def __init__(
        self, 
        message: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize base custom exception.
        
        Args:
            message: Error message
            status_code: HTTP status code
            details: Additional error details
        """
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details
        }


class UnsupportedFileTypeError(BaseCustomException):
    """Exception raised for unsupported file types."""
    
    def __init__(
        self,
        file_type: str,
        supported_types: list[str],
        message: Optional[str] = None
    ) -> None:
        """Initialize unsupported file type error.
        
        Args:
            file_type: The unsupported file type
            supported_types: List of supported file types
            message: Optional custom error message
        """
        super().__init__(
            message or f"Unsupported file type: {file_type}. Supported types: {', '.join(supported_types)}",
            status_code=400,
            details={
                "file_type": file_type,
                "supported_types": supported_types
            }
        )


class DocumentProcessingError(BaseCustomException):
    """Exception raised for errors during document processing."""
    
    def __init__(
        self,
        doc_id: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize document processing error.
        
        Args:
            doc_id: Document identifier
            error_type: Type of processing error
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=500,
            details={
                "document_id": doc_id,
                "error_type": error_type,
                **(details or {})
            }
        )


class DocumentStorageError(BaseCustomException):
    """Exception raised for errors during document storage."""
    
    def __init__(
        self,
        doc_id: str,
        storage_path: str,
        error_type: str,
        message: str
    ) -> None:
        """Initialize document storage error.
        
        Args:
            doc_id: Document identifier
            storage_path: Attempted storage path
            error_type: Type of storage error
            message: Error message
        """
        super().__init__(
            message,
            status_code=500,
            details={
                "document_id": doc_id,
                "storage_path": storage_path,
                "error_type": error_type
            }
        )


class DocumentIngestionError(BaseCustomException):
    """Exception raised for errors during document ingestion."""
    
    def __init__(
        self,
        doc_id: str,
        stage: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize document ingestion error.
        
        Args:
            doc_id: Document identifier
            stage: Ingestion stage where error occurred
            error_type: Type of ingestion error
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=500,
            details={
                "document_id": doc_id,
                "stage": stage,
                "error_type": error_type,
                **(details or {})
            }
        )


class NotFoundException(BaseCustomException):
    """Exception raised when a requested resource is not found."""
    
    def __init__(
        self,
        resource_type: str,
        resource_id: Any,
        message: Optional[str] = None
    ) -> None:
        """Initialize not found error.
        
        Args:
            resource_type: Type of resource not found
            resource_id: Identifier of resource
            message: Optional custom error message
        """
        super().__init__(
            message or f"{resource_type} with id {resource_id} not found",
            status_code=404,
            details={
                "resource_type": resource_type,
                "resource_id": str(resource_id)
            }
        )


# Alias for backward compatibility
NotFoundError = NotFoundException


class ValidationError(BaseCustomException):
    """Exception raised when data validation fails."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize validation error.
        
        Args:
            message: Error message
            field: Field that failed validation
            value: Invalid value
            details: Additional validation details
        """
        super().__init__(
            message,
            status_code=400,
            details={
                "field": field,
                "value": value,
                **(details or {})
            }
        )


class ProviderValidationError(ValidationError):
    """Exception raised when LLM provider validation fails.
    
    This exception handles validation errors specific to LLM providers,
    including Pydantic validation failures for provider schemas.
    """
    
    def __init__(
        self,
        provider_name: str,
        validation_error: Union[PydanticValidationError, str],
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize provider validation error.
        
        Args:
            provider_name: Name of the provider
            validation_error: Pydantic validation error or error message
            field: Field that failed validation
            value: Invalid value
            details: Additional validation details
        """
        if isinstance(validation_error, PydanticValidationError):
            error_details = {
                "errors": [
                    {
                        "loc": [".".join(str(loc) for loc in error["loc"])],
                        "msg": error["msg"],
                        "type": error["type"]
                    }
                    for error in validation_error.errors()
                ]
            }
            message = f"Provider validation failed for {provider_name}: {validation_error}"
        else:
            error_details = {}
            message = str(validation_error)

        super().__init__(
            message,
            field=field,
            value=value,
            details={
                "provider": provider_name,
                **error_details,
                **(details or {})
            }
        )


class LLMParameterError(BaseCustomException):
    """Exception raised for errors related to LLM parameters."""
    
    def __init__(
        self,
        param_name: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize LLM parameter error.
        
        Args:
            param_name: Name of the parameter
            error_type: Type of parameter error
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=400,
            details={
                "parameter": param_name,
                "error_type": error_type,
                **(details or {})
            }
        )


class DuplicateEntryError(ValidationError):
    """Exception raised when attempting to create duplicate LLM parameters."""
    
    def __init__(
        self,
        param_name: str,
        message: Optional[str] = None
    ) -> None:
        """Initialize duplicate parameter error.
        
        Args:
            param_name: Name of duplicate parameter
            message: Optional custom error message
        """
        super().__init__(
            message or f"Parameter set with name '{param_name}' already exists",
            field="name",
            value=param_name,
            details={"parameter_name": param_name}
        )


class DefaultParameterError(ValidationError):
    """Exception raised for errors related to default parameter operations."""
    
    def __init__(
        self,
        operation: str,
        param_name: str,
        message: Optional[str] = None
    ) -> None:
        """Initialize default parameter error.
        
        Args:
            operation: Operation that caused the error
            param_name: Name of parameter set
            message: Optional custom error message
        """
        super().__init__(
            message or f"Cannot {operation} default parameter set '{param_name}'",
            field="is_default",
            value=True,
            details={
                "operation": operation,
                "parameter_name": param_name
            }
        )


class PromptTemplateNotFoundError(NotFoundException):
    """Exception raised when a prompt template is not found."""
    
    def __init__(
        self,
        template_id: str,
        message: Optional[str] = None
    ) -> None:
        """Initialize prompt template not found error.
        
        Args:
            template_id: ID of the template
            message: Optional custom error message
        """
        super().__init__(
            "PromptTemplate",
            template_id,
            message or f"Prompt template with id {template_id} not found"
        )


class PromptTemplateConflictError(ValidationError):
    """Exception raised when there is a conflict with prompt templates."""
    def __init__(self, template_name: str, provider_id: str, message: str):
        self.template_name = template_name
        self.provider_id = provider_id
        self.message = message
        super().__init__(f"Template conflict for '{template_name}' with provider '{provider_id}': {message}")


class InvalidPromptTemplateError(ValidationError):
    """Exception raised when prompt template validation fails."""
    
    def __init__(
        self,
        template_id: str,
        reason: str,
        message: Optional[str] = None
    ) -> None:
        """Initialize invalid prompt template error.
        
        Args:
            template_id: ID of the template
            reason: Reason for validation failure
            message: Optional custom error message
        """
        super().__init__(
            message or f"Invalid prompt template: {reason}",
            field="template",
            value=template_id,
            details={
                "template_id": template_id,
                "reason": reason
            }
        )


class LLMProviderError(BaseCustomException):
    """Exception raised for errors during LLM provider operations.
    
    This exception handles errors that occur during:
    - Provider initialization
    - Text generation
    - Streaming generation
    - Embedding generation
    - Client operations
    """
    
    def __init__(
        self,
        provider: str,
        error_type: str,
        message: str,
        operation: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize LLM provider error.
        
        Args:
            provider: Name of the LLM provider (e.g., watsonx, openai, anthropic)
            error_type: Type of error (e.g., initialization, authentication, rate_limit)
            message: Error message
            operation: Optional operation that failed (e.g., generate, embed)
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=500,
            details={
                "provider": provider,
                "error_type": error_type,
                **({"operation": operation} if operation else {}),
                **(details or {})
            }
        )


class ConfigurationError(BaseCustomException):
    """Exception raised for general configuration errors."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error message describing the configuration issue
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=500,
            details=details or {}
        )


class ProviderConfigError(BaseCustomException):
    """Exception raised for errors related to provider configuration."""
    
    def __init__(
        self,
        provider: str,
        model_id: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize provider configuration error.
        
        Args:
            provider: Name of the provider
            model_id: Model identifier
            error_type: Type of configuration error
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=400,
            details={
                "provider": provider,
                "model_id": model_id,
                "error_type": error_type,
                **(details or {})
            }
        )


class QuestionGenerationError(BaseCustomException):
    """Exception raised for failures in the question generation process."""
    
    def __init__(
        self,
        collection_id: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize question generation error.
        
        Args:
            collection_id: Collection identifier
            error_type: Type of generation error
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=500,
            details={
                "collection_id": collection_id,
                "error_type": error_type,
                **(details or {})
            }
        )


class EmptyDocumentError(BaseCustomException):
    """Exception raised when no valid text chunks are found."""
    
    def __init__(
        self,
        collection_id: str,
        message: Optional[str] = None
    ) -> None:
        """Initialize empty document error.
        
        Args:
            collection_id: Collection identifier
            message: Optional custom error message
        """
        super().__init__(
            message or f"No valid text chunks found in documents for collection {collection_id}",
            status_code=400,
            details={"collection_id": collection_id}
        )


class CollectionProcessingError(BaseCustomException):
    """Exception raised for general collection processing failures."""
    
    def __init__(
        self,
        collection_id: str,
        stage: str,
        error_type: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize collection processing error.
        
        Args:
            collection_id: Collection identifier
            stage: Processing stage where error occurred
            error_type: Type of processing error
            message: Error message
            details: Additional error details
        """
        super().__init__(
            message,
            status_code=500,
            details={
                "collection_id": collection_id,
                "stage": stage,
                "error_type": error_type,
                **(details or {})
            }
        )

class RepositoryError(BaseCustomException):
    """Exception raised for repository/database-related errors."""

    def __init__(
        self,
        message: str,
        details: Optional[dict] = None
    ) -> None:
        """Initialize repository error.
        
        Args:
            message: Description of the error.
            details: Optional dictionary with additional error details.
        """
        super().__init__(
            message=message,
            status_code=500,
            details=details or {}
        )

class ModelValidationError(ValidationError):
    """Exception raised when LLM model validation fails.
    
    This exception handles validation errors specific to LLM models,
    including Pydantic validation failures for model schemas.
    """
    
    def __init__(
        self,
        field: str,
        message: str,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize model validation error.
        
        Args:
            field: Field that failed validation
            message: Error message describing the validation failure
            value: Optional invalid value that caused the error
            details: Additional validation details
        """
        super().__init__(
            message=message,
            field=field,
            value=value,
            details={
                "validation_type": "model",
                **(details or {})
            }
        )


class ModelConfigError(BaseCustomException):
    """Exception raised for errors related to model configuration.
    
    This exception handles configuration errors specific to LLM models,
    such as invalid model settings, missing required configurations,
    or incompatible model configurations.
    """
    
    def __init__(
        self,
        field: str,
        message: str,
        model_id: Optional[str] = None,
        provider_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize model configuration error.
        
        Args:
            field: Configuration field that caused the error
            message: Error message describing the configuration issue
            model_id: Optional identifier of the model
            provider_id: Optional identifier of the provider
            details: Additional error details
        """
        error_details = {
            "field": field,
            "config_type": "model"
        }
        
        if model_id:
            error_details["model_id"] = model_id
        if provider_id:
            error_details["provider_id"] = provider_id
        if details:
            error_details.update(details)

        super().__init__(
            message=message,
            status_code=400,
            details=error_details
        )
