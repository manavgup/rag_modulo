"""MCP Resources for RAG Modulo.

This module defines MCP resources that expose RAG Modulo data:
- rag://collection/{id}/documents: List documents in a collection
- rag://collection/{id}/stats: Collection statistics
- rag://search/{query}/results: Cached search results
"""

import contextlib
import json
from collections.abc import Generator
from contextlib import contextmanager
from uuid import UUID

from mcp.server.fastmcp import FastMCP
from sqlalchemy.orm import Session

from core.config import get_settings
from core.enhanced_logging import get_logger
from rag_solution.file_management.database import get_db
from rag_solution.services.collection_service import CollectionService
from rag_solution.services.file_management_service import FileManagementService

logger = get_logger(__name__)


@contextmanager
def db_session_context() -> Generator[Session, None, None]:
    """Context manager for proper database session lifecycle.

    This wraps the get_db() generator to ensure proper cleanup,
    including rollback on errors and session closure.

    Yields:
        Session: Database session that is properly managed

    Example:
        with db_session_context() as db:
            result = db.query(Model).all()

    Raises:
        Exception: Any database errors are propagated after cleanup
    """
    db_gen = get_db()
    db_session = next(db_gen)
    try:
        yield db_session
    finally:
        # Exhaust the generator to trigger its cleanup code
        with contextlib.suppress(StopIteration):
            next(db_gen)


def register_rag_resources(mcp: FastMCP) -> None:
    """Register all RAG resources with the MCP server.

    Args:
        mcp: The FastMCP server instance to register resources with
    """

    @mcp.resource("rag://collection/{collection_id}/documents")  # type: ignore[misc]
    def get_collection_documents(collection_id: str) -> str:
        """Get list of documents in a collection.

        Returns a JSON-formatted list of all documents in the specified
        collection, including metadata like filename, type, and size.

        Args:
            collection_id: UUID of the collection

        Returns:
            JSON string containing document list
        """
        logger.info("Fetching documents for collection %s", collection_id)

        try:
            # Validate UUID format first
            collection_uuid = UUID(collection_id)
        except ValueError as e:
            logger.warning("Invalid collection_id: %s", e)
            return json.dumps({"error": f"Invalid collection_id: {e}"})

        try:
            settings = get_settings()

            with db_session_context() as db_session:
                file_service = FileManagementService(db=db_session, settings=settings)

                # Get files in collection
                files = file_service.get_files_by_collection(collection_uuid)

                documents = [
                    {
                        "id": str(f.id),
                        "filename": f.filename,
                        "file_type": f.file_type,
                        "file_size_bytes": f.file_size_bytes,
                        "document_id": f.document_id,
                    }
                    for f in files
                ]

                return json.dumps(
                    {
                        "collection_id": collection_id,
                        "documents": documents,
                        "total": len(documents),
                    },
                    indent=2,
                )

        except Exception as e:
            logger.exception("Failed to fetch collection documents")
            return json.dumps({"error": str(e)})

    @mcp.resource("rag://collection/{collection_id}/stats")  # type: ignore[misc]
    def get_collection_stats(collection_id: str) -> str:
        """Get statistics for a collection.

        Returns statistics about the collection including document count,
        total chunks, vector dimensions, and storage usage.

        Args:
            collection_id: UUID of the collection

        Returns:
            JSON string containing collection statistics
        """
        logger.info("Fetching stats for collection %s", collection_id)

        try:
            settings = get_settings()
            collection_uuid = UUID(collection_id)

            with db_session_context() as db_session:
                collection_service = CollectionService(db=db_session, settings=settings)

                # Get collection
                collection = collection_service.get_collection(collection_uuid)

                if not collection:
                    return json.dumps({"error": f"Collection {collection_id} not found"})

                stats = {
                    "collection_id": str(collection.id),
                    "name": collection.name,
                    "status": collection.status.value
                    if hasattr(collection.status, "value")
                    else str(collection.status),
                    "is_private": collection.is_private,
                    "created_at": collection.created_at.isoformat() if collection.created_at else None,
                    "updated_at": collection.updated_at.isoformat() if collection.updated_at else None,
                }

                # Add chunk counts if available
                if hasattr(collection, "total_chunks"):
                    stats["total_chunks"] = collection.total_chunks
                if hasattr(collection, "total_documents"):
                    stats["total_documents"] = collection.total_documents

                return json.dumps(stats, indent=2)

        except ValueError as e:
            logger.warning("Invalid collection_id: %s", e)
            return json.dumps({"error": f"Invalid collection_id: {e}"})
        except Exception as e:
            logger.exception("Failed to fetch collection stats")
            return json.dumps({"error": str(e)})

    @mcp.resource("rag://user/{user_id}/collections")  # type: ignore[misc]
    def get_user_collections(user_id: str) -> str:
        """Get all collections for a user.

        Returns a list of all collections owned by or shared with
        the specified user.

        Args:
            user_id: UUID of the user

        Returns:
            JSON string containing collection list
        """
        logger.info("Fetching collections for user %s", user_id)

        try:
            # Validate UUID format first
            user_uuid = UUID(user_id)
        except ValueError as e:
            logger.warning("Invalid user_id: %s", e)
            return json.dumps({"error": f"Invalid user_id: {e}"})

        try:
            settings = get_settings()

            with db_session_context() as db_session:
                collection_service = CollectionService(db=db_session, settings=settings)

                # Get user's collections
                collections = collection_service.get_user_collections(user_uuid)

                collection_list = [
                    {
                        "id": str(c.id),
                        "name": c.name,
                        "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                        "is_private": c.is_private,
                        "created_at": c.created_at.isoformat() if c.created_at else None,
                    }
                    for c in collections
                ]

                return json.dumps(
                    {
                        "user_id": user_id,
                        "collections": collection_list,
                        "total": len(collection_list),
                    },
                    indent=2,
                )

        except Exception as e:
            logger.exception("Failed to fetch user collections")
            return json.dumps({"error": str(e)})

    logger.info("Registered 3 RAG resources with MCP server")
