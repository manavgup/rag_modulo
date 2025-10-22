"""Example integration of enhanced logging in RAG services.

This file demonstrates how to integrate the enhanced logging system into
RAG Modulo services. Use these patterns when updating services.

Example patterns shown:
1. Using log_operation for automatic timing and context
2. Using pipeline_stage_context for pipeline stage tracking
3. Adding structured metadata to logs
4. Request correlation across async operations
"""

import asyncio

from pydantic import UUID4

from core.enhanced_logging import get_logger
from core.logging_context import (
    PipelineStage,
    log_operation,
    pipeline_stage_context,
    request_context,
)

# Get logger for this module
logger = get_logger(__name__)


async def example_search_operation(
    collection_id: UUID4,
    user_id: UUID4,
    query: str,
) -> dict:
    """Example search operation with enhanced logging.

    This demonstrates the recommended pattern for integrating enhanced logging
    into SearchService and other RAG services.

    Args:
        collection_id: Collection to search
        user_id: User making the request
        query: Search query

    Returns:
        dict: Search results
    """
    # Wrap the entire operation with log_operation for automatic timing and context
    with log_operation(
        logger,
        operation="search_documents",
        entity_type="collection",
        entity_id=str(collection_id),
        user_id=str(user_id),
        query=query,  # Additional metadata
    ):
        # Each pipeline stage is tracked separately
        with pipeline_stage_context(PipelineStage.QUERY_VALIDATION):
            # Log with structured metadata
            logger.info("Validating search query", extra={"query_length": len(query)})
            # Validation logic here...
            await asyncio.sleep(0.1)  # Simulated work

        with pipeline_stage_context(PipelineStage.QUERY_REWRITING):
            rewritten_query = await _rewrite_query(query)
            # Log with both original and rewritten for debugging
            logger.info(
                "Query rewritten successfully",
                extra={
                    "original_query": query,
                    "rewritten_query": rewritten_query,
                    "rewriting_strategy": "llm_based",
                },
            )

        with pipeline_stage_context(PipelineStage.EMBEDDING_GENERATION):
            embeddings = await _generate_embeddings(rewritten_query)
            logger.debug("Query embeddings generated", extra={"dimension": len(embeddings)})

        with pipeline_stage_context(PipelineStage.VECTOR_SEARCH):
            results = await _vector_search(embeddings, collection_id)
            # Log search metrics
            logger.info(
                "Vector search completed",
                extra={
                    "result_count": len(results),
                    "top_score": results[0]["score"] if results else 0,
                },
            )

        with pipeline_stage_context(PipelineStage.RERANKING):
            reranked_results = await _rerank_results(results, query)
            logger.info(
                "Results reranked",
                extra={
                    "original_count": len(results),
                    "final_count": len(reranked_results),
                },
            )

        # Final result
        logger.info("Search completed successfully", extra={"total_results": len(reranked_results)})

        return {"results": reranked_results, "query": rewritten_query}


async def _rewrite_query(query: str) -> str:
    """Simulate query rewriting."""
    await asyncio.sleep(0.05)
    return f"{query} expanded terms"


async def _generate_embeddings(query: str) -> list[float]:
    """Simulate embedding generation."""
    await asyncio.sleep(0.1)
    return [0.1] * 384  # Fake 384-dim embedding


async def _vector_search(embeddings: list[float], collection_id: UUID4) -> list[dict]:
    """Simulate vector search."""
    await asyncio.sleep(0.2)
    return [
        {"id": "doc1", "score": 0.95, "text": "Result 1"},
        {"id": "doc2", "score": 0.87, "text": "Result 2"},
        {"id": "doc3", "score": 0.72, "text": "Result 3"},
    ]


async def _rerank_results(results: list[dict], query: str) -> list[dict]:
    """Simulate reranking."""
    await asyncio.sleep(0.1)
    return results[:2]  # Keep top 2


async def example_chain_of_thought_operation(
    collection_id: UUID4,
    user_id: UUID4,
    complex_query: str,
) -> dict:
    """Example Chain of Thought operation with enhanced logging.

    Demonstrates nested operations and sub-question tracking.

    Args:
        collection_id: Collection to search
        user_id: User making the request
        complex_query: Complex question requiring decomposition

    Returns:
        dict: Synthesized answer
    """
    with log_operation(
        logger,
        operation="chain_of_thought_reasoning",
        entity_type="collection",
        entity_id=str(collection_id),
        user_id=str(user_id),
        query=complex_query,
    ):
        with pipeline_stage_context(PipelineStage.COT_QUESTION_DECOMPOSITION):
            sub_questions = await _decompose_question(complex_query)
            logger.info(
                "Question decomposed into sub-questions",
                extra={
                    "original_question": complex_query,
                    "sub_question_count": len(sub_questions),
                    "sub_questions": sub_questions,
                },
            )

        # Process each sub-question
        sub_answers = []
        for i, sub_q in enumerate(sub_questions):
            with pipeline_stage_context(PipelineStage.COT_REASONING):
                # Each sub-question gets its own logged operation
                logger.info(
                    f"Processing sub-question {i+1}/{len(sub_questions)}",
                    extra={"sub_question": sub_q, "sub_question_index": i},
                )

                # Nested search operation - context is preserved
                answer = await example_search_operation(collection_id, user_id, sub_q)
                sub_answers.append(answer)

        with pipeline_stage_context(PipelineStage.COT_ANSWER_SYNTHESIS):
            final_answer = await _synthesize_answers(sub_answers)
            logger.info(
                "Answers synthesized into final response",
                extra={
                    "sub_answer_count": len(sub_answers),
                    "final_answer_length": len(final_answer),
                },
            )

        return {"answer": final_answer, "reasoning_steps": len(sub_questions)}


