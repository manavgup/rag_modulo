"""Unit tests for MCP tools module.

Tests for all RAG tools exposed via MCP.
"""

from datetime import datetime
from enum import Enum
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from backend.mcp_server.server import MCPServerContext
from backend.mcp_server.tools import register_rag_tools


class FileStatus(str, Enum):
    """Mock file status enum."""

    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"


class CollectionStatus(str, Enum):
    """Mock collection status enum."""

    ACTIVE = "active"
    PENDING = "pending"


@pytest.fixture
def mock_settings() -> MagicMock:
    """Create mock settings."""
    settings = MagicMock()
    settings.JWT_SECRET_KEY = "test-secret"  # pragma: allowlist secret
    return settings


@pytest.fixture
def mock_app_context() -> MCPServerContext:
    """Create mock app context with all services."""
    return MCPServerContext(
        db_session=MagicMock(),
        search_service=MagicMock(),
        collection_service=MagicMock(),
        podcast_service=MagicMock(),
        question_service=MagicMock(),
        file_service=MagicMock(),
        authenticator=MagicMock(),
        settings=MagicMock(),
    )


@pytest.fixture
def mock_mcp_context(mock_app_context: MCPServerContext) -> MagicMock:
    """Create mock MCP context."""
    ctx = MagicMock()
    ctx.request_context.lifespan_context = mock_app_context
    ctx.info = AsyncMock()
    ctx.warning = AsyncMock()
    ctx.report_progress = AsyncMock()
    return ctx


class TestRegisterRagTools:
    """Tests for register_rag_tools function."""

    def test_register_tools(self) -> None:
        """Test that tools are registered with MCP server."""
        mock_mcp = MagicMock()

        register_rag_tools(mock_mcp)

        # Verify tool decorator was called 6 times
        assert mock_mcp.tool.call_count == 6


class TestRagSearchTool:
    """Tests for rag_search tool."""

    @pytest.mark.asyncio
    async def test_search_success(self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock) -> None:
        """Test successful search."""
        # Setup mock search result
        mock_doc = MagicMock()
        mock_doc.document_id = UUID("5a7283f0-3f19-4b85-9ded-4429dca33265")
        mock_doc.document_name = "test.pdf"
        mock_doc.chunk_text = "Test chunk content"

        mock_query_result = MagicMock()
        mock_query_result.text = "Test result text"
        mock_query_result.score = 0.95
        mock_query_result.metadata = {"source": "test"}

        mock_result = MagicMock()
        mock_result.answer = "Test answer"
        mock_result.documents = [mock_doc]
        mock_result.query_results = [mock_query_result]
        mock_result.execution_time = 1.5
        mock_result.rewritten_query = "rewritten query"
        mock_result.cot_output = None

        mock_app_context.search_service.search = AsyncMock(return_value=mock_result)

        # Create tool function by registering tools
        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        # Call the search tool
        result = await tool_functions["rag_search"](
            question="test question",
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert result["answer"] == "Test answer"
        assert len(result["documents"]) == 1
        assert result["execution_time"] == 1.5

    @pytest.mark.asyncio
    async def test_search_with_cot(self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock) -> None:
        """Test search with Chain of Thought enabled."""
        mock_result = MagicMock()
        mock_result.answer = "CoT answer"
        mock_result.documents = []
        mock_result.query_results = []
        mock_result.execution_time = 2.0
        mock_result.rewritten_query = None
        mock_result.cot_output = "Step 1: Analyze\nStep 2: Synthesize"

        mock_app_context.search_service.search = AsyncMock(return_value=mock_result)

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_search"](
            question="complex question",
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
            enable_cot=True,
            show_cot_steps=True,
        )

        assert result["cot_output"] == "Step 1: Analyze\nStep 2: Synthesize"

    @pytest.mark.asyncio
    async def test_search_invalid_uuid(self, mock_mcp_context: MagicMock) -> None:
        """Test search with invalid UUID."""
        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_search"](
            question="test",
            collection_id="not-a-uuid",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert "error" in result
        assert result["error_type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_search_service_error(self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock) -> None:
        """Test search handles service errors."""
        mock_app_context.search_service.search = AsyncMock(side_effect=Exception("Search failed"))

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_search"](
            question="test",
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert "error" in result
        assert result["error_type"] == "search_error"


class TestRagListCollectionsTool:
    """Tests for rag_list_collections tool."""

    @pytest.mark.asyncio
    async def test_list_collections_success(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test successful collection listing."""
        mock_coll = MagicMock()
        mock_coll.id = UUID("5a7283f0-3f19-4b85-9ded-4429dca33265")
        mock_coll.name = "Test Collection"
        mock_coll.description = "Test description"
        mock_coll.status = CollectionStatus.ACTIVE
        mock_coll.created_at = datetime(2024, 1, 1)
        mock_coll.updated_at = datetime(2024, 1, 2)

        mock_app_context.collection_service.get_user_collections = MagicMock(return_value=[mock_coll])

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_list_collections"](
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert result["total"] == 1
        assert result["collections"][0]["name"] == "Test Collection"

    @pytest.mark.asyncio
    async def test_list_collections_with_stats(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test collection listing with stats."""
        mock_coll = MagicMock()
        mock_coll.id = UUID("5a7283f0-3f19-4b85-9ded-4429dca33265")
        mock_coll.name = "Test Collection"
        mock_coll.description = "Test"
        mock_coll.status = CollectionStatus.ACTIVE
        mock_coll.created_at = None
        mock_coll.updated_at = None
        mock_coll.total_chunks = 100
        mock_coll.document_count = 10

        mock_app_context.collection_service.get_user_collections = MagicMock(return_value=[mock_coll])

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_list_collections"](
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
            include_stats=True,
        )

        assert result["collections"][0]["total_chunks"] == 100
        assert result["collections"][0]["document_count"] == 10

    @pytest.mark.asyncio
    async def test_list_collections_invalid_user(self, mock_mcp_context: MagicMock) -> None:
        """Test collection listing with invalid user ID."""
        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_list_collections"](
            user_id="invalid",
            ctx=mock_mcp_context,
        )

        assert "error" in result
        assert result["error_type"] == "validation_error"


