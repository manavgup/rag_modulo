"""Search commands for RAG CLI.

This module implements CLI commands for search operations including
query execution, explanation, and batch search functionality.
"""

from rag_solution.cli.client import RAGAPIClient
from rag_solution.cli.config import RAGConfig

from .base import BaseCommand, CommandResult


class SearchCommands(BaseCommand):
    """Commands for search operations.

    This class implements all search-related CLI commands,
    providing methods to interact with the search API.
    """

    def __init__(self, api_client: RAGAPIClient, config: RAGConfig | None = None) -> None:
        """Initialize search commands.

        Args:
            api_client: HTTP API client instance
            config: Optional configuration settings
        """
        super().__init__(api_client, config)

    def query(
        self, collection_id: str, query: str, pipeline_id: str | None = None, max_chunks: int = 5
    ) -> CommandResult:
        """Execute a search query.

        Args:
            collection_id: Collection to search in
            query: Search query text
            pipeline_id: Optional specific pipeline to use
            max_chunks: Maximum number of chunks to retrieve

        Returns:
            CommandResult with search results
        """
        self._require_authentication()

        try:
            # Get current user to obtain user_id
            try:
                current_user = self.api_client.get("/api/auth/me")
                user_id = current_user.get("uuid") or current_user.get("id")
            except Exception:
                # If we can't get current user, search won't work with current backend
                return self._create_error_result(
                    "Failed to get current user. Search requires authenticated user context."
                )

            # Get user's default pipeline if not provided
            if not pipeline_id:
                try:
                    pipelines = self.api_client.get(f"/api/users/{user_id}/pipelines")
                    if pipelines and len(pipelines) > 0:
                        # Find default or use first
                        for p in pipelines:
                            if p.get("is_default"):
                                pipeline_id = p["id"]
                                break
                        if not pipeline_id:
                            pipeline_id = pipelines[0]["id"]
                except Exception:
                    pass  # Will fail at search if no pipeline

            if not pipeline_id:
                return self._create_error_result("No pipeline found. User may not be properly initialized.")

            # Call the correct /api/search endpoint with SearchInput schema
            data = {
                "question": query,  # SearchInput uses "question" not "query"
                "collection_id": collection_id,
                "user_id": user_id,
                "pipeline_id": pipeline_id,
                "config_metadata": {"max_chunks": max_chunks},
            }

            response = self.api_client.post("/api/search", data=data)

            return self._create_success_result(data=response, message="Search completed successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def explain(
        self, collection_id: str, query: str, show_retrieval: bool = False, show_rewriting: bool = False
    ) -> CommandResult:
        """Explain search results and processing.

        Args:
            collection_id: Collection to search in
            query: Search query text
            show_retrieval: Include retrieval process details
            show_rewriting: Include query rewriting details

        Returns:
            CommandResult with search explanation
        """
        self._require_authentication()

        try:
            data = {
                "collection_id": collection_id,
                "query": query,
                "show_retrieval": show_retrieval,
                "show_rewriting": show_rewriting,
            }

            response = self.api_client.post("/api/search/explain", data=data)

            return self._create_success_result(data=response, message="Search explanation generated successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def batch_search(self, collection_id: str, queries: list[str], pipeline_id: str | None = None) -> CommandResult:
        """Execute multiple search queries in batch.

        Args:
            collection_id: Collection to search in
            queries: List of search queries
            pipeline_id: Optional specific pipeline to use

        Returns:
            CommandResult with batch search results
        """
        self._require_authentication()

        try:
            data = {"collection_id": collection_id, "queries": queries}

            if pipeline_id:
                data["pipeline_id"] = pipeline_id

            response = self.api_client.post("/api/search/batch", data=data)

            successful_queries = response.get("successful", 0)
            failed_queries = response.get("failed", 0)

            message = f"Processed {successful_queries} queries successfully"
            if failed_queries > 0:
                message += f" with {failed_queries} failures"

            return self._create_success_result(data=response, message=message)

        except Exception as e:
            return self._handle_api_error(e)

    def semantic_search(
        self, collection_id: str, query: str, similarity_threshold: float = 0.7, max_results: int = 10
    ) -> CommandResult:
        """Execute semantic search with similarity filtering.

        Args:
            collection_id: Collection to search in
            query: Search query text
            similarity_threshold: Minimum similarity score
            max_results: Maximum number of results

        Returns:
            CommandResult with semantic search results
        """
        self._require_authentication()

        try:
            data = {
                "collection_id": collection_id,
                "query": query,
                "similarity_threshold": similarity_threshold,
                "max_results": max_results,
            }

            response = self.api_client.post("/api/search/semantic", data=data)

            return self._create_success_result(
                data=response, message=f"Found {len(response.get('results', []))} semantic matches"
            )

        except Exception as e:
            return self._handle_api_error(e)

    def hybrid_search(
        self, collection_id: str, query: str, semantic_weight: float = 0.7, keyword_weight: float = 0.3
    ) -> CommandResult:
        """Execute hybrid search combining semantic and keyword search.

        Args:
            collection_id: Collection to search in
            query: Search query text
            semantic_weight: Weight for semantic search component
            keyword_weight: Weight for keyword search component

        Returns:
            CommandResult with hybrid search results
        """
        self._require_authentication()

        try:
            data = {
                "collection_id": collection_id,
                "query": query,
                "semantic_weight": semantic_weight,
                "keyword_weight": keyword_weight,
            }

            response = self.api_client.post("/api/search/hybrid", data=data)

            return self._create_success_result(data=response, message="Hybrid search completed successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def search_similar_documents(
        self, document_id: str, collection_id: str | None = None, limit: int = 5
    ) -> CommandResult:
        """Find documents similar to a given document.

        Args:
            document_id: Reference document ID
            collection_id: Optional collection to limit search
            limit: Maximum number of similar documents

        Returns:
            CommandResult with similar documents
        """
        self._require_authentication()

        try:
            data = {"document_id": document_id, "limit": limit}

            if collection_id:
                data["collection_id"] = collection_id

            response = self.api_client.post("/api/search/similar-documents", data=data)

            return self._create_success_result(
                data=response, message=f"Found {len(response.get('similar_documents', []))} similar documents"
            )

        except Exception as e:
            return self._handle_api_error(e)

    def get_search_history(self, limit: int = 20, collection_id: str | None = None) -> CommandResult:
        """Get search history for the current user.

        Args:
            limit: Maximum number of searches to return
            collection_id: Optional collection filter

        Returns:
            CommandResult with search history
        """
        self._require_authentication()

        try:
            from typing import Any

            params: dict[str, Any] = {"limit": limit}
            if collection_id:
                params["collection_id"] = collection_id

            response = self.api_client.get("/api/search/history", params=params)

            return self._create_success_result(
                data=response, message=f"Retrieved {len(response.get('searches', []))} search history items"
            )

        except Exception as e:
            return self._handle_api_error(e)

    def save_search(
        self, query: str, collection_id: str, name: str | None = None, description: str | None = None
    ) -> CommandResult:
        """Save a search query for later use.

        Args:
            query: Search query to save
            collection_id: Collection the search applies to
            name: Optional name for the saved search
            description: Optional description

        Returns:
            CommandResult with saved search data
        """
        self._require_authentication()

        try:
            data = {"query": query, "collection_id": collection_id}

            if name:
                data["name"] = name
            if description:
                data["description"] = description

            response = self.api_client.post("/api/search/saved-searches", data=data)

            return self._create_success_result(data=response, message="Search saved successfully")

        except Exception as e:
            return self._handle_api_error(e)

    def list_saved_searches(self, collection_id: str | None = None) -> CommandResult:
        """List saved searches for the current user.

        Args:
            collection_id: Optional collection filter

        Returns:
            CommandResult with saved searches
        """
        self._require_authentication()

        try:
            params = {}
            if collection_id:
                params["collection_id"] = collection_id

            response = self.api_client.get("/api/search/saved-searches", params=params)

            return self._create_success_result(
                data=response, message=f"Retrieved {len(response.get('saved_searches', []))} saved searches"
            )

        except Exception as e:
            return self._handle_api_error(e)
