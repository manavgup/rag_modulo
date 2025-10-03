# ADR-001: Podcast Content Retrieval Strategy

- **Status:** Proposed
- **Date:** 2025-10-02
- **Deciders:** Engineering Team, Product

## Context

For Issue #240 (Podcast Generation Epic), we need to determine how to retrieve and prepare content from a user's document collection for podcast script generation. Users upload documents to a collection, and we need to transform this content into an engaging podcast.

The key question is: **Should we use the existing RAG pipeline with a modified prompt, or implement a separate document retrieval mechanism?**

Key considerations:
- We already have a sophisticated RAG pipeline with reranking, hierarchical chunking, and quality enhancements
- Podcast generation needs comprehensive coverage of collection content, not just answers to specific questions
- The RAG pipeline is optimized for question-answering, but can be adapted for content synthesis
- Token limits constrain how much content we can feed to the LLM for script generation

## Decision

**We will use the existing RAG pipeline with a specialized podcast-generation prompt.**

The podcast generation workflow will:

1. **Create synthetic query** for comprehensive content retrieval:
   ```
   "Provide a comprehensive overview of all key topics, insights,
    and important information from this collection for creating
    an educational podcast."
   ```

2. **Use existing SearchService** with podcast-specific configuration:
   ```python
   search_input = SearchInput(
       user_id=user_id,
       collection_id=collection_id,
       question=synthetic_query,
       config_metadata={
           "top_k": 50,  # Retrieve more chunks for comprehensive coverage
           "enable_reranking": True,  # Quality ranking
           "enable_hierarchical": True,  # Parent-child context
           "cot_enabled": False,  # Skip reasoning for retrieval
       }
   )
   ```

3. **Feed RAG results to LLM** for Q&A dialogue script generation:
   ```
   System: "You are a professional podcast script writer.
            Create engaging conversational dialogue between a HOST and EXPERT."

   User: "Create a {duration}-minute podcast dialogue based on:
          {rag_results}

          Format as:
          HOST: [Question or introduction]
          EXPERT: [Detailed answer]"
   ```

## Consequences

### ✨ Positive Consequences

