# Data Flow

This document describes the data flow through RAG Modulo, from user requests to responses, covering the complete lifecycle of search queries, document processing, and authentication.

## Search Request Flow

### Overview

RAG Modulo uses a **6-stage pipeline architecture** for processing search queries:

```
1. Pipeline Resolution → 2. Query Enhancement → 3. Retrieval
→ 4. Reranking → 5. Reasoning (CoT) → 6. Generation
```

### Detailed Flow

```
┌─────────────┐
│   User      │
│  (Frontend) │
└──────┬──────┘
       │ POST /api/search { question, collection_id }
       ↓
┌──────────────────────────────────────────────────┐
│            API Gateway (FastAPI)                 │
│  - JWT Middleware validates token                │
│  - Extract user_id from token (not client input) │
│  - Inject dependencies (SearchService, db)       │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│        SearchRouter (search_router.py)           │
│  - Validate SearchInput schema                   │
│  - Override user_id from JWT token (security)    │
│  - Call SearchService.search()                   │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│       SearchService (search_service.py)          │
│                                                  │
│  Stage 1: Pipeline Resolution                    │
│  ┌────────────────────────────────────────────┐ │
│  │ - Get user's default pipeline              │ │
│  │ - Create pipeline if none exists           │ │
│  │ - Load pipeline configuration              │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  Stage 2: Query Enhancement                      │
│  ┌────────────────────────────────────────────┐ │
│  │ - Analyze query complexity                 │ │
│  │ - Rewrite query for better retrieval       │ │
│  │ - Add conversation context if available    │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  Stage 3: Retrieval                              │
│  ┌────────────────────────────────────────────┐ │
│  │ - Generate embeddings for query            │ │
│  │ - Search vector database (Milvus)          │ │
│  │ - Retrieve top_k documents                 │ │
│  │ - Filter by collection_id                  │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  Stage 4: Reranking                              │
│  ┌────────────────────────────────────────────┐ │
│  │ - Apply cross-encoder reranking            │ │
│  │ - Score documents for relevance            │ │
│  │ - Reorder results by score                 │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  Stage 5: Reasoning (Chain of Thought)           │
│  ┌────────────────────────────────────────────┐ │
│  │ - Detect if complex question               │ │
│  │ - Decompose into sub-questions             │ │
│  │ - Execute iterative reasoning              │ │
│  │ - Accumulate context across steps          │ │
│  │ - Apply quality scoring (0.0-1.0)          │ │
│  │ - Retry if quality < 0.6 (up to 3x)        │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  Stage 6: Generation                             │
│  ┌────────────────────────────────────────────┐ │
│  │ - Build context from retrieved docs        │ │
│  │ - Load prompt template                     │ │
│  │ - Call LLM provider (WatsonX/OpenAI/etc)   │ │
│  │ - Parse structured output (XML/JSON)       │ │
│  │ - Extract answer and thinking              │ │
│  │ - Track token usage                        │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│          SearchOutput Response                   │
│  {                                               │
│    answer: "Generated answer...",                │
│    documents: [{...}, {...}],                    │
│    query_results: [...],                         │
│    rewritten_query: "Enhanced query",            │
│    cot_output: {                                 │
│      reasoning_steps: [...],                     │
│      quality_score: 0.85                         │
│    },                                            │
│    token_warning: {...},                         │
│    execution_time: 2.45                          │
│  }                                               │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────┐
│   Frontend   │
│  - Display   │
│  - Sources   │
│  - CoT Steps │
└──────────────┘
```

### Request Processing Details

#### Stage 1: Pipeline Resolution

```python
async def _resolve_user_default_pipeline(self, user_id: UUID4) -> Pipeline:
    # Get user's LLM provider configuration
    provider = await self.llm_provider_service.get_user_provider(user_id)

    # Get or create default pipeline
    pipeline = await self.pipeline_service.get_user_default_pipeline(
        user_id=user_id,
        provider=provider
    )

    # Create pipeline if none exists
    if not pipeline:
        pipeline = await self.pipeline_service.create_default_pipeline(
            user_id=user_id,
            provider=provider
        )

    return pipeline
```

#### Stage 2: Query Enhancement

```python
async def _enhance_query(self, query: str, context: SearchContext) -> str:
    # Check if query needs enhancement
    if len(query.split()) < 5:
        return query  # Short queries don't need enhancement

    # Use query rewriter
    rewriter = await self.pipeline_service.get_query_rewriter(
        context.user_id
    )

    # Enhance with conversation context
    conversation_history = await self._get_conversation_history(
        context.conversation_id
    )

    enhanced = await rewriter.rewrite(
        query=query,
        conversation_history=conversation_history
    )

    return enhanced
```

#### Stage 3: Retrieval

