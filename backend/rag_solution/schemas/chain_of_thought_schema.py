"""Chain of Thought (CoT) schemas for enhanced RAG search quality."""

from typing import Any

from pydantic import UUID4, BaseModel, Field, field_validator


class SourceAttribution(BaseModel):
    """Attribution information for a source document used in reasoning."""

    document_id: str = Field(..., description="Unique identifier for the source document")
    document_title: str | None = Field(None, description="Title or name of the source document")
    relevance_score: float = Field(..., description="Relevance score for this source (0-1)")
    excerpt: str | None = Field(None, description="Relevant excerpt from the source")
    chunk_index: int | None = Field(None, description="Index of the chunk within the document")
    retrieval_rank: int | None = Field(None, description="Rank in the retrieval results")

    @field_validator("relevance_score")
    @classmethod
    def validate_relevance_score(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("relevance_score must be between 0 and 1")
        return v


class ChainOfThoughtConfig(BaseModel):
    """Configuration for Chain of Thought reasoning."""

    enabled: bool = Field(default=False, description="Whether CoT is enabled")
    max_reasoning_depth: int = Field(default=3, description="Maximum reasoning steps")
    reasoning_strategy: str = Field(
        default="decomposition",
        description="Strategy: decomposition, iterative, hierarchical, causal"
    )
    context_preservation: bool = Field(default=True, description="Preserve context across steps")
    token_budget_multiplier: float = Field(default=2.0, description="Token budget multiplier")
    evaluation_threshold: float = Field(default=0.6, description="Evaluation threshold")

    @field_validator("max_reasoning_depth")
    @classmethod
    def validate_max_depth(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("max_reasoning_depth must be greater than 0")
        return v

    @field_validator("token_budget_multiplier")
    @classmethod
    def validate_token_multiplier(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("token_budget_multiplier must be greater than 0")
        return v

    @field_validator("evaluation_threshold")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("evaluation_threshold must be between 0 and 1")
        return v

    @field_validator("reasoning_strategy")
    @classmethod
    def validate_strategy(cls, v: str) -> str:
        valid_strategies = ["decomposition", "iterative", "hierarchical", "causal"]
        if v not in valid_strategies:
            raise ValueError(f"reasoning_strategy must be one of {valid_strategies}")
        return v


class DecomposedQuestion(BaseModel):
    """A decomposed sub-question in the reasoning chain."""

    sub_question: str = Field(..., description="The sub-question")
    reasoning_step: int = Field(..., description="Step number in reasoning chain")
    dependency_indices: list[int] = Field(default_factory=list, description="Dependencies on other steps")
    question_type: str | None = Field(None, description="Type of question")
    complexity_score: float = Field(default=0.5, description="Complexity score 0-1")

    @field_validator("reasoning_step")
    @classmethod
    def validate_step(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("reasoning_step must be greater than 0")
        return v

    @field_validator("complexity_score")
    @classmethod
    def validate_complexity(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("complexity_score must be between 0 and 1")
        return v

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str | None) -> str | None:
        if v is None:
            return v
        valid_types = ["definition", "comparison", "causal", "procedural", "analytical"]
        if v not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")
        return v


class QuestionDecomposition(BaseModel):
    """Result of question decomposition containing sub-questions."""

    sub_questions: list[DecomposedQuestion] = Field(
        default_factory=list,
        description="List of decomposed sub-questions"
    )


class SynthesisResult(BaseModel):
    """Result of answer synthesis."""

    final_answer: str = Field(..., description="The synthesized final answer")
    total_confidence: float = Field(..., description="Overall confidence score")


class ReasoningStep(BaseModel):
    """A single reasoning step in the Chain of Thought process."""

    step_number: int = Field(..., description="Step number")
    question: str = Field(..., description="Question for this step")
    context_used: list[str] = Field(default_factory=list, description="Context documents used (legacy)")
    source_attributions: list[SourceAttribution] = Field(default_factory=list, description="Structured source attributions")
    intermediate_answer: str | None = Field(None, description="Intermediate answer")
    confidence_score: float | None = Field(default=0.0, description="Confidence score 0-1")
    reasoning_trace: str | None = Field(None, description="Reasoning trace")
    execution_time: float | None = Field(None, description="Execution time in seconds")

    @field_validator("step_number")
    @classmethod
    def validate_step_number(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("step_number must be greater than 0")
        return v

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 1):
            raise ValueError("confidence_score must be between 0 and 1")
        return v

    @field_validator("execution_time")
    @classmethod
    def validate_execution_time(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("execution_time must be greater than 0")
        return v


class SourceSummary(BaseModel):
    """Summary of all sources used across the reasoning chain."""

    all_sources: list[SourceAttribution] = Field(default_factory=list, description="All unique sources used")
    primary_sources: list[SourceAttribution] = Field(default_factory=list, description="Most influential sources")
    source_usage_by_step: dict[int, list[str]] = Field(default_factory=dict, description="Sources used by each step")


class ChainOfThoughtOutput(BaseModel):
    """Output from Chain of Thought reasoning."""

    original_question: str = Field(..., description="Original user question")
    final_answer: str = Field(..., description="Final synthesized answer")
    reasoning_steps: list[ReasoningStep] = Field(default_factory=list, description="Reasoning steps taken")
    source_summary: SourceSummary | None = Field(None, description="Summary of source attributions")
    total_confidence: float = Field(default=0.0, description="Overall confidence score")
    token_usage: int | None = Field(None, description="Total tokens used")
    total_execution_time: float | None = Field(None, description="Total execution time")
    reasoning_strategy: str | None = Field(None, description="Strategy used")

    @field_validator("total_confidence")
    @classmethod
    def validate_total_confidence(cls, v: float) -> float:
        if v < 0 or v > 1:
            raise ValueError("total_confidence must be between 0 and 1")
        return v

    @field_validator("token_usage")
    @classmethod
    def validate_token_usage(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("token_usage must be greater than 0")
        return v

    @field_validator("total_execution_time")
    @classmethod
    def validate_total_execution_time(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("total_execution_time must be greater than 0")
        return v


class ChainOfThoughtInput(BaseModel):
    """Input for Chain of Thought reasoning."""

    question: str = Field(..., min_length=1, description="User question")
    collection_id: UUID4 = Field(..., description="Collection ID")
    user_id: UUID4 = Field(..., description="User ID")
    cot_config: dict[str, Any] | None = Field(None, description="CoT configuration")
    context_metadata: dict[str, Any] | None = Field(None, description="Context metadata")


class QuestionClassification(BaseModel):
    """Classification of a question for CoT routing."""

    question_type: str = Field(..., description="Type of question")
    complexity_level: str = Field(..., description="Complexity level")
    requires_cot: bool = Field(..., description="Whether CoT is needed")
    estimated_steps: int | None = Field(None, description="Estimated reasoning steps")
    confidence: float | None = Field(None, description="Classification confidence")
    reasoning: str | None = Field(None, description="Classification reasoning")

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, v: str) -> str:
        valid_types = ["simple", "multi_part", "comparison", "causal", "complex_analytical"]
        if v not in valid_types:
            raise ValueError(f"question_type must be one of {valid_types}")
        return v

    @field_validator("complexity_level")
    @classmethod
    def validate_complexity_level(cls, v: str) -> str:
        valid_levels = ["low", "medium", "high", "very_high"]
        if v not in valid_levels:
            raise ValueError(f"complexity_level must be one of {valid_levels}")
        return v

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float | None) -> float | None:
        if v is not None and (v < 0 or v > 1):
            raise ValueError("confidence must be between 0 and 1")
        return v

    @field_validator("estimated_steps")
    @classmethod
    def validate_estimated_steps(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("estimated_steps must be greater than 0")
        return v