1. **Leverage Existing Infrastructure**
   - Reuses battle-tested RAG pipeline (reranking, hierarchical chunking from Issue #257)
   - No need to build separate document retrieval system
   - Automatic benefits from future RAG improvements

2. **Better Content Quality**
   - Semantic relevance through vector similarity
   - Reranking ensures best content surfaces first
   - Hierarchical chunking provides better context
   - Handles large document collections gracefully

3. **Consistent Architecture**
   - Same service patterns and dependencies
   - Familiar codebase for maintenance
   - Unified monitoring and observability

4. **Token Efficiency**
   - RAG retrieval naturally limits content to top-k results
   - Avoids overwhelming LLM with entire collection
   - Semantic search finds most relevant chunks

5. **Flexible Querying**
   - Can customize synthetic queries based on user preferences
   - Easy to add themed podcasts ("focus on AI ethics", "recent developments only")
   - Supports future features like topic-specific episodes

### ⚠️ Potential Risks

1. **Query Dependency**
   - Synthetic query quality affects retrieval results
   - May miss content if query is poorly formulated
   - **Mitigation:** Use well-tested generic queries; allow user customization in future

2. **Comprehensive Coverage**
   - top_k limits may exclude some content from large collections
   - **Mitigation:** Use higher top_k values (50+ chunks) for podcasts vs. search (5-10)

3. **RAG Pipeline Coupling**
   - Podcast generation depends on SearchService availability
   - Changes to RAG pipeline could affect podcast quality
   - **Mitigation:** Proper versioning and comprehensive tests

## Alternatives Considered

| Option | Why Not |
|--------|---------|
| **Direct Vector Store Query** | Would bypass reranking and hierarchical chunking improvements; no semantic relevance scoring; requires reimplementing document retrieval logic |
| **Fetch All Documents** | Exceeds token limits for large collections; includes irrelevant content; no quality filtering; high LLM costs |
| **Separate Summarization Pipeline** | Duplicates existing RAG infrastructure; higher maintenance burden; inconsistent quality vs. RAG results |
| **Collection-Level Embeddings** | Loses granular content detail; can't handle multi-topic collections; requires separate embedding strategy |

## Implementation Details

### Workflow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. User Uploads Documents → Collection                       │
│    (Existing ingestion pipeline)                             │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Documents Processed                                        │
│    - Chunked (hierarchical parent-child)                     │
│    - Embedded (vector representations)                       │
│    - Stored in Vector DB (Milvus)                            │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Podcast Generation Request                                │
│    POST /api/v1/podcasts/generate                            │
│    { collection_id, duration, voice_settings }               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. PodcastService.generate_podcast()                         │
│    - Validates collection, user, document count             │
│    - Creates podcast record (status: QUEUED)                │
│    - Triggers background processing                          │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. Content Retrieval via RAG Pipeline                        │
│                                                               │
│    PodcastService._retrieve_documents():                     │
│    ┌──────────────────────────────────────┐                 │
│    │ SearchInput(                          │                 │
│    │   question="Comprehensive overview   │                 │
│    │             of all topics...",        │                 │
│    │   collection_id=...,                 │                 │
│    │   config={                            │                 │
│    │     top_k: 50,                        │                 │
│    │     enable_reranking: true,          │                 │
│    │     enable_hierarchical: true        │                 │
│    │   }                                   │                 │
│    │ )                                     │                 │
│    └──────────────────────────────────────┘                 │
│                    ↓                                          │
│    ┌──────────────────────────────────────┐                 │
│    │ SearchService.search()                │                 │
│    │ - Vector similarity search            │                 │
│    │ - Hierarchical chunk expansion        │                 │
│    │ - Reranking (LLM-based scoring)       │                 │
│    │ - Returns top 50 most relevant        │                 │
│    │   chunks with context                 │                 │
│    └──────────────────────────────────────┘                 │
│                    ↓                                          │
│    Returns: DocumentMetadata[]                               │
│    - chunk_text                                              │
│    - source_document                                         │
│    - relevance_score                                         │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. Script Generation (LLM) - Q&A Dialogue Format             │
│                                                               │
│    Prompt:                                                    │
│    """                                                        │
│    System: You are a professional podcast script writer.     │
│    Create engaging dialogue between HOST and EXPERT.         │
│                                                               │
│    User: Create a {duration}-minute podcast dialogue based on│
│    the following information:                                │
│                                                               │
│    {rag_results}                                             │
│                                                               │
│    Format as conversational Q&A:                             │
│    HOST: [Question or introduction]                          │
│    EXPERT: [Detailed answer with examples]                   │
│    HOST: [Follow-up or transition]                           │
│    EXPERT: [Further explanation]                             │
│                                                               │
│    Requirements:                                              │
│    - Natural conversational flow                             │
│    - Approximately {word_count} words (150 wpm)              │
│    - HOST asks insightful questions                          │
│    - EXPERT provides detailed, engaging answers              │
│    - Include introduction and conclusion                     │
│    """                                                        │
│                                                               │
│    Output: Q&A dialogue script                               │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Script Parsing                                            │
│    - Parse script into turns (HOST/EXPERT)                   │
│    - Extract speaker and text for each turn                  │
│    - Calculate estimated duration per turn                   │
│    - Create PodcastScript model with list of PodcastTurn     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. Multi-Voice Audio Generation (Text-to-Speech)             │
│    For each turn in script:                                  │
│    - Generate audio with speaker-specific voice              │
│      • HOST: alloy voice (warm, conversational)              │
│      • EXPERT: onyx voice (authoritative, clear)             │
│    - Add 500ms pause between speakers                        │
│    - Track progress (completed_turns / total_turns)          │
│    - Combine segments into final audio file                  │
│    - Store audio file                                        │
│    - Update status: COMPLETED                                │
└─────────────────────────────────────────────────────────────┘
```

### Code Example

```python
async def _retrieve_documents(
    self,
    collection_id: UUID4,
    user_id: UUID4,
    duration: PodcastDuration
) -> list[DocumentMetadata]:
    """Retrieve documents using existing RAG pipeline."""

    # Adjust top_k based on podcast duration
    top_k_map = {
        PodcastDuration.SHORT: 30,      # 5 min
        PodcastDuration.MEDIUM: 50,     # 15 min
        PodcastDuration.LONG: 75,       # 30 min
        PodcastDuration.EXTENDED: 100,  # 60 min
    }

    synthetic_query = (
        "Provide a comprehensive overview of all key topics, main insights, "
        "important concepts, and significant information from this collection "
        "suitable for creating an educational podcast."
    )

    search_input = SearchInput(
        user_id=user_id,
        collection_id=collection_id,
        question=synthetic_query,
        config_metadata={
            "top_k": top_k_map[duration],
            "enable_reranking": True,
            "enable_hierarchical": True,
            "cot_enabled": False,  # Skip chain-of-thought for retrieval
        }
    )

    # Use existing SearchService
    search_result = await self.search_service.search(search_input)

    return search_result.documents
```

## Status

**Proposed** - Awaiting team discussion and approval.

This approach maximizes reuse of existing infrastructure while providing flexibility for future enhancements.

## Future Enhancements

1. **User-Customizable Queries:** Allow users to specify podcast theme/focus
2. **Multi-Query Strategy:** Run multiple synthetic queries to ensure comprehensive coverage
3. **Collection Summarization:** Pre-generate collection summaries for faster podcast generation
4. **Topic Extraction:** Identify main topics and ensure coverage in script