async def _decompose_question(query: str) -> list[str]:
    """Simulate question decomposition."""
    await asyncio.sleep(0.05)
    return [f"Sub-question 1 from: {query}", f"Sub-question 2 from: {query}"]


async def _synthesize_answers(answers: list[dict]) -> str:
    """Simulate answer synthesis."""
    await asyncio.sleep(0.1)
    return "Synthesized final answer based on sub-answers"


async def example_error_handling(collection_id: UUID4, user_id: UUID4) -> dict | None:
    """Example error handling with enhanced logging.

    Demonstrates how errors are automatically logged with context.

    Args:
        collection_id: Collection to search
        user_id: User making the request

    Returns:
        Optional[dict]: Result or None on error
    """
    try:
        with log_operation(
            logger,
            operation="risky_operation",
            entity_type="collection",
            entity_id=str(collection_id),
            user_id=str(user_id),
        ), pipeline_stage_context(PipelineStage.DOCUMENT_PROCESSING):
            # Simulate an error
            raise ValueError("Simulated processing error")
    except ValueError as e:
        # Error is automatically logged by log_operation context manager
        # with full context, timing, and stack trace
        logger.error("Operation failed, returning None", extra={"error_type": type(e).__name__})
        return None


async def example_batch_processing(document_ids: list[str], collection_id: UUID4) -> list[dict]:
    """Example batch processing with enhanced logging.

    Demonstrates logging for batch operations with progress tracking.

    Args:
        document_ids: List of document IDs to process
        collection_id: Collection containing documents

    Returns:
        list[dict]: Processed results
    """
    with log_operation(
        logger,
        operation="batch_document_processing",
        entity_type="collection",
        entity_id=str(collection_id),
        document_count=len(document_ids),
    ):
        results = []

        with pipeline_stage_context(PipelineStage.DOCUMENT_CHUNKING):
            for i, doc_id in enumerate(document_ids):
                # Log progress periodically
                if i % 10 == 0:
                    logger.info(
                        f"Processing progress: {i}/{len(document_ids)}",
                        extra={
                            "progress_percent": round((i / len(document_ids)) * 100, 1),
                            "documents_processed": i,
                            "documents_total": len(document_ids),
                        },
                    )

                # Process each document
                result = await _process_document(doc_id)
                results.append(result)

        logger.info(
            "Batch processing completed",
            extra={
                "total_documents": len(document_ids),
                "successful": len(results),
                "failed": len(document_ids) - len(results),
            },
        )

        return results


async def _process_document(doc_id: str) -> dict:
    """Simulate document processing."""
    await asyncio.sleep(0.01)
    return {"doc_id": doc_id, "status": "processed"}


# Example of using request_context at API endpoint level
async def example_api_endpoint_handler(request_id: str, user_id: str, collection_id: str, query: str) -> dict:
    """Example API endpoint handler with request context.

    This pattern should be used at the API router level to set up
    request-wide context that propagates through all service calls.

    Args:
        request_id: Request ID from HTTP headers or generated
        user_id: Authenticated user ID
        collection_id: Collection ID from request
        query: Search query

    Returns:
        dict: API response
    """
    from uuid import UUID

    # Set request-level context at the API boundary
    with request_context(request_id=request_id, user_id=user_id):
        logger.info("Handling API request", extra={"endpoint": "/api/search", "method": "POST"})

        # All subsequent operations inherit this context
        result = await example_search_operation(UUID(collection_id), UUID(user_id), query)

        logger.info("API request completed", extra={"status": "success"})

        return result


if __name__ == "__main__":
    """Example usage and testing."""
    import uuid

    # This would normally be done at application startup
    async def main() -> None:
        from core.enhanced_logging import initialize_logging

        # Initialize logging with development settings
        await initialize_logging(
            log_level="DEBUG",
            log_format="text",  # Use text for development
            log_to_file=True,
            log_storage_enabled=True,
        )

        # Run example operations
        collection_id = uuid.uuid4()
        user_id = uuid.uuid4()

        print("\n=== Example 1: Simple Search ===")
        result1 = await example_search_operation(collection_id, user_id, "What is machine learning?")
        print(f"Result: {result1['query']}")

        print("\n=== Example 2: Chain of Thought ===")
        result2 = await example_chain_of_thought_operation(
            collection_id, user_id, "How does machine learning work and what are the key components?"
        )
        print(f"Reasoning steps: {result2['reasoning_steps']}")

        print("\n=== Example 3: Error Handling ===")
        result3 = await example_error_handling(collection_id, user_id)
        print(f"Result: {result3}")

        print("\n=== Example 4: Batch Processing ===")
        doc_ids = [f"doc_{i}" for i in range(25)]
        result4 = await example_batch_processing(doc_ids, collection_id)
        print(f"Processed: {len(result4)} documents")

    asyncio.run(main())
