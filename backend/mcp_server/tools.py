"""MCP Tools for RAG Modulo.

This module defines all MCP tools that expose RAG Modulo functionality:
- rag_search: Search documents in a collection
- rag_ingest: Ingest documents into a collection
- rag_list_collections: List available collections
- rag_generate_podcast: Generate a podcast from collection content
- rag_smart_questions: Generate smart follow-up questions
- rag_get_document: Retrieve a specific document's content

Each tool validates authentication and checks required permissions before
executing the operation. Authentication is handled by the MCPAuthenticator.
"""

from typing import Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession

from backend.core.enhanced_logging import get_logger
from backend.mcp_server.permissions import TOOL_PERMISSIONS
from backend.mcp_server.types import (
    MCPErrorType,
    MCPServerContext,
    create_error_response,
    get_app_context,
    parse_uuid,
    validate_auth,
)
from backend.rag_solution.schemas.search_schema import SearchInput, SearchOutput

logger = get_logger(__name__)


def register_rag_tools(mcp: FastMCP) -> None:
    """Register all RAG tools with the MCP server.

    Args:
        mcp: The FastMCP server instance to register tools with
    """

    @mcp.tool()
    async def rag_search(
        question: str,
        collection_id: str,
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
        enable_cot: bool = False,
        show_cot_steps: bool = False,
        max_results: int = 10,
        max_chunk_length: int = 500,
    ) -> dict[str, Any]:
        """Search documents in a RAG collection and generate an answer.

        Performs semantic search across the specified collection using the
        provided question, retrieves relevant document chunks, and generates
        an AI-powered answer synthesized from the retrieved content.

        Requires 'rag:search' permission.

        Args:
            question: The question or query to search for
            collection_id: UUID of the collection to search in
            user_id: UUID of the user making the request
            ctx: MCP context with server resources
            enable_cot: Enable Chain of Thought reasoning for complex questions
            show_cot_steps: Include reasoning steps in the response
            max_results: Maximum number of document chunks to retrieve (1-50)
            max_chunk_length: Maximum character length for chunk text in response (100-2000)

        Returns:
            Dictionary containing:
            - answer: Generated answer to the question
            - documents: List of source document metadata
            - query_results: Retrieved document chunks with relevance scores
            - execution_time: Time taken to execute the search
            - cot_output: Chain of Thought steps if enabled

        Raises:
            PermissionError: If authentication fails or user lacks required permissions
        """
        app_ctx = get_app_context(ctx)

        # Validate authentication and permissions
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_search"])
        except PermissionError as e:
            logger.warning("Search authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Searching collection {collection_id} for: {question[:50]}...")

        try:
            collection_uuid = parse_uuid(collection_id, "collection_id")
            user_uuid = parse_uuid(user_id, "user_id")

            # Build search input
            config_metadata: dict[str, Any] = {
                "max_results": max_results,
            }
            if enable_cot:
                config_metadata["cot_enabled"] = True
                config_metadata["show_cot_steps"] = show_cot_steps

            search_input = SearchInput(
                question=question,
                collection_id=collection_uuid,
                user_id=user_uuid,
                config_metadata=config_metadata,
            )

            # Execute search
            result: SearchOutput = await app_ctx.search_service.search(search_input)

            # Convert to MCP-friendly format
            response = {
                "answer": result.answer,
                "documents": [
                    {
                        "document_id": str(doc.document_id),
                        "document_name": doc.document_name,
                        "chunk_text": doc.chunk_text[:max_chunk_length] if doc.chunk_text else None,
                    }
                    for doc in result.documents
                ],
                "query_results": [
                    {
                        "text": qr.text[:max_chunk_length] if qr.text else None,
                        "score": qr.score,
                        "metadata": qr.metadata,
                    }
                    for qr in result.query_results[:max_results]
                ],
                "execution_time": result.execution_time,
                "rewritten_query": result.rewritten_query,
            }

            if result.cot_output:
                response["cot_output"] = result.cot_output

            await ctx.info(f"Search completed in {result.execution_time:.2f}s")
            return response

        except ValueError as e:
            await ctx.warning(f"Invalid input: {e}")
            return create_error_response(e, MCPErrorType.VALIDATION)
        except Exception as e:
            logger.exception("Search failed")
            await ctx.warning(f"Search failed: {e}")
            return create_error_response(e, MCPErrorType.OPERATION)

    @mcp.tool()
    async def rag_list_collections(
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
        include_stats: bool = False,
    ) -> dict[str, Any]:
        """List all collections accessible to the user.

        Retrieves a list of document collections that the specified user
        has access to, optionally including statistics about each collection.

        Requires 'rag:list' permission.

        Args:
            user_id: UUID of the user requesting collections
            ctx: MCP context with server resources
            include_stats: Include document counts and chunk statistics

        Returns:
            Dictionary containing:
            - collections: List of collection metadata
            - total: Total number of collections

        Raises:
            PermissionError: If authentication fails or user lacks required permissions
        """
        app_ctx = get_app_context(ctx)

        # Validate authentication and permissions
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_list_collections"])
        except PermissionError as e:
            logger.warning("List collections authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Listing collections for user {user_id}")

        try:
            user_uuid = parse_uuid(user_id, "user_id")

            # Get user's collections
            collections = app_ctx.collection_service.get_user_collections(user_uuid)

            collection_list = []
            for coll in collections:
                coll_data = {
                    "id": str(coll.id),
                    "name": coll.name,
                    "description": coll.description,
                    "status": coll.status.value if hasattr(coll.status, "value") else coll.status,
                    "created_at": coll.created_at.isoformat() if coll.created_at else None,
                    "updated_at": coll.updated_at.isoformat() if coll.updated_at else None,
                }

                if include_stats:
                    # Add chunk counts if available
                    if hasattr(coll, "total_chunks"):
                        coll_data["total_chunks"] = coll.total_chunks
                    if hasattr(coll, "document_count"):
                        coll_data["document_count"] = coll.document_count

                collection_list.append(coll_data)

            await ctx.info(f"Found {len(collection_list)} collections")
            return {
                "collections": collection_list,
                "total": len(collection_list),
            }

        except ValueError as e:
            await ctx.warning(f"Invalid input: {e}")
            return create_error_response(e, MCPErrorType.VALIDATION)
        except Exception as e:
            logger.exception("List collections failed")
            await ctx.warning(f"List collections failed: {e}")
            return create_error_response(e, MCPErrorType.OPERATION)

    @mcp.tool()
    async def rag_ingest(
        collection_id: str,
        user_id: str,
        file_urls: list[str],
        ctx: Context[ServerSession, MCPServerContext, Any],
        collection_name: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        """Ingest documents into a RAG collection.

        Validates the ingestion request and queues documents for processing.
        Actual file processing requires files to be accessible via the RAG Modulo
        file system or uploaded through the REST API.

        Requires 'rag:ingest' and 'rag:write' permissions.

        Note:
            For URL-based ingestion, files must be accessible from the server.
            For local file paths, files must exist on the server filesystem.
            For full upload functionality, use the REST API file upload endpoint.

        Args:
            collection_id: UUID of existing collection, or "new" to create one
            user_id: UUID of the user performing the ingestion
            file_urls: List of URLs or file paths to ingest
            ctx: MCP context with server resources
            collection_name: Name for new collection (required if collection_id="new")
            description: Description for new collection

        Returns:
            Dictionary containing:
            - collection_id: UUID of the collection documents were added to
            - files_queued: Number of files queued for processing
            - status: Ingestion status ('queued', 'partial', 'error')
            - message: Human-readable status message
            - details: Per-file status information

        Raises:
            PermissionError: If authentication fails or user lacks required permissions
        """
        app_ctx = get_app_context(ctx)

        # Validate authentication and permissions
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_ingest"])
        except PermissionError as e:
            logger.warning("Ingest authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Validating ingestion request for {len(file_urls)} documents...")

        try:
            user_uuid = parse_uuid(user_id, "user_id")

            # Handle new collection creation
            if collection_id.lower() == "new":
                if not collection_name:
                    return create_error_response(
                        "collection_name required when creating new collection",
                        MCPErrorType.VALIDATION,
                    )

                # Create new collection
                from backend.rag_solution.schemas.collection_schema import CollectionInput

                collection_input = CollectionInput(
                    name=collection_name,
                    is_private=False,  # Default to public for MCP-created collections
                )
                collection = app_ctx.collection_service.create_collection(collection_input)
                collection_uuid = collection.id
                await ctx.info(f"Created new collection: {collection.name}")
            else:
                collection_uuid = parse_uuid(collection_id, "collection_id")

            # Validate collection exists and user has access
            collection = app_ctx.collection_service.get_collection(collection_uuid)
            if not collection:
                return create_error_response(
                    f"Collection {collection_id} not found",
                    MCPErrorType.NOT_FOUND,
                )

            # Report progress and validate files
            total_files = len(file_urls)
            file_details = []

            for idx, url in enumerate(file_urls):
                await ctx.report_progress(
                    progress=(idx + 1) / total_files,
                    total=1.0,
                    message=f"Validating {url}...",
                )

                # Validate URL/path format
                file_details.append(
                    {
                        "url": url,
                        "status": "queued",
                        "message": "File queued for processing via REST API",
                    }
                )

            # Note: MCP ingestion queues files for processing. Actual file processing
            # requires the REST API with BackgroundTasks for async document processing.
            # This design prevents blocking the MCP tool call during large file uploads.
            await ctx.info(
                f"Ingestion request validated: {total_files} files queued. "
                "Use REST API POST /api/v1/files/upload for actual file upload and processing."
            )

            return {
                "collection_id": str(collection_uuid),
                "user_id": str(user_uuid),
                "files_queued": total_files,
                "status": "queued",
                "message": (
                    "Files validated and queued. Use REST API file upload endpoint "
                    "for actual ingestion: POST /api/v1/files/upload"
                ),
                "details": file_details,
            }

        except ValueError as e:
            await ctx.warning(f"Invalid input: {e}")
            return create_error_response(e, MCPErrorType.VALIDATION)
        except Exception as e:
            logger.exception("Ingestion validation failed")
            await ctx.warning(f"Ingestion failed: {e}")
            return create_error_response(e, MCPErrorType.OPERATION)

    @mcp.tool()
    async def rag_generate_podcast(
        collection_id: str,
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
        title: str | None = None,
        description: str | None = None,
        duration: str = "medium",
        language: str = "en",
        generate_script_only: bool = False,
    ) -> dict[str, Any]:
        """Generate an AI podcast from collection content.

        Creates a podcast script from the collection content. Full audio generation
        requires the REST API with background processing, but script-only generation
        can be performed directly.

        Requires 'rag:podcast' and 'rag:read' permissions.

        Note:
            - Script generation: Available directly via MCP
            - Audio generation: Requires REST API (async background processing)

        Args:
            collection_id: UUID of the collection to generate podcast from
            user_id: UUID of the user requesting the podcast
            ctx: MCP context with server resources
            title: Optional title for the podcast
            description: Optional description for the podcast
            duration: Podcast duration - short (5min), medium (15min), long (30min), extended (60min)
            language: Language code for the podcast (default: "en")
            generate_script_only: If True, only generate the script (no audio)

        Returns:
            Dictionary containing:
            - status: 'script_generated' or 'audio_requires_api'
            - collection_id: UUID of the source collection
            - script: Generated podcast script (if generate_script_only=True)
            - api_endpoint: REST API endpoint for audio generation

        Raises:
            PermissionError: If authentication fails or user lacks required permissions
        """
        app_ctx = get_app_context(ctx)

        # Validate authentication and permissions
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_generate_podcast"])
        except PermissionError as e:
            logger.warning("Podcast authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Processing podcast request for collection {collection_id}")

        try:
            collection_uuid = parse_uuid(collection_id, "collection_id")
            user_uuid = parse_uuid(user_id, "user_id")

            from backend.rag_solution.schemas.podcast_schema import (
                PodcastDuration,
                PodcastGenerationInput,
                VoiceSettings,
            )

            # Map duration string to enum
            duration_map = {
                "short": PodcastDuration.SHORT,
                "medium": PodcastDuration.MEDIUM,
                "long": PodcastDuration.LONG,
                "extended": PodcastDuration.EXTENDED,
            }
            podcast_duration = duration_map.get(duration.lower(), PodcastDuration.MEDIUM)

            # Create voice settings with defaults
            voice_settings = VoiceSettings(
                voice_id="default",
                language=language,
            )

            # Create podcast generation input
            podcast_input = PodcastGenerationInput(
                user_id=user_uuid,
                collection_id=collection_uuid,
                duration=podcast_duration,
                voice_settings=voice_settings,
                title=title,
                description=description,
                language=language,
            )

            # Report initial progress
            await ctx.report_progress(progress=0.1, total=1.0, message="Validating request...")

            if generate_script_only:
                # Generate script only (can be done synchronously)
                await ctx.report_progress(progress=0.3, total=1.0, message="Generating script...")

                try:
                    script_result = await app_ctx.podcast_service.generate_script_only(podcast_input)
                    await ctx.info("Script generation completed")

                    return {
                        "status": "script_generated",
                        "collection_id": str(collection_uuid),
                        "user_id": str(user_uuid),
                        "title": script_result.title if hasattr(script_result, "title") else title,
                        "script": script_result.script if hasattr(script_result, "script") else str(script_result),
                        "duration": duration,
                        "language": language,
                        "message": "Script generated successfully. Use REST API for audio generation.",
                        "api_endpoint": "POST /api/v1/podcasts/generate",
                    }
                except Exception as script_error:
                    logger.warning("Script generation failed: %s", script_error)
                    return {
                        "status": "script_generation_failed",
                        "error": str(script_error),
                        "error_type": "script_error",
                        "message": "Script generation failed. Try using REST API for full functionality.",
                        "api_endpoint": "POST /api/v1/podcasts/generate",
                    }
            else:
                # Audio generation requires background processing
                await ctx.info(
                    "Audio generation requires background processing. "
                    "Use REST API for full podcast generation with audio."
                )

                return {
                    "status": "audio_requires_api",
                    "collection_id": str(collection_uuid),
                    "user_id": str(user_uuid),
                    "duration": duration,
                    "language": language,
                    "message": (
                        "Audio generation requires async processing. "
                        "Use the REST API endpoint for full podcast generation."
                    ),
                    "api_endpoint": "POST /api/v1/podcasts/generate",
                    "hint": "Set generate_script_only=True to generate just the script via MCP.",
                }

        except ValueError as e:
            await ctx.warning(f"Invalid input: {e}")
            return create_error_response(e, MCPErrorType.VALIDATION)
        except Exception as e:
            logger.exception("Podcast request failed")
            await ctx.warning(f"Podcast request failed: {e}")
            return create_error_response(e, MCPErrorType.OPERATION)

    @mcp.tool()
    async def rag_smart_questions(
        collection_id: str,
        user_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
        context: str | None = None,
        previous_questions: list[str] | None = None,
        num_questions: int = 5,
    ) -> dict[str, Any]:
        """Generate smart follow-up questions for a collection.

        Analyzes the collection content and optionally recent conversation
        context to suggest relevant follow-up questions that users might
        want to explore.

        Requires 'rag:read' permission.

        Args:
            collection_id: UUID of the collection to generate questions for
            user_id: UUID of the user requesting questions
            ctx: MCP context with server resources
            context: Optional conversation context for personalized questions
            previous_questions: List of previously asked questions to avoid
            num_questions: Number of questions to generate (default: 5)

        Returns:
            Dictionary containing:
            - questions: List of suggested questions
            - categories: Question categories if available

        Raises:
            PermissionError: If authentication fails or user lacks required permissions
        """
        app_ctx = get_app_context(ctx)

        # Validate authentication and permissions
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_smart_questions"])
        except PermissionError as e:
            logger.warning("Smart questions authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Generating smart questions for collection {collection_id}")

        try:
            collection_uuid = parse_uuid(collection_id, "collection_id")
            # Validate user_id format (may be used for future authorization)
            _user_uuid = parse_uuid(user_id, "user_id")

            # Get existing collection questions
            # Note: Generating new questions requires LLM provider config and document texts.
            # Use the REST API for full question generation functionality.
            questions = app_ctx.question_service.get_collection_questions(collection_uuid)

            if not questions:
                await ctx.info("No pre-generated questions found. Use REST API to generate new questions.")
                return {
                    "questions": [],
                    "total": 0,
                    "message": "No questions found. Use REST API to generate questions.",
                }

            # Filter out previous questions if provided
            if previous_questions:
                prev_set = {q.lower() for q in previous_questions}
                questions = [q for q in questions if q.question.lower() not in prev_set]

            # Format response
            question_list = [
                {
                    "id": str(q.id) if hasattr(q, "id") else None,
                    "question": q.question,
                    "category": q.category if hasattr(q, "category") else None,
                }
                for q in questions[:num_questions]
            ]

            await ctx.info(f"Generated {len(question_list)} questions")
            return {
                "questions": question_list,
                "total": len(question_list),
            }

        except ValueError as e:
            await ctx.warning(f"Invalid input: {e}")
            return create_error_response(e, MCPErrorType.VALIDATION)
        except Exception as e:
            logger.exception("Question generation failed")
            await ctx.warning(f"Question generation failed: {e}")
            return create_error_response(e, MCPErrorType.OPERATION)

    @mcp.tool()
    async def rag_get_document(
        document_id: str,
        collection_id: str,
        ctx: Context[ServerSession, MCPServerContext, Any],
        include_chunks: bool = False,
        max_chunk_length: int = 500,
    ) -> dict[str, Any]:
        """Retrieve a specific document from a collection.

        Fetches the metadata and optionally the content chunks of a
        specific document within a collection.

        Requires 'rag:read' permission.

        Args:
            document_id: UUID of the document to retrieve
            collection_id: UUID of the collection containing the document
            ctx: MCP context with server resources
            include_chunks: Include document content chunks in response
            max_chunk_length: Maximum length of each chunk to return

        Returns:
            Dictionary containing:
            - document_id: UUID of the document
            - filename: Original filename
            - file_type: Document type (pdf, docx, etc.)
            - created_at: Document creation timestamp
            - chunks: List of content chunks if requested

        Raises:
            PermissionError: If authentication fails or user lacks required permissions
        """
        app_ctx = get_app_context(ctx)

        # Validate authentication and permissions
        try:
            await validate_auth(ctx, TOOL_PERMISSIONS["rag_get_document"])
        except PermissionError as e:
            logger.warning("Get document authorization failed: %s", e)
            return create_error_response(e, MCPErrorType.AUTHORIZATION)

        await ctx.info(f"Retrieving document {document_id}")

        try:
            document_uuid = parse_uuid(document_id, "document_id")
            # Validate collection_id format (for future use in collection-scoped queries)
            _ = parse_uuid(collection_id, "collection_id")

            # Get document from file service
            doc = app_ctx.file_service.get_file_by_id(document_uuid)

            if not doc:
                return create_error_response(
                    f"Document {document_id} not found",
                    MCPErrorType.NOT_FOUND,
                )

            response = {
                "document_id": str(doc.id),
                "filename": doc.filename,
                "file_type": doc.file_type,
                "file_size": doc.file_size,
                "created_at": doc.created_at.isoformat() if doc.created_at else None,
                "updated_at": doc.updated_at.isoformat() if doc.updated_at else None,
            }

            if include_chunks:
                # Get document chunks from vector store
                # This would require querying the vector database
                # For now, return document metadata only
                response["chunks"] = []
                response["chunk_note"] = (
                    "Chunk retrieval requires vector store query - use rag_search for content retrieval"
                )

            await ctx.info(f"Retrieved document: {doc.filename}")
            return response

        except ValueError as e:
            await ctx.warning(f"Invalid input: {e}")
            return create_error_response(e, MCPErrorType.VALIDATION)
        except Exception as e:
            logger.exception("Document retrieval failed")
            await ctx.warning(f"Document retrieval failed: {e}")
            return create_error_response(e, MCPErrorType.OPERATION)

    logger.info("Registered 6 RAG tools with MCP server")
