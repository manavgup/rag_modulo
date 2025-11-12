# Testing Structured Output with Citations

This guide explains how to test the structured output functionality with the NewIBM collection.

## Current Implementation Status

✅ **Completed:**
- Template flexibility for structured output prompts
- All 3 providers support custom templates (OpenAI, Anthropic, WatsonX)
- Hybrid citation attribution (LLM + post-hoc fallback)
- Citation deduplication with multi-page support
- chunk_id and page_number integration in prompts

❌ **Not Yet Integrated:**
- SearchService integration (not exposed via API)
- Frontend UI for displaying citations
- API endpoints for structured output

## Backend Testing

### Option 1: Run the Manual Test Script (Recommended)

The test script (`test_structured_output_manual.py`) runs 3 comprehensive tests:

```bash
# 1. Start local dev infrastructure
make local-dev-infra

# 2. Run the test script
poetry run python test_structured_output_manual.py
```

**What it tests:**
1. **Default Hardcoded Prompt** - Backward compatible, no template
2. **Custom Template** - User-configurable template with financial analysis focus
3. **Hybrid Attribution** - LLM citations with post-hoc fallback

**Expected Output:**
```
🚀 Starting Manual Tests for Structured Output
Collection: NewIBM (a066f5e7-e402-44d8-acd1-7c74bb752ef7)
Query: What were IBM's key financial highlights in 2023 according to the annual report?

================================================================================
TEST 1: Default Hardcoded Prompt (No Template)
================================================================================
✅ Retrieved 5 documents from search

🔄 Generating structured output with openai provider (default prompt)...

📊 RESULTS:
Answer: Based on the IBM 2023 annual report, key financial highlights include...
Confidence: 0.92
Number of Citations: 5

Token Usage:
  - Prompt tokens: 1234
  - Completion tokens: 567
  - Total tokens: 1801

📚 Citations:

  Citation 1:
    Document ID: 550e8400-e29b-41d4-a716-446655440000
    Title: IBM Annual Report 2023
    Page: 5
    Chunk ID: chunk_12
    Relevance: 0.95
    Excerpt: Revenue increased by 12% year-over-year to $61.9 billion...

[... more citations ...]
```

### Option 2: Direct Provider Testing

If you want to test specific providers or configurations:

```python
# test_provider_direct.py
import asyncio
from uuid import UUID
from backend.rag_solution.generation.providers.factory import LLMProviderFactory
from backend.rag_solution.schemas.structured_output_schema import StructuredOutputConfig
# ... (initialize services)

# Test with specific provider
provider = LLMProviderFactory.create_provider("openai", ...)

# Test with custom config
config = StructuredOutputConfig(
    enabled=True,
    format_type="standard",
    include_reasoning=True,  # Include reasoning steps
    max_citations=10,        # More citations
    min_confidence=0.7,      # Higher confidence threshold
)

answer, usage = provider.generate_structured_output(
    user_id=USER_ID,
    prompt="Your question here",
    context_documents=docs,
    config=config
)
```

### Option 3: Unit Tests

Run existing unit tests to verify schema validation:

```bash
# Run structured output schema tests
poetry run pytest tests/unit/schemas/test_structured_output_schema.py -v

# Expected: 21 passed
```

## Frontend Testing (When Integrated)

### Prerequisites

The structured output feature is **not yet integrated** with the frontend. To make it visible in the UI, you would need to:

1. **Integrate with SearchService** (`backend/rag_solution/services/search_service.py`):
   ```python
   # Add to search() method
   if enable_structured_output:
       structured_answer, usage = self.provider.generate_structured_output(
           user_id=user_id,
           prompt=question,
           context_documents=self._build_context_documents(retrieved_docs),
           config=structured_output_config,
           template=user_template  # From database
       )
   ```

2. **Update SearchOutput schema** to include citations
3. **Create UI components** for displaying citations
4. **Add API endpoints** for structured output configuration

### Manual Frontend Testing (When Available)

Once integrated, you would test like this:

```bash
# 1. Start backend
make local-dev-backend

# 2. Start frontend
make local-dev-frontend

# 3. Open browser
open http://localhost:3000
```

**Testing Steps:**
1. Navigate to NewIBM collection (ID: a066f5e7-e402-44d8-acd1-7c74bb752ef7)
2. Enable "Structured Output" in settings
3. Ask: "What were IBM's key financial highlights in 2023?"
4. **Verify UI shows:**
   - Answer text
   - Confidence score (0.0-1.0)
   - Citations with:
     - Document title
     - Page number
     - Chunk ID
     - Excerpt
     - Relevance score
   - Click citations to highlight source in document viewer

### Browser DevTools Inspection

Check the API response format:

