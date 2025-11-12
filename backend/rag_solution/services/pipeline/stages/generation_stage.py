"""
Generation stage.

This stage generates the final answer using LLM or CoT reasoning.
Wraps the answer generation functionality from PipelineService.
"""

import re
from typing import Any

from core.logging_utils import get_logger
from rag_solution.schemas.structured_output_schema import StructuredOutputConfig
from rag_solution.services.pipeline.base_stage import BaseStage, StageResult
from rag_solution.services.pipeline.search_context import SearchContext

logger = get_logger("services.pipeline.stages.generation")


class GenerationStage(BaseStage):  # pylint: disable=too-few-public-methods
    """
    Generates final answer using LLM or CoT reasoning.

    This stage:
    1. Checks if CoT result is available (use that as answer)
    2. Otherwise, generates answer from reranked documents
    3. Applies answer cleaning and formatting
    4. Updates context with generated answer

    Note: Single public method (execute) is by design for pipeline stage pattern.
    """

    def __init__(self, pipeline_service: "PipelineService") -> None:  # type: ignore
        """
        Initialize the generation stage.

        Args:
            pipeline_service: PipelineService instance for generation operations
        """
        super().__init__("Generation")
        self.pipeline_service = pipeline_service

    async def execute(self, context: SearchContext) -> StageResult:
        """
        Execute answer generation.

        Args:
            context: Current search context

        Returns:
            StageResult with generated answer in context

        Raises:
            ValueError: If required context attributes are missing
            AttributeError: If context attributes are not accessible
        """
        self._log_stage_start(context)

        try:
            # Ensure we have query results
            if context.query_results is None:
                raise ValueError("Query results not set in context")

            # Ensure we have pipeline_id
            if not context.pipeline_id:
                raise ValueError("Pipeline ID not set in context")

            # Check if structured output is enabled
            structured_output_enabled = False
            if context.search_input.config_metadata:
                structured_output_enabled = context.search_input.config_metadata.get("structured_output_enabled", False)

            # Determine answer source
            if context.cot_output:
                # Use CoT answer
                generated_answer = context.cot_output.final_answer
                answer_source = "cot"
                logger.info("Using CoT-generated answer")
            elif structured_output_enabled:
                # Generate structured output with citations
                generated_answer = await self._generate_structured_answer(context)
                answer_source = "structured_output"
                logger.info("Generated structured answer with citations")
            else:
                # Generate answer from documents
                generated_answer = await self._generate_answer_from_documents(context)
                answer_source = "llm"
                logger.info("Generated answer using LLM")

            # Clean answer
            cleaned_answer = self._clean_answer(generated_answer)

            logger.info("Answer generated: %d chars, source=%s", len(cleaned_answer), answer_source)

            # Update context
            context.generated_answer = cleaned_answer
            context.add_metadata("generation", {"source": answer_source, "answer_length": len(cleaned_answer)})

            result = StageResult(success=True, context=context)
            self._log_stage_complete(result)
            return result

        except (ValueError, AttributeError, TypeError, KeyError) as e:
            return await self._handle_error(context, e)

    async def _generate_answer_from_documents(self, context: SearchContext) -> str:
        """
        Generate answer using LLM from documents.

        Args:
            context: Search context

        Returns:
            Generated answer text
        """
        # Validate configuration and get required components
        _, llm_parameters, provider = self.pipeline_service._validate_configuration(
            context.pipeline_id,
            context.user_id,  # pylint: disable=protected-access
        )

        # Get templates
        rag_template, _ = self.pipeline_service._get_templates(context.user_id)  # pylint: disable=protected-access

        # Format context from query results
        context_text = self.pipeline_service._format_context(  # pylint: disable=protected-access
            rag_template.id, context.query_results
        )

        # Use rewritten query if available, otherwise original question
        query = context.rewritten_query or context.search_input.question

        # COMPREHENSIVE DEBUG LOGGING - Log context sent to LLM
        self._log_llm_context(query, context_text, context.query_results, context.user_id)

        # Generate answer
        answer = self.pipeline_service._generate_answer(  # pylint: disable=protected-access
            context.user_id, query, context_text, provider, llm_parameters, rag_template
        )

        return answer

    async def _generate_structured_answer(self, context: SearchContext) -> str:
        """
        Generate structured answer with citations using LLM.

        Args:
            context: Search context

        Returns:
            Generated answer text (extracted from structured answer)
        """
        # Validate configuration and get required components
        _, llm_parameters, provider = self.pipeline_service._validate_configuration(
            context.pipeline_id,
            context.user_id,  # pylint: disable=protected-access
        )

        # Get templates
        rag_template, _ = self.pipeline_service._get_templates(context.user_id)  # pylint: disable=protected-access

        # Build context documents from query results with metadata
        context_documents = []
        for result in context.query_results:
            doc_dict: dict[str, Any] = {
                "id": str(result.chunk.document_id) if result.chunk and result.chunk.document_id else "unknown",
                "title": (
                    result.chunk.metadata.document_id
                    if result.chunk and result.chunk.metadata and hasattr(result.chunk.metadata, "document_id")
                    else "Untitled"
                ),
                "content": result.chunk.text if result.chunk and result.chunk.text else "",
                "page_number": (
                    result.chunk.metadata.page_number
                    if result.chunk and result.chunk.metadata and result.chunk.metadata.page_number
                    else None
                ),
                "chunk_id": result.chunk.chunk_id if result.chunk and result.chunk.chunk_id else None,
            }
            context_documents.append(doc_dict)

        # Extract structured output configuration from config_metadata
        config_metadata = context.search_input.config_metadata or {}
        structured_config = StructuredOutputConfig(
            enabled=True,
            format_type=config_metadata.get("format_type", "standard"),
            include_reasoning=config_metadata.get("include_reasoning", False),
            max_citations=config_metadata.get("max_citations", 5),
            min_confidence=config_metadata.get("min_confidence", 0.0),
            validation_strict=config_metadata.get("validation_strict", True),
            max_context_per_doc=config_metadata.get("max_context_per_doc", 2000),
        )

        # Use rewritten query if available, otherwise original question
        query = context.rewritten_query or context.search_input.question

        logger.info(
            "Generating structured output: query=%s, num_docs=%d, max_citations=%d",
            query[:100],
            len(context_documents),
            structured_config.max_citations,
        )

        try:
            # Generate structured answer using provider
            structured_answer, usage = provider.generate_structured_output(
                user_id=context.user_id,
                prompt=query,
                context_documents=context_documents,
                config=structured_config,
                model_parameters=llm_parameters,
                template=rag_template,
            )

            # Store structured answer in context
            context.structured_answer = structured_answer

            # Track token usage
            provider.track_usage(usage, user_id=context.user_id)

            logger.info(
                "Structured answer generated: confidence=%.2f, citations=%d, tokens=%d",
                structured_answer.confidence,
                len(structured_answer.citations),
                usage.total_tokens,
            )

            # Return the answer text for use as generated_answer
            return structured_answer.answer

        except NotImplementedError:
            # Provider doesn't support structured output - fall back to regular generation
            logger.warning(
                "Provider %s does not support structured output, falling back to regular generation",
                provider.__class__.__name__,
            )
            return await self._generate_answer_from_documents(context)
        except Exception as e:
            # Log error and fall back to regular generation
            logger.error("Structured output generation failed: %s, falling back to regular generation", e)
            return await self._generate_answer_from_documents(context)

    def _clean_answer(self, answer: str) -> str:
        """
        Clean generated answer by removing artifacts.

        Args:
            answer: Raw answer text

        Returns:
            Cleaned answer text
        """
        # Remove common LLM artifacts
        cleaned = answer.strip()

        # Remove "Answer:" prefix if present
        cleaned = re.sub(r"^(Answer|Response|Result):\s*", "", cleaned, flags=re.IGNORECASE)

        # Remove thinking tags if present (from CoT leakage)
        cleaned = re.sub(r"<thinking>.*?</thinking>", "", cleaned, flags=re.DOTALL | re.IGNORECASE)

        # Remove extra whitespace
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        cleaned = cleaned.strip()

        return cleaned

    def _log_llm_context(self, query: str, context_text: str, query_results, user_id) -> None:
        """
        Log the context being sent to LLM for debugging.

        Args:
            query: The query being sent
            context_text: The formatted context text
            query_results: The query results used to build context
            user_id: User ID for the request
        """
        try:
            import os
            from datetime import datetime

            debug_dir = "/tmp/rag_debug"
            os.makedirs(debug_dir, exist_ok=True)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            debug_file = f"{debug_dir}/context_to_llm_{timestamp}.txt"

            with open(debug_file, "w", encoding="utf-8") as f:
                f.write("=" * 80 + "\n")
                f.write("CONTEXT SENT TO LLM (GENERATION STAGE)\n")
                f.write(f"Timestamp: {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")

                f.write(f"User ID: {user_id}\n")
                f.write(f"Query: {query}\n")
                f.write(f"Number of chunks in query_results: {len(query_results)}\n")
                f.write(f"Context text length: {len(context_text)} chars\n\n")

                f.write("=" * 80 + "\n")
                f.write("QUERY RESULTS (CHUNKS USED):\n")
                f.write("=" * 80 + "\n\n")

                for i, result in enumerate(query_results, 1):
                    f.write(f"CHUNK #{i}\n")
                    f.write("-" * 80 + "\n")
                    f.write(f"Score: {result.score:.6f}\n")

                    if result.chunk:
                        if result.chunk.metadata:
                            page = getattr(result.chunk.metadata, "page_number", "?")
                            chunk_num = getattr(result.chunk.metadata, "chunk_number", "?")
                            f.write(f"Page: {page}\n")
                            f.write(f"Chunk Number: {chunk_num}\n")

                        chunk_text = result.chunk.text or ""
                        f.write(f"Text Length: {len(chunk_text)} chars\n\n")
                        f.write("Text Preview (first 200 chars):\n")
                        f.write(chunk_text[:200])
                        f.write("\n")
                    else:
                        f.write("WARNING: No chunk data\n")

                    f.write("\n" + "-" * 80 + "\n\n")

                f.write("=" * 80 + "\n")
                f.write("FORMATTED CONTEXT TEXT (sent to LLM):\n")
                f.write("=" * 80 + "\n\n")
                f.write(context_text)
                f.write("\n\n")

                f.write("=" * 80 + "\n")
                f.write("END OF LLM CONTEXT LOG\n")
                f.write("=" * 80 + "\n")

            logger.info("📝 LLM context logged to: %s", debug_file)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.warning("Failed to log LLM context: %s", e)
