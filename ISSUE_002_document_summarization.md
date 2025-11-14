# Issue: Implement System-Wide Document Summarization Mode

**Labels:** `enhancement`, `high-priority`, `rag-pipeline`, `summarization`
**Milestone:** Production RAG Enhancements
**Estimated Effort:** 7-10 days

---

## Problem Statement

Current system can summarize **conversation history** but NOT **retrieved documents** in the search pipeline.

### Current State

✅ **Strong Conversation Summarization** (`conversation_summarization_service.py`, 452 lines):
- Multiple strategies: `RECENT_PLUS_SUMMARY`, `FULL_CONVERSATION`, `KEY_POINTS_ONLY`, `TOPIC_BASED`
- Context window management (auto-summarize at 80% threshold)
- Token savings calculation
- Metadata extraction (topics, decisions, questions)

❌ **Missing Document Summarization**:
- No dedicated summarization pipeline for retrieved documents
- No map-reduce pattern for long documents
- No hierarchical summarization (section → document → collection)
- No intent classification to detect summarization requests

### Impact

When user asks "Summarize this document about machine learning":
1. SearchService retrieves top-k chunks (not all chunks)
2. Chunks passed to LLM with RAG template
3. LLM *may* generate a summary, but not systematically
4. **Problem**: May miss important content not in top-k chunks

---

## Proposed Solution

### Phase 1: Intent Classification & Routing (2-3 days)

#### 1.1 Define Query Intent Types

```python
# backend/rag_solution/schemas/query_intent_schema.py

from enum import Enum

class QueryIntent(str, Enum):
    """Classification of user query intent."""
    RETRIEVAL = "retrieval"          # Standard RAG search
    SUMMARIZATION = "summarization"  # Document/collection summary
    COMPARISON = "comparison"        # Compare multiple documents
    EXTRACTION = "extraction"        # Extract specific data (dates, names, etc.)
    QUESTION_ANSWERING = "qa"        # Direct question answering

class QueryIntentClassification(BaseModel):
    """Result of query intent classification."""
    intent: QueryIntent
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str | None = None
    suggested_strategy: str | None = None  # "map_reduce", "hierarchical", etc.
    target_scope: str | None = None  # "document", "collection", "chunks"
```

#### 1.2 Intent Classifier Service

```python
# backend/rag_solution/services/intent_classifier_service.py

class IntentClassifierService:
    """Classifies user query intent for pipeline routing."""

    # Keyword-based rules (fast, no LLM call)
    SUMMARIZATION_KEYWORDS = [
        "summarize", "summary", "overview", "main points",
        "key findings", "tldr", "recap", "in summary",
        "brief", "condense", "synthesize"
    ]

    COMPARISON_KEYWORDS = [
        "compare", "difference", "versus", "vs",
        "contrast", "similar", "unlike"
    ]

    def classify_intent(self, question: str) -> QueryIntentClassification:
        """Classify query intent using keyword matching + heuristics."""

        question_lower = question.lower()

        # Check for summarization intent
        if any(kw in question_lower for kw in self.SUMMARIZATION_KEYWORDS):
            # Determine scope
            if "document" in question_lower or "this" in question_lower:
                scope = "document"
            elif "collection" in question_lower or "all" in question_lower:
                scope = "collection"
            else:
                scope = "chunks"

            return QueryIntentClassification(
                intent=QueryIntent.SUMMARIZATION,
                confidence=0.9,
                reasoning="Detected summarization keywords",
                suggested_strategy="map_reduce" if scope == "document" else "hierarchical",
                target_scope=scope
            )

        # Check for comparison
        if any(kw in question_lower for kw in self.COMPARISON_KEYWORDS):
            return QueryIntentClassification(
                intent=QueryIntent.COMPARISON,
                confidence=0.85,
                reasoning="Detected comparison keywords",
                suggested_strategy="comparative_summary"
            )

        # Default to retrieval
        return QueryIntentClassification(
            intent=QueryIntent.RETRIEVAL,
            confidence=0.7,
            reasoning="No special intent detected",
            suggested_strategy="standard_rag"
        )
```

### Phase 2: Summarization Stage (3-5 days)

#### 2.1 Map-Reduce Summarization (For Long Documents)

