from typing import Optional, Any, Dict

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

class DuplicateParameterError(ValidationError):
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

class DuplicatePromptTemplateError(ValidationError):
    """Exception raised when attempting to create a duplicate prompt template."""
    
    def __init__(
        self,
        template_name: str,
        provider: str,
        message: Optional[str] = None
    ) -> None:
        """Initialize duplicate prompt template error.
        
        Args:
            template_name: Name of the template
            provider: LLM provider
            message: Optional custom error message
        """
        super().__init__(
            message or f"Prompt template '{template_name}' for provider '{provider}' already exists",
            field="name",
            value=template_name,
            details={
                "template_name": template_name,
                "provider": provider
            }
        )

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
