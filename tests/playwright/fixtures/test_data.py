"""
Test data fixtures for Playwright tests.

Contains sample data for collections, documents, and search queries.
"""
import os
import tempfile
from typing import Any


class TestDataFixtures:
    """Centralized test data management."""

    @staticmethod
    def get_sample_collections() -> list[dict[str, Any]]:
        """Get sample collection data for testing."""
        return [
            {
                "name": "Playwright Test Collection",
                "description": "A test collection created by Playwright automation",
                "expected_status": "ready"
            },
            {
                "name": "AI Research Papers",
                "description": "Collection of AI and machine learning research papers",
                "expected_status": "ready"
            },
            {
                "name": "Technical Documentation",
                "description": "Software documentation and API references",
                "expected_status": "ready"
            }
        ]

    @staticmethod
    def get_sample_documents() -> list[dict[str, Any]]:
        """Get sample document data for testing."""
        return [
            {
                "name": "machine_learning_basics.txt",
                "content": """
                Machine Learning Basics

                Machine learning is a subset of artificial intelligence that enables computers
                to learn and make decisions from data without being explicitly programmed.

                Key concepts:
                - Supervised Learning: Learning with labeled data
                - Unsupervised Learning: Finding patterns in unlabeled data
                - Neural Networks: Inspired by the human brain
                - Deep Learning: Neural networks with multiple layers

                Applications:
                - Image recognition
                - Natural language processing
                - Recommendation systems
                - Autonomous vehicles
                """,
                "type": "text/plain"
            },
            {
                "name": "rag_overview.txt",
                "content": """
                Retrieval-Augmented Generation (RAG) Overview

                RAG is a framework that combines retrieval of relevant information
                with generative language models to provide accurate, contextual responses.

                Components:
                1. Vector Database: Stores document embeddings
                2. Retrieval System: Finds relevant documents
                3. Language Model: Generates responses using retrieved context

                Benefits:
                - Reduces hallucination in LLM responses
                - Provides source attribution
                - Enables knowledge updates without retraining
                - Supports domain-specific knowledge
                """,
                "type": "text/plain"
            },
            {
                "name": "api_documentation.txt",
                "content": """
                RAG Modulo API Documentation

                Base URL: http://localhost:8000

                Collections Endpoints:
                GET /api/collections - List all collections
                POST /api/collections - Create new collection
                GET /api/collections/{id} - Get collection details
                PUT /api/collections/{id} - Update collection
                DELETE /api/collections/{id} - Delete collection

                Documents Endpoints:
                POST /api/collections/{id}/documents - Upload documents
                DELETE /api/collections/{id}/documents/{doc_id} - Delete document

                Search Endpoints:
                POST /api/search - Search collections

                WebSocket Endpoints:
                WS /ws - Real-time chat interface
                """,
                "type": "text/plain"
            }
        ]

    @staticmethod
    def get_sample_search_queries() -> list[dict[str, Any]]:
        """Get sample search queries for testing."""
        return [
            {
                "query": "What is machine learning?",
                "expected_keywords": ["machine learning", "artificial intelligence", "data"],
                "expected_sources": True
            },
            {
                "query": "How does RAG work?",
                "expected_keywords": ["retrieval", "generation", "vector", "database"],
                "expected_sources": True
            },
            {
                "query": "What are the API endpoints?",
                "expected_keywords": ["api", "endpoints", "collections", "search"],
                "expected_sources": True
            },
            {
                "query": "Tell me about neural networks",
                "expected_keywords": ["neural", "networks", "brain", "layers"],
                "expected_sources": True
            }
        ]

    @staticmethod
    def create_test_file(content: str, filename: str, file_type: str = "text/plain") -> str:
        """Create a temporary test file and return its path."""
        # Determine file extension based on type
        if file_type == "text/plain":
            suffix = ".txt"
        elif file_type == "application/pdf":
            suffix = ".pdf"
        elif file_type == "application/json":
            suffix = ".json"
        else:
            suffix = ".txt"

        # Create temporary file
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=suffix,
            prefix=f"{filename}_",
            delete=False,
            encoding="utf-8"
        ) as f:
            f.write(content)
            return f.name

    @staticmethod
    def create_test_files_for_collection() -> list[str]:
        """Create multiple test files and return their paths."""
        documents = TestDataFixtures.get_sample_documents()
        file_paths = []

        for doc in documents:
            file_path = TestDataFixtures.create_test_file(
                doc["content"],
                doc["name"].replace(".txt", ""),
                doc["type"]
            )
            file_paths.append(file_path)

        return file_paths

    @staticmethod
    def cleanup_test_files(file_paths: list[str]) -> None:
        """Clean up temporary test files."""
        for file_path in file_paths:
            try:
                os.unlink(file_path)
            except OSError:
                pass  # File might already be deleted

    @staticmethod
    def get_expected_responses() -> dict[str, dict[str, Any]]:
        """Get expected response patterns for validation."""
        return {
            "machine_learning": {
                "keywords": ["machine learning", "artificial intelligence", "data", "algorithms"],
                "min_length": 50,
                "should_have_sources": True
            },
            "rag_system": {
                "keywords": ["retrieval", "generation", "vector", "database", "embedding"],
                "min_length": 50,
                "should_have_sources": True
            },
            "api_endpoints": {
                "keywords": ["api", "endpoint", "collection", "search", "http"],
                "min_length": 30,
                "should_have_sources": True
            }
        }

    @staticmethod
    def get_invalid_test_data() -> dict[str, Any]:
        """Get invalid data for negative testing."""
        return {
            "empty_collection_name": "",
            "too_long_collection_name": "x" * 256,
            "special_chars_collection_name": "!@#$%^&*()",
            "empty_search_query": "",
            "too_long_search_query": "x" * 10000,
            "invalid_file_types": [".exe", ".bat", ".sh"],
            "large_file_size": 100 * 1024 * 1024  # 100MB
        }

    @staticmethod
    def get_performance_test_data() -> dict[str, Any]:
        """Get data for performance testing."""
        return {
            "concurrent_users": 5,
            "messages_per_user": 3,
            "large_collection_size": 50,  # Number of documents
            "stress_test_duration": 60,  # Seconds
            "max_response_time": 30000,  # Milliseconds
            "max_upload_time": 60000  # Milliseconds for file uploads
        }

    @staticmethod
    def get_mock_auth_data() -> dict[str, str]:
        """Get mock authentication data for development testing."""
        return {
            "mock_token": "mock-dev-token",
            "mock_user_id": "test-user-123",
            "mock_username": "playwright-test-user",
            "mock_email": "test@example.com",
            "auth_header": "Bearer mock-dev-token"
        }

    @staticmethod
    def get_websocket_test_data() -> dict[str, Any]:
        """Get WebSocket specific test data."""
        return {
            "connection_timeout": 10000,
            "message_timeout": 30000,
            "ping_interval": 30000,
            "max_reconnect_attempts": 5,
            "test_messages": [
                "Hello, can you help me?",
                "What is in this collection?",
                "Tell me more about that",
                "Thank you for the information"
            ]
        }