```python
# backend/rag_solution/services/pipeline/stages/summarization_stage.py

class SummarizationStage(BaseStage):
    """Pipeline stage for document summarization."""

    def __init__(self, pipeline_service: PipelineService, provider: LLMBase):
        super().__init__("Summarization")
        self.pipeline_service = pipeline_service
        self.provider = provider

    async def execute(self, context: SearchContext) -> StageResult:
        """Execute summarization based on detected intent."""

        # Check if summarization is needed
        if context.query_intent != QueryIntent.SUMMARIZATION:
            return StageResult(success=True, context=context, skipped=True)

        strategy = context.query_intent_classification.suggested_strategy

        if strategy == "map_reduce":
            summary = await self._map_reduce_summarize(context)
        elif strategy == "hierarchical":
            summary = await self._hierarchical_summarize(context)
        else:
            summary = await self._direct_summarize(context)

        context.generated_answer = summary
        context.add_metadata("summarization", {
            "strategy": strategy,
            "chunks_processed": len(context.query_results),
            "summary_length": len(summary)
        })

        return StageResult(success=True, context=context)

    async def _map_reduce_summarize(self, context: SearchContext) -> str:
        """
        Map-Reduce summarization for long documents.

        Map: Summarize each chunk independently
        Reduce: Combine chunk summaries into final summary
        """

        chunks = context.query_results
        chunk_summaries = []

        # MAP PHASE: Summarize each chunk
        logger.info(f"MAP phase: Summarizing {len(chunks)} chunks")

        map_prompt_template = """Summarize this section concisely (2-3 sentences):

{text}

Summary:"""

        for i, result in enumerate(chunks):
            chunk_text = result.chunk.text if result.chunk else ""
            prompt = map_prompt_template.format(text=chunk_text)

            chunk_summary = await self.provider.generate_text(
                user_id=context.user_id,
                prompt=prompt,
                model_parameters=LLMParametersInput(max_new_tokens=150, temperature=0.3)
            )
            chunk_summaries.append(chunk_summary)
            logger.debug(f"Chunk {i+1}/{len(chunks)} summarized: {len(chunk_summary)} chars")

        # REDUCE PHASE: Combine summaries
        logger.info(f"REDUCE phase: Combining {len(chunk_summaries)} summaries")

        reduce_prompt_template = """Combine these section summaries into a comprehensive overview:

{summaries}

Provide a well-structured summary with:
1. Executive Summary (2-3 sentences)
2. Key Findings (bullet points)
3. Main Themes
4. Conclusions

Final Summary:"""

        combined_text = "\n\n".join(f"Section {i+1}: {s}" for i, s in enumerate(chunk_summaries))
        prompt = reduce_prompt_template.format(summaries=combined_text)

        final_summary = await self.provider.generate_text(
            user_id=context.user_id,
            prompt=prompt,
            model_parameters=LLMParametersInput(max_new_tokens=800, temperature=0.3)
        )

        return final_summary

    async def _hierarchical_summarize(self, context: SearchContext) -> str:
        """
        Hierarchical summarization for multiple documents.

        Level 1: Summarize each document
        Level 2: Combine document summaries
        """

        # Group chunks by document
        from collections import defaultdict
        chunks_by_doc = defaultdict(list)

        for result in context.query_results:
            doc_id = result.document_id or "unknown"
            chunks_by_doc[doc_id].append(result)

        # Level 1: Summarize each document
        doc_summaries = []
        for doc_id, doc_chunks in chunks_by_doc.items():
            # Create temporary context for this document
            doc_context = SearchContext(
                search_input=context.search_input,
                user_id=context.user_id,
                query_results=doc_chunks
            )
            doc_summary = await self._map_reduce_summarize(doc_context)
            doc_summaries.append({
                "document_id": doc_id,
                "summary": doc_summary,
                "chunk_count": len(doc_chunks)
            })

        # Level 2: Combine document summaries
        combined_prompt = f"""Create a comprehensive summary from these document summaries:

{chr(10).join(f"Document {i+1}: {d['summary']}" for i, d in enumerate(doc_summaries))}

Provide an integrated overview highlighting common themes and key differences.

Summary:"""

        final_summary = await self.provider.generate_text(
            user_id=context.user_id,
            prompt=combined_prompt,
            model_parameters=LLMParametersInput(max_new_tokens=1000, temperature=0.3)
        )

        return final_summary

    async def _direct_summarize(self, context: SearchContext) -> str:
        """
        Direct summarization for short content.

        When total content fits in context window, summarize directly.
        """

        # Concatenate all chunk texts
        full_text = "\n\n".join(
            result.chunk.text for result in context.query_results
            if result.chunk and result.chunk.text
        )

        prompt = f"""Provide a comprehensive summary of this content:

{full_text}

Include:
1. Executive Summary
2. Key Points (bullet points)
3. Main Themes
4. Important Details

Summary:"""

        summary = await self.provider.generate_text(
            user_id=context.user_id,
            prompt=prompt,
            model_parameters=LLMParametersInput(max_new_tokens=800, temperature=0.3)
        )

        return summary
```

