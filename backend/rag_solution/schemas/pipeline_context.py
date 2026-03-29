"""Pipeline context -- all config needed for a search request, fetched in one composite query."""

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class PipelineContext:
    """Read-only config snapshot for the search pipeline.

    Fetched once per request via ``PipelineContextRepository.get_context()``,
    then threaded through all pipeline stages so they never need to hit the DB
    individually.
    """

    # Pipeline
    pipeline_id: UUID
    retriever_type: str
    max_context_length: int

    # Provider
    provider_name: str
    provider_base_url: str
    provider_api_key: str
    provider_project_id: str | None

    # Models -- list of (model_id, model_type) tuples
    models: tuple[tuple[str, str], ...] = field(default_factory=tuple)

    # Generation params
    max_new_tokens: int = 100
    temperature: float = 0.7
    top_k: int = 50
    top_p: float = 1.0
    repetition_penalty: float = 1.1

    # Template
    template_id: UUID | None = None
    template_format: str = ""
    system_prompt: str = "You are a helpful AI assistant."

    # Collection
    vector_db_name: str = ""
    collection_id: UUID | None = None