```javascript
// Expected response structure
{
  "answer": "IBM's 2023 financial highlights include...",
  "confidence": 0.92,
  "citations": [
    {
      "document_id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "IBM Annual Report 2023",
      "excerpt": "Revenue increased by 12%...",
      "page_number": 5,
      "chunk_id": "chunk_12",
      "relevance_score": 0.95
    }
  ],
  "format_type": "standard",
  "metadata": {
    "attribution_method": "llm_generated"  // or "post_hoc_semantic"
  }
}
```

## Testing Template Flexibility

### Create Custom Template in UI (When Available)

1. Navigate to **Settings → Prompt Templates**
2. Click **"Create New Template"**
3. Fill in:
   - **Name:** "IBM Financial Analysis"
   - **Type:** `STRUCTURED_OUTPUT`
   - **Template Format:**
     ```
     You are a financial analyst expert.

     Question: {question}

     Source Documents:
     {context}

     Provide detailed financial analysis with specific numbers and page citations.
     ```
   - **Input Variables:**
     - `question`: "The user's financial query"
     - `context`: "Retrieved financial documents"
   - **System Prompt:** "You are an expert financial analyst."
4. Save template
5. Use template in search query

### Verify Template Usage

Check that the LLM response follows your custom template structure:

- Custom instructions appear in prompt
- Response format matches template guidance
- Citations include requested metadata

## Testing Hybrid Attribution

### Scenario 1: LLM Citations Pass Validation

**Setup:**
- Set `min_confidence: 0.6` (reasonable threshold)
- Use clear, factual query

**Expected:**
- LLM generates valid citations
- `metadata.attribution_method == "llm_generated"`
- All citations reference valid document IDs

### Scenario 2: Post-Hoc Fallback Triggered

**Setup:**
- Set `min_confidence: 0.95` (very high threshold)
- Use complex or ambiguous query

**Expected:**
- LLM citations fail validation (3 attempts)
- System falls back to semantic similarity attribution
- `metadata.attribution_method == "post_hoc_semantic"`
- Citations still valid and relevant

### Verify Attribution Quality

```python
# Check citation validity
for citation in structured_answer.citations:
    assert citation.document_id in [doc['id'] for doc in context_documents]
    assert len(citation.excerpt) >= 20  # Minimum excerpt length
    assert 0.0 <= citation.relevance_score <= 1.0
    if citation.page_number:
        assert citation.page_number > 0
```

## Common Issues & Troubleshooting

### Issue: No documents retrieved

**Symptom:** `❌ No documents retrieved from search`

**Solution:**
1. Check collection exists: `COLLECTION_ID = "a066f5e7-e402-44d8-acd1-7c74bb752ef7"`
2. Verify documents are indexed in collection
3. Check search service is running
4. Try simpler query: "IBM revenue"

### Issue: Template formatting fails

**Symptom:** `Template formatting failed: ..., falling back to default`

**Solution:**
1. Verify template has required variables: `{question}`, `{context}`
2. Check template format is valid (no syntax errors)
3. Review logs for specific error
4. System will gracefully fall back to hardcoded default

### Issue: All citations have low relevance scores

**Symptom:** `relevance_score < 0.5` for all citations

**Solution:**
1. Check query matches document content
2. Try broader query
3. Verify chunk_id and page_number are in context_documents
4. Review document preprocessing/chunking strategy

### Issue: LLM doesn't populate chunk_id or page_number

**Symptom:** `citation.chunk_id == None`, `citation.page_number == None`

**Solution:**
1. Verify context_documents include these fields:
   ```python
   context_documents = [{
       "id": "...",
       "title": "...",
       "content": "...",
       "page_number": 5,      # ← Must be present
       "chunk_id": "chunk_12" # ← Must be present
   }]
   ```
2. Check provider prompts include metadata formatting
3. Review LLM response for citation structure

## Performance Benchmarks

**Expected Performance:**

| Metric | Value |
|--------|-------|
| Latency (OpenAI gpt-4o) | 2-4 seconds |
| Latency (Anthropic Claude) | 3-5 seconds |
| Latency (WatsonX) | 4-6 seconds |
| Token Usage | 1500-2500 tokens |
| Citation Count | 3-5 citations |
| Confidence Score | 0.7-0.95 |
| Success Rate (LLM) | 80-95% |
| Success Rate (Hybrid) | 95-99% |

## Next Steps

To make structured output visible in the UI, you'll need to:

1. **Integrate with SearchService**
   - Add structured output configuration to search flow
   - Extract chunk_id/page_number from QueryResults
   - Build context_documents with metadata

2. **Update API**
   - Add structured output endpoints
   - Update SearchOutput schema to include citations
   - Add template selection parameter

3. **Build Frontend Components**
   - Citation display component
   - Source highlighting
   - Confidence indicator
   - Template selector

4. **End-to-End Testing**
   - Test full flow: query → retrieval → LLM → citations → UI
   - Verify multi-page citations work correctly
   - Test template customization in UI

Would you like me to help with any of these integration steps?