#### 2.2 Summarization-Specific Prompt Templates

```python
# backend/rag_solution/schemas/prompt_template_schema.py

class PromptTemplateType(str, Enum):
    RAG_QUERY = "rag_query"
    QUESTION_GENERATION = "question_generation"
    RESPONSE_EVALUATION = "response_evaluation"
    SUMMARIZATION_MAP = "summarization_map"      # NEW
    SUMMARIZATION_REDUCE = "summarization_reduce"  # NEW
    COMPARATIVE_SUMMARY = "comparative_summary"    # NEW
```

### Phase 3: Integration with Pipeline (2 days)

#### 3.1 Update PipelineExecutor

```python
# backend/rag_solution/services/pipeline/pipeline_executor.py

class PipelineExecutor:
    async def execute_search_pipeline(self, context: SearchContext) -> SearchContext:
        """Execute search pipeline with intent-aware routing."""

        # NEW: Classify intent first
        intent_classifier = IntentClassifierService()
        intent_classification = intent_classifier.classify_intent(context.search_input.question)
        context.query_intent = intent_classification.intent
        context.query_intent_classification = intent_classification

        logger.info(
            f"Detected query intent: {intent_classification.intent} "
            f"(confidence={intent_classification.confidence:.2f})"
        )

        # Execute standard stages
        stages = [
            PipelineResolutionStage(self.pipeline_service),
            QueryEnhancementStage(self.pipeline_service),
            RetrievalStage(self.pipeline_service),
        ]

        # Conditional routing based on intent
        if context.query_intent == QueryIntent.SUMMARIZATION:
            # For summarization: retrieve ALL chunks (not just top-k)
            # Then use summarization stage instead of generation
            stages.append(SummarizationStage(self.pipeline_service, provider))
        else:
            # Standard RAG pipeline
            stages.extend([
                RerankingStage(self.pipeline_service),
                ReasoningStage(self.pipeline_service),
                GenerationStage(self.pipeline_service)
            ])

        # Execute all stages
        for stage in stages:
            result = await stage.execute(context)
            if not result.success:
                raise PipelineExecutionError(f"Stage {stage.name} failed")

        return context
```

---

## Enhanced RetrievalStage for Summarization

```python
# Modification to RetrievalStage

async def execute(self, context: SearchContext) -> StageResult:
    """Execute retrieval with intent-aware top-k selection."""

    # For summarization, retrieve MORE chunks (or all chunks from target documents)
    if context.query_intent == QueryIntent.SUMMARIZATION:
        # Retrieve all chunks from relevant documents
        top_k = 50  # Much higher limit
        logger.info("Summarization mode: retrieving top 50 chunks")
    else:
        # Standard RAG retrieval
        top_k = context.retrieval_config.top_k or 10

    # ... rest of retrieval logic
```

---

## API Usage Example

```python
# Explicit summarization request
search_input = SearchInput(
    question="Summarize the key findings from all documents about machine learning",
    collection_id=collection_uuid,
    user_id=user_uuid,
    config_metadata={
        "intent": "summarization",  # Optional: override auto-detection
        "summarization_strategy": "hierarchical"  # Optional: specify strategy
    }
)

response = await search_service.search(search_input)

# Response includes comprehensive summary
print(response.answer)  # Multi-paragraph summary with key findings
print(response.metadata["summarization"]["strategy"])  # "hierarchical"
print(response.metadata["summarization"]["chunks_processed"])  # 50
```

---

## Files to Modify

