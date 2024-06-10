class VectorStoreError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, message: str):
        super().__init__(message)


class CollectionError(VectorStoreError):
    """Exception raised for errors related to collection operations."""
    def __init__(self, message: str):
        super().__init__(message)


class DocumentError(VectorStoreError):
    """Exception raised for errors related to document operations."""
    def __init__(self, message: str):
        super().__init__(message)
