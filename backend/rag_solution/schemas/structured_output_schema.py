"""Structured output schemas for RAG system responses with JSON schema validation.

This module defines Pydantic models for structured responses from LLM providers,
enabling reliable parsing of citations, confidence scores, and reasoning steps.

Follows industry best practices from OpenAI, Anthropic, and LangChain for
structured LLM outputs with provider-level validation guarantees.
"""

from enum import Enum
from typing import Any

from pydantic import UUID4, BaseModel, ConfigDict, Field, field_validator


class FormatType(str, Enum):
    """Format type for structured answer output."""

    STANDARD = "standard"  # Regular answer with citations
    COT_REASONING = "cot_reasoning"  # Chain of Thought with reasoning steps
    COMPARATIVE = "comparative"  # Comparing multiple sources
    SUMMARY = "summary"  # Summary of multiple documents


class Citation(BaseModel):
    """Citation model for document attribution.

    Attributes:
        document_id: UUID4 of the source document
        title: Document title for display
        excerpt: Relevant excerpt from the document (max 500 chars)
        page_number: Optional page number reference
        relevance_score: Score indicating relevance to query (0.0-1.0)
        chunk_id: Optional chunk identifier for precise source tracking
    """

    document_id: UUID4 = Field(..., description="UUID4 of the source document")
    title: str = Field(..., description="Document title", max_length=500)
    excerpt: str = Field(..., description="Relevant excerpt from document", max_length=500)
    page_number: int | None = Field(None, description="Page number reference", ge=1)
    relevance_score: float = Field(..., description="Relevance score", ge=0.0, le=1.0)
    chunk_id: str | None = Field(None, description="Chunk identifier", max_length=100)

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "document_id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Machine Learning Fundamentals",
                "excerpt": "Machine learning is a subset of artificial intelligence that enables...",
                "page_number": 42,
                "relevance_score": 0.95,
                "chunk_id": "chunk_123",
            }
        },
    )

    @field_validator("excerpt")
    @classmethod
    def validate_excerpt(cls, v: str) -> str:
        """Ensure excerpt is not empty and has reasonable length."""
        if not v or not v.strip():
            raise ValueError("Excerpt cannot be empty")
        return v.strip()


class ReasoningStep(BaseModel):
    """Reasoning step for Chain of Thought outputs.

    Attributes:
        step_number: Sequential step number in reasoning chain
        thought: The reasoning or analysis performed in this step
        conclusion: Conclusion reached in this step
        citations: List of citations supporting this reasoning step
    """

    step_number: int = Field(..., description="Step number in reasoning chain", ge=1)
    thought: str = Field(..., description="Reasoning or analysis", max_length=2000)
    conclusion: str = Field(..., description="Conclusion from this step", max_length=1000)
    citations: list[Citation] = Field(default_factory=list, description="Supporting citations")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "step_number": 1,
                "thought": "First, I need to understand what machine learning is...",
                "conclusion": "Machine learning is a method for training computers to learn from data.",
                "citations": [],
            }
        },
    )

    @field_validator("thought", "conclusion")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        """Ensure text fields are not empty."""
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()


class StructuredAnswer(BaseModel):
    """Structured answer with citations and optional reasoning steps.

    This is the main response model that LLM providers should return when
    structured output is requested. It includes the answer text, confidence
    score, citations, and optional reasoning steps for CoT queries.

    Attributes:
        answer: The main answer text
        confidence: Confidence score for the answer (0.0-1.0)
        citations: List of citations supporting the answer
        reasoning_steps: Optional list of reasoning steps (for CoT queries)
        format_type: Type of answer format
        metadata: Additional metadata about the generation
    """

    answer: str = Field(..., description="Main answer text", min_length=1, max_length=10000)
    confidence: float = Field(..., description="Confidence score", ge=0.0, le=1.0)
    citations: list[Citation] = Field(default_factory=list, description="Supporting citations")
    reasoning_steps: list[ReasoningStep] | None = Field(None, description="Reasoning steps for CoT queries")
    format_type: FormatType = Field(default=FormatType.STANDARD, description="Answer format type")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "answer": "Machine learning is a subset of AI that enables computers to learn from data...",
                "confidence": 0.92,
                "citations": [
                    {
                        "document_id": "550e8400-e29b-41d4-a716-446655440000",
                        "title": "ML Fundamentals",
                        "excerpt": "Machine learning enables...",
                        "relevance_score": 0.95,
                    }
                ],
                "format_type": "standard",
                "metadata": {"model": "gpt-4", "tokens": 150},
            }
        },
    )

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, v: str) -> str:
        """Ensure answer is not empty."""
        if not v or not v.strip():
            raise ValueError("Answer cannot be empty")
        return v.strip()

    @field_validator("citations")
    @classmethod
    def validate_citations(cls, v: list[Citation]) -> list[Citation]:
        """Ensure citations list is valid and deduplicated.

        When duplicate citations exist (same document_id and chunk_id),
        preserves the one with the highest relevance score.

        Returns:
            Deduplicated list of citations with highest relevance scores
        """
        if not v:
            return v

        # Use dict to track best citation for each (document_id, chunk_id) pair
        best_citations: dict[tuple[str, str | None], Citation] = {}

        for citation in v:
            key = (str(citation.document_id), citation.chunk_id)

            # Keep citation with highest relevance score for each unique key
            if key not in best_citations or citation.relevance_score > best_citations[key].relevance_score:
                best_citations[key] = citation

        # Return citations in order of relevance score (highest first)
        return sorted(best_citations.values(), key=lambda c: c.relevance_score, reverse=True)

    @field_validator("reasoning_steps")
    @classmethod
    def validate_reasoning_steps(cls, v: list[ReasoningStep] | None) -> list[ReasoningStep] | None:
        """Ensure reasoning steps are properly ordered."""
        if v is None:
            return None
        # Validate step numbers are sequential starting from 1
        expected_step = 1
        for step in v:
            if step.step_number != expected_step:
                raise ValueError(
                    f"Reasoning steps must be sequential. Expected {expected_step}, got {step.step_number}"
                )
            expected_step += 1
        return v


class StructuredOutputConfig(BaseModel):
    """Configuration for structured output generation.

    Attributes:
        enabled: Whether to request structured output from provider
        format_type: Desired format type for the response
        include_reasoning: Whether to include reasoning steps (CoT)
        max_citations: Maximum number of citations to include
        min_confidence: Minimum confidence threshold (0.0-1.0)
        validation_strict: Whether to enforce strict validation
        max_context_per_doc: Maximum characters per document context (100-10000)
    """

    enabled: bool = Field(default=False, description="Enable structured output")
    format_type: FormatType = Field(default=FormatType.STANDARD, description="Desired format type")
    include_reasoning: bool = Field(default=False, description="Include reasoning steps")
    max_citations: int = Field(default=5, description="Maximum citations", ge=1, le=20)
    min_confidence: float = Field(default=0.0, description="Minimum confidence threshold", ge=0.0, le=1.0)
    validation_strict: bool = Field(default=True, description="Enforce strict validation")
    max_context_per_doc: int = Field(
        default=2000, description="Maximum characters per document context", ge=100, le=10000
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "enabled": True,
                "format_type": "standard",
                "include_reasoning": False,
                "max_citations": 5,
                "min_confidence": 0.6,
                "validation_strict": True,
                "max_context_per_doc": 2000,
            }
        },
    )
