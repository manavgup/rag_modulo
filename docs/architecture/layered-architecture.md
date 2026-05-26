# Layered Architecture: Router → Service → Repository

RAG Modulo uses a strict 3-layer separation with FastAPI dependency injection. Every request follows the same path: router validates and delegates, service owns the logic, repository talks to the database.

## The Layers

![Layered Architecture — Request Flow with Code](../diagrams/09-layered-architecture-detail.svg)

### Router Layer (18 routers)

Thin HTTP controllers. Each router defines FastAPI endpoints with `@router.get/post`, validates input via Pydantic schemas, extracts the authenticated user, and delegates to a service injected via `Depends()`.

```python
# backend/rag_solution/router/search_router.py
@router.post("", response_model=SearchOutput)
async def search(
    search_input: SearchInput,
    current_user: Annotated[dict, Depends(get_current_user)],
    search_service: Annotated[SearchService, Depends(get_search_service)],
) -> SearchOutput:
```

**Rule**: No business logic in routers. If a router method is longer than 10 lines, the logic belongs in a service.

### Service Layer (36 services)

All business logic lives here. Services receive dependencies via constructor injection, wired in `core/dependencies.py`. Services call repositories for data access — they never use `db.query()` directly.

```python
# backend/rag_solution/services/search_service.py
class SearchService:
    async def search(self, search_input: SearchInput) -> SearchOutput:
        self._validate_search_input(search_input)
        self._validate_collection_access(search_input.collection_id, search_input.user_id)
        return await self.pipeline.execute(ctx)
```

Services are grouped by domain:
- **Search**: SearchService, ChainOfThoughtService, EntityExtractionService, pipeline stages
- **Conversation**: ConversationService, MessageProcessingOrchestrator, ConversationContextService
- **LLM Config**: PipelineService, LLMProviderService, LLMModelService, LLMParametersService, PromptTemplateService
- **Data + Content**: CollectionService, FileManagementService, UserService, PodcastService, VoiceService

### Repository Layer (19 repositories)

Data access only. Each repository receives a SQLAlchemy `Session`, performs queries, and returns **database models** (never Pydantic schemas — lesson from [PR #587](https://github.com/manavgup/rag_modulo/pull/587)).

```python
# backend/rag_solution/repository/collection_repository.py
class CollectionRepository:
    def get(self, collection_id: UUID) -> Collection:
        return self.db.query(Collection)
            .options(joinedload(Collection.users), joinedload(Collection.files))
            .filter(Collection.id == collection_id)
            .first()
```

Uses `joinedload()` to prevent N+1 queries. The conversation repository consolidation reduced session listing from 54 queries to 1.

### Database Layer

- **PostgreSQL** — relational data (users, collections, conversations, config)
- **Milvus** — vector embeddings for similarity search (primary vector store)
- **MinIO** — object storage for uploaded documents
- **MLFlow** — experiment tracking and evaluation

## Dependency Injection

`core/dependencies.py` contains 19 factory functions that create service instances with their dependencies:

```python
def get_search_service(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings)
) -> SearchService:
    return SearchService(db, settings)
```

For the complex `MessageProcessingOrchestrator`, shared leaf services are created once and forwarded to all consumers to prevent duplicate DB queries (lesson from [PR #782–#785](https://github.com/manavgup/rag_modulo/pull/782)).

## Cross-Cutting Concerns

- **Authentication**: `AuthenticationMiddleware` (JWT validation, dev bypass)
- **Schemas**: 25 Pydantic models for input validation and output serialization
- **Logging**: Structured logging via `core.enhanced_logging`
- **Performance**: `PipelineContext` (frozen dataclass, fetched once per request) and `ConfigCache` (request-scoped dict cache)

## Related

- [Full system architecture diagram](../diagrams/06-architecture.svg) — all 18 routers, 36 services, 19 repositories with dependency annotations
- [Design patterns](../diagrams/08-design-patterns.svg) — Factory, Repository, Pipeline, Circuit Breaker, Strategy, and 5 more
- [Search pipeline stages](../diagrams/02-pipeline-stages.svg) — the 6-stage composable search flow
- [DB query reduction](../diagrams/05-query-reduction.svg) — PipelineContext and conversation consolidation
- [LESSONS_LEARNED.md](../../LESSONS_LEARNED.md) — architecture decisions that paid off and didn't
- [Issue #773 — RAG quality investigation](../debug/issue-773-rag-quality-investigation.md) — full pipeline trace of a hallucination
- [Issue #777 — DB query trace](../debug/issue-777-db-query-trace.md) — 44 numbered SQL queries mapped to call sites