```python
async def _retrieve_documents(
    self,
    query: str,
    collection_id: UUID4,
    top_k: int = 10
) -> list[QueryResult]:
    # Generate embeddings
    embeddings = await self.embedding_service.embed_text(query)

    # Search vector database
    results = await self.vector_store.search(
        collection_name=str(collection_id),
        query_vector=embeddings,
        top_k=top_k,
        filters={"collection_id": str(collection_id)}
    )

    return results
```

#### Stage 5: Chain of Thought Reasoning

```python
async def _apply_chain_of_thought(
    self,
    question: str,
    documents: list[Document],
    context: SearchContext
) -> ChainOfThoughtOutput:
    # 1. Classify question
    classification = await self.cot_service.classify_question(question)

    if not classification.requires_cot:
        return None  # Skip CoT for simple questions

    # 2. Decompose question
    decomposition = await self.cot_service.decompose_question(
        question=question,
        max_depth=3
    )

    # 3. Execute reasoning steps
    reasoning_steps = []
    accumulated_context = []

    for sub_question in decomposition.sub_questions:
        # Search for each sub-question
        sub_result = await self._retrieve_documents(
            query=sub_question,
            collection_id=context.collection_id
        )

        # Build reasoning with accumulated context
        reasoning = await self._build_reasoning_step(
            sub_question=sub_question,
            documents=sub_result,
            accumulated_context=accumulated_context
        )

        # Quality check with retry logic
        if reasoning.quality_score < 0.6:
            reasoning = await self._retry_reasoning(
                sub_question,
                documents,
                max_retries=3
            )

        reasoning_steps.append(reasoning)
        accumulated_context.append(reasoning.reasoning)

    # 4. Synthesize final answer
    final_answer = await self.cot_service.synthesize(
        original_question=question,
        reasoning_steps=reasoning_steps
    )

    return ChainOfThoughtOutput(
        reasoning_steps=reasoning_steps,
        final_answer=final_answer,
        quality_score=final_answer.quality_score
    )
```

#### Stage 6: Generation

```python
async def _generate_answer(
    self,
    question: str,
    documents: list[Document],
    cot_output: ChainOfThoughtOutput | None,
    context: SearchContext
) -> str:
    # Build context from documents
    context_text = self._build_context(documents)

    # Add CoT reasoning if available
    if cot_output:
        context_text += f"\n\nReasoning:\n{cot_output.final_answer}"

    # Load prompt template
    template = await self.prompt_service.get_template(
        name="rag_generation",
        user_id=context.user_id
    )

    # Format prompt
    prompt = template.format(
        question=question,
        context=context_text
    )

    # Call LLM provider
    provider = await self.llm_provider_factory.get_provider(
        provider_name=context.provider_name,
        model_id=context.model_id
    )

    # Generate with structured output
    response = await provider.generate_response(
        prompt=prompt,
        max_tokens=1024,
        temperature=0.7
    )

    # Parse structured output (XML tags)
    parsed = self._parse_llm_response(response)

    # Track token usage
    await self.token_service.track_usage(
        user_id=context.user_id,
        tokens=parsed.token_count
    )

    return parsed.answer
```

## Document Processing Flow

### Upload and Processing Pipeline

```
┌─────────────┐
│   User      │
│  Uploads    │
│  Document   │
└──────┬──────┘
       │ POST /api/files/upload
       ↓
┌──────────────────────────────────────────────────┐
│         FileRouter (file_router.py)              │
│  - Validate file type and size                   │
│  - Create Collection if needed                   │
│  - Store file in MinIO                           │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│    FileManagementService (file_service.py)       │
│  - Save file to object storage (MinIO)           │
│  - Create File record in database                │
│  - Set status = PROCESSING                       │
│  - Trigger document processing                   │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│   DocumentProcessor (document_processor.py)      │
│                                                  │
│  1. Detect file format (.pdf, .docx, etc)        │
│  ┌────────────────────────────────────────────┐ │
│  │ - Use file extension                       │ │
│  │ - Select appropriate processor             │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  2. Extract content using Docling                │
│  ┌────────────────────────────────────────────┐ │
│  │ PDF: Text + tables + OCR images            │ │
│  │ DOCX: Structured document parsing          │ │
│  │ PPTX: Slide content extraction             │ │
│  │ XLSX: Sheet and table processing           │ │
│  │ Images: OCR text extraction                │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  3. Generate chunks (hierarchical strategy)      │
│  ┌────────────────────────────────────────────┐ │
│  │ - Split into semantic chunks               │ │
│  │ - Maintain context across chunks           │ │
│  │ - Add metadata (page, section, etc)        │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  4. Generate embeddings                          │
│  ┌────────────────────────────────────────────┐ │
│  │ - Call embedding model                     │ │
│  │ - Create vector representations            │ │
│  │ - Batch processing for efficiency          │ │
│  └────────────────────────────────────────────┘ │
│                      ↓                           │
│  5. Store in vector database                     │
│  ┌────────────────────────────────────────────┐ │
│  │ - Create collection if needed              │ │
│  │ - Insert vectors with metadata             │ │
│  │ - Index for fast retrieval                 │ │
│  └────────────────────────────────────────────┘ │
│                                                  │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│         Update File Status                       │
│  - Set status = COMPLETED                        │
│  - Update collection status                      │
│  - Generate suggested questions                  │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────┐
│   Notify     │
│   Frontend   │
│  (WebSocket) │
└──────────────┘
```

