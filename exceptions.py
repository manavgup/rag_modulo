class UnsupportedFileTypeError(Exception):
    """Exception raised for unsupported file types."""
    pass

class DocumentProcessingError(Exception):
    """Exception raised for errors during document processing."""
    pass

class DocumentStorageError(Exception):
    """Exception raised for errors during document storage."""
    pass

class DocumentIngestionError(Exception):
    """Exception raised for errors during document ingestion."""
    pass