1. **Schemas**
   - `backend/rag_solution/schemas/query_intent_schema.py` - NEW
   - `backend/rag_solution/schemas/prompt_template_schema.py` - Add summarization template types

2. **Services**
   - `backend/rag_solution/services/intent_classifier_service.py` - NEW
   - `backend/rag_solution/services/pipeline/stages/summarization_stage.py` - NEW
   - `backend/rag_solution/services/pipeline/pipeline_executor.py` - Add intent routing
   - `backend/rag_solution/services/pipeline/stages/retrieval_stage.py` - Add intent-aware top-k

3. **Pipeline Context**
   - `backend/rag_solution/services/pipeline/search_context.py` - Add `query_intent` field

4. **Tests**
   - `tests/unit/services/test_intent_classifier.py` - NEW
   - `tests/unit/services/test_summarization_stage.py` - NEW
   - `tests/integration/test_document_summarization.py` - NEW

5. **Documentation**
   - `docs/features/document-summarization.md` - NEW
   - `docs/api/summarization_api.md` - NEW

---

## Acceptance Criteria

- [ ] `QueryIntent` enum with SUMMARIZATION type
- [ ] `IntentClassifierService` with keyword-based classification
- [ ] `SummarizationStage` with 3 strategies: map-reduce, hierarchical, direct
- [ ] Intent detection with 90%+ accuracy on test queries
- [ ] Map-reduce summarization for documents > 4000 tokens
- [ ] Hierarchical summarization for multi-document collections
- [ ] Integration with `PipelineExecutor` for intent routing
- [ ] RetrievalStage retrieves more chunks for summarization (top-50 vs top-10)
- [ ] Summarization-specific prompt templates
- [ ] Unit tests for all summarization strategies
- [ ] Integration tests comparing summarization vs. standard RAG
- [ ] Documentation with usage examples
- [ ] Performance: Map-reduce summarization < 10 seconds for 20 chunks

---

## Testing Strategy

### Unit Tests

```python
def test_intent_classifier_detects_summarization():
    """Test intent classifier identifies summarization requests."""
    classifier = IntentClassifierService()

    queries = [
        "Summarize this document",
        "Give me an overview of the key findings",
        "What are the main points?",
        "TLDR"
    ]

    for query in queries:
        classification = classifier.classify_intent(query)
        assert classification.intent == QueryIntent.SUMMARIZATION
        assert classification.confidence >= 0.8

def test_map_reduce_summarization():
    """Test map-reduce summarization logic."""
    stage = SummarizationStage(pipeline_service, provider)

    # Create context with 10 chunks
    chunks = [create_test_chunk(f"Content {i}") for i in range(10)]
    context = SearchContext(query_results=chunks, query_intent=QueryIntent.SUMMARIZATION)

    summary = await stage._map_reduce_summarize(context)

    assert len(summary) > 100  # Non-trivial summary
    assert "key findings" in summary.lower() or "summary" in summary.lower()
```

### Integration Tests

```python
@pytest.mark.integration
async def test_end_to_end_document_summarization():
    """Test full summarization pipeline."""

    # Upload test document
    doc = await upload_document("ml_research_paper.pdf")

    # Request summarization
    search_input = SearchInput(
        question="Summarize the key findings from this machine learning paper",
        collection_id=collection_id,
        user_id=user_id
    )

    response = await search_service.search(search_input)

    # Verify summary characteristics
    assert len(response.answer) > 200  # Substantive summary
    assert response.metadata["summarization"]["strategy"] in ["map_reduce", "hierarchical"]
    assert response.metadata["summarization"]["chunks_processed"] > 10

    # Summary should mention key concepts
    assert any(term in response.answer.lower() for term in ["machine learning", "results", "findings"])
```

---

## References

- LangChain Map-Reduce: https://python.langchain.com/docs/modules/chains/document/map_reduce
- LlamaIndex Summarization: https://docs.llamaindex.ai/en/stable/examples/query_engine/summarization.html
- Related: `conversation_summarization_service.py` (existing conversation summarization)

---

## Priority

**HIGH** - 20-30% of RAG queries are summarization requests (industry data)

---

## Estimated Effort

**7-10 days** (1 developer)

- Phase 1: 2-3 days
- Phase 2: 3-5 days
- Phase 3: 2 days