### Document Processing Code Example

```python
async def process_document(
    self,
    file_path: str,
    collection_id: UUID4,
    user_id: UUID4
) -> ProcessingResult:
    # 1. Detect file type
    file_type = self._detect_file_type(file_path)

    # 2. Get appropriate processor
    processor = self._get_processor(file_type)

    # 3. Extract content
    documents = []
    async for doc in processor.process(file_path, collection_id):
        documents.append(doc)

    # 4. Generate embeddings
    for doc in documents:
        doc.embedding = await self.embedding_service.embed_text(doc.content)

    # 5. Store in vector database
    await self.vector_store.insert(
        collection_name=str(collection_id),
        documents=documents
    )

    # 6. Update status
    await self.file_repository.update_status(
        file_id=file_id,
        status=FileStatus.COMPLETED
    )

    return ProcessingResult(
        success=True,
        chunks_created=len(documents),
        collection_id=collection_id
    )
```

## Authentication Flow

### OIDC Authentication with IBM Cloud Identity

```
┌─────────────┐
│   User      │
│  (Browser)  │
└──────┬──────┘
       │ Click "Login"
       ↓
┌──────────────────────────────────────────────────┐
│         Frontend (React)                         │
│  - Redirect to OIDC provider                     │
│  - URL: /api/auth/login                          │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│      IBM Cloud Identity (OIDC Provider)          │
│  - User enters credentials                       │
│  - Two-factor authentication (if enabled)        │
│  - Generate authorization code                   │
└──────┬───────────────────────────────────────────┘
       │ Redirect to callback URL
       │ with authorization code
       ↓
┌──────────────────────────────────────────────────┐
│       AuthRouter (auth_router.py)                │
│  - Exchange code for tokens                      │
│  - Validate ID token signature                   │
│  - Extract user info (sub, email, name)          │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│         UserService (user_service.py)            │
│  - Find or create user in database               │
│  - Update user profile                           │
│  - Initialize user defaults (pipeline, provider) │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│         Generate JWT Token                       │
│  - Sign token with JWT_SECRET_KEY                │
│  - Include: user_id, email, name, role           │
│  - Set expiration (24 hours)                     │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│         Return to Frontend                       │
│  - Store JWT in localStorage                     │
│  - Include in all API requests                   │
│  - Header: Authorization: Bearer <token>         │
└──────────────────────────────────────────────────┘
```

### Subsequent API Requests

```
┌─────────────┐
│   User      │
│  (Frontend) │
└──────┬──────┘
       │ API Request + JWT Token
       ↓
┌──────────────────────────────────────────────────┐
│     Authentication Middleware                    │
│  1. Extract token from Authorization header      │
│  2. Verify JWT signature                         │
│  3. Check expiration                             │
│  4. Validate issuer and audience                 │
│  5. Extract user claims                          │
│  6. Add user to request.state.user               │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│        Router Endpoint                           │
│  - Use get_current_user() dependency             │
│  - Access user_id from JWT (never client input)  │
│  - Verify resource ownership                     │
└──────────────────────────────────────────────────┘
```

## Conversation Flow

### Chat History Management

```
┌─────────────┐
│   User      │
│  Sends      │
│  Message    │
└──────┬──────┘
       │ POST /api/conversations/message
       ↓
┌──────────────────────────────────────────────────┐
│   ConversationRouter (conversation_router.py)    │
│  - Get or create conversation session            │
│  - Store user message                            │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│       SearchService (search_service.py)          │
│  - Load conversation history                     │
│  - Add context to query enhancement              │
│  - Execute search pipeline                       │
│  - Generate answer                               │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────────────────────────────────────────┐
│       Store Assistant Response                   │
│  - Save message to database                      │
│  - Update conversation summary                   │
│  - Track token usage                             │
└──────┬───────────────────────────────────────────┘
       ↓
┌──────────────┐
│   Return to  │
│   Frontend   │
│  (WebSocket) │
└──────────────┘
```

## Data Persistence

### Database Operations

**PostgreSQL** stores all metadata:
- User accounts and profiles
- Collection metadata
- File metadata and status
- Conversation history
- Pipeline configurations
- LLM provider settings
- Token usage tracking

**Milvus** stores vector embeddings:
- Document chunk embeddings
- Collection-based isolation
- Efficient similarity search
- Automatic indexing

**MinIO** stores binary files:
- Uploaded documents
- Generated podcasts
- Temporary processing files
- Model artifacts

## Related Documentation

- [Components](components.md) - System architecture
- [Security](security.md) - Authentication details
- [Performance](performance.md) - Optimization strategies