class TestRagIngestTool:
    """Tests for rag_ingest tool."""

    @pytest.mark.asyncio
    async def test_ingest_existing_collection(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test ingesting into existing collection."""
        mock_app_context.collection_service.process_documents = AsyncMock()

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_ingest"](
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            file_urls=["file1.pdf", "file2.pdf"],
            ctx=mock_mcp_context,
        )

        assert result["status"] == "completed"
        assert result["documents_processed"] == 2

    @pytest.mark.asyncio
    async def test_ingest_new_collection(self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock) -> None:
        """Test creating new collection and ingesting."""
        mock_collection = MagicMock()
        mock_collection.id = UUID("5a7283f0-3f19-4b85-9ded-4429dca33265")
        mock_collection.name = "New Collection"

        mock_app_context.collection_service.create_collection = MagicMock(return_value=mock_collection)
        mock_app_context.collection_service.process_documents = AsyncMock()

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_ingest"](
            collection_id="new",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            file_urls=["file1.pdf"],
            ctx=mock_mcp_context,
            collection_name="New Collection",
            description="Test collection",
        )

        assert result["status"] == "completed"
        assert result["collection_id"] == str(mock_collection.id)

    @pytest.mark.asyncio
    async def test_ingest_new_without_name(self, mock_mcp_context: MagicMock) -> None:
        """Test creating new collection without name fails."""
        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_ingest"](
            collection_id="new",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            file_urls=["file1.pdf"],
            ctx=mock_mcp_context,
        )

        assert "error" in result
        assert "collection_name required" in result["error"]


class TestRagGeneratePodcastTool:
    """Tests for rag_generate_podcast tool."""

    @pytest.mark.asyncio
    async def test_generate_podcast_success(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test podcast tool returns requires_api status.

        Note: The MCP podcast tool doesn't directly call generate_podcast because
        it requires FastAPI's BackgroundTasks. Instead, it validates input and
        returns a status indicating the REST API should be used.
        """
        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        # Use the actual tool signature: no topic param, uses duration/title/description
        result = await tool_functions["rag_generate_podcast"](
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
            title="Test Title",
            duration="medium",
        )

        # Tool returns requires_api status since BackgroundTasks isn't available in MCP
        assert result["status"] == "requires_api"
        assert result["collection_id"] == "5a7283f0-3f19-4b85-9ded-4429dca33265"
        assert result["duration"] == "medium"

    @pytest.mark.asyncio
    async def test_generate_podcast_validation_error(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test podcast tool returns validation error for invalid UUID."""
        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        # Use invalid UUID to trigger validation error
        result = await tool_functions["rag_generate_podcast"](
            collection_id="invalid-uuid",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert "error" in result
        assert result["error_type"] == "validation_error"


class TestRagSmartQuestionsTool:
    """Tests for rag_smart_questions tool."""

    @pytest.mark.asyncio
    async def test_smart_questions_success(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test successful question generation with existing questions."""
        # Create enough mock questions (5+) so suggest_questions won't be called
        mock_questions = []
        for i in range(5):
            mock_q = MagicMock()
            mock_q.id = UUID(f"12345678-1234-5678-1234-56781234567{i}")
            mock_q.question = f"What is topic {i}?"
            mock_q.category = "overview"
            mock_questions.append(mock_q)

        mock_app_context.question_service.get_collection_questions = MagicMock(return_value=mock_questions)

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_smart_questions"](
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        # Default num_questions is 5
        assert result["total"] == 5
        assert result["questions"][0]["question"] == "What is topic 0?"

    @pytest.mark.asyncio
    async def test_smart_questions_no_existing_questions(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test that when no questions exist, a message is returned.

        Note: The MCP smart_questions tool doesn't call suggest_questions because
        it requires LLM provider config and document texts. Instead, it only
        retrieves existing questions and returns a message when none exist.
        """
        mock_app_context.question_service.get_collection_questions = MagicMock(return_value=[])

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_smart_questions"](
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
            num_questions=5,
        )

        # When no questions exist, the tool returns empty list with a message
        assert result["total"] == 0
        assert result["questions"] == []
        assert "message" in result
        assert "REST API" in result["message"]

    @pytest.mark.asyncio
    async def test_smart_questions_filters_previous(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test filtering out previously asked questions."""
        # Create enough questions so that filtering still leaves at least num_questions
        mock_questions = []
        for i in range(6):
            mock_q = MagicMock()
            mock_q.id = UUID(f"12345678-1234-5678-1234-56781234567{i}")
            mock_q.question = f"Question {i}" if i > 0 else "Previously asked"
            mock_q.category = None
            mock_questions.append(mock_q)

        mock_app_context.question_service.get_collection_questions = MagicMock(return_value=mock_questions)

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_smart_questions"](
            collection_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            user_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
            previous_questions=["previously asked"],  # lowercase
        )

        # After filtering, we have 5 remaining and num_questions defaults to 5
        assert result["total"] == 5
        # Make sure filtered question is not in results
        question_texts = [q["question"] for q in result["questions"]]
        assert "Previously asked" not in question_texts


class TestRagGetDocumentTool:
    """Tests for rag_get_document tool."""

    @pytest.mark.asyncio
    async def test_get_document_success(self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock) -> None:
        """Test successful document retrieval."""
        mock_doc = MagicMock()
        mock_doc.id = UUID("5a7283f0-3f19-4b85-9ded-4429dca33265")
        mock_doc.filename = "test.pdf"
        mock_doc.file_type = "pdf"
        mock_doc.file_size = 1024
        mock_doc.created_at = datetime(2024, 1, 1)
        mock_doc.updated_at = datetime(2024, 1, 2)

        mock_app_context.file_service.get_file_by_id = MagicMock(return_value=mock_doc)

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_get_document"](
            document_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            collection_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert result["filename"] == "test.pdf"
        assert result["file_type"] == "pdf"

    @pytest.mark.asyncio
    async def test_get_document_not_found(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test document not found."""
        mock_app_context.file_service.get_file_by_id = MagicMock(return_value=None)

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_get_document"](
            document_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            collection_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
        )

        assert "error" in result
        assert result["error_type"] == "not_found"

    @pytest.mark.asyncio
    async def test_get_document_with_chunks(
        self, mock_app_context: MCPServerContext, mock_mcp_context: MagicMock
    ) -> None:
        """Test document retrieval with chunks requested."""
        mock_doc = MagicMock()
        mock_doc.id = UUID("5a7283f0-3f19-4b85-9ded-4429dca33265")
        mock_doc.filename = "test.pdf"
        mock_doc.file_type = "pdf"
        mock_doc.file_size = 1024
        mock_doc.created_at = None
        mock_doc.updated_at = None

        mock_app_context.file_service.get_file_by_id = MagicMock(return_value=mock_doc)

        mock_mcp = MagicMock()
        tool_functions = {}

        def capture_tool(func=None):
            if func:
                tool_functions[func.__name__] = func
                return func
            return capture_tool

        mock_mcp.tool = capture_tool
        register_rag_tools(mock_mcp)

        result = await tool_functions["rag_get_document"](
            document_id="5a7283f0-3f19-4b85-9ded-4429dca33265",
            collection_id="e2f82031-85e3-487c-9bf2-2686ab7ea5f9",
            ctx=mock_mcp_context,
            include_chunks=True,
        )

        assert "chunks" in result
        assert "chunk_note" in result
