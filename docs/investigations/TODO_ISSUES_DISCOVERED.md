# TODO: Issues Discovered During Embedding Comparison Test

## Completed ✅

### 1. Chunking - Handle Oversized Sentences
**Status**: FIXED
**Location**: `backend/rag_solution/data_ingestion/chunking.py:192-245`
**Issue**: Sentences longer than target size (e.g., markdown tables) were added as-is, creating chunks up to 24,654 characters
**Fix**: Added logic to split oversized sentences at word boundaries before adding to chunks
**Result**: Max chunk size reduced from 24,654 chars to 596 chars (~238 tokens, well under 512 limit)

### 2. Configuration Consistency - Character vs Token Units
**Status**: FIXED
**Location**: `backend/core/config.py:69-73`, `backend/rag_solution/data_ingestion/chunking.py:371-389`
**Issue**: `sentence_chunker()` was interpreting config values as tokens and multiplying by 2.5, while other strategies used characters directly
**Fix**: Standardized ALL chunking strategies to use CHARACTERS, removed 2.5x multiplier
**Result**: Consistent behavior across all chunking strategies

### 3. Code Smells in Repository
**Status**: FIXED
**Location**: `backend/rag_solution/repository/llm_model_repository.py:69-92`
**Issue**: Using `hasattr()` for duck-typing and `dict[str, Any]` type erasure
**Fix**: Changed to only accept `LLMModelInput` Pydantic type, use `model_dump(exclude_unset=True)` properly
**Result**: Type-safe repository methods

---

## Pending 🔧

### 4. Issue #461: CoT Reasoning Leak
**Status**: NOT FIXED
**Branch**: `fix/issue-461-cot-reasoning-leak`
**Location**: Evidence in `/tmp/watsonx_prompts/prompt_20251022_132857_*.txt`
**Issue**: LLM is generating additional Q&A pairs despite clear instructions not to:
```
CRITICAL RULES - FOLLOW EXACTLY:
1. Answer ONLY the specific question provided below
2. Do NOT generate additional questions or 'Question:' / 'Answer:' pairs
```
But response contains:
- "What is the symbol for IBM stock on the NYSE?"
- "Where can one find IBM's annual report..."
- "How can one obtain the literature..."
- (10+ additional unwanted Q&A pairs)

**Impact**: Response contaminated with unwanted reasoning steps that should be filtered out
**File to Review**: `backend/rag_solution/services/user_provider_service.py` (modified on branch)

### 5. Reranker Template Validation Bug
**Status**: NOT FIXED
**Location**: `backend/rag_solution/services/search_service.py:214`
**Issue**: `prompt_service.get_by_type()` returns `None` when no reranking template exists (line 56 of prompt_template_service.py), then passes `template=None` to `LLMReranker()`, causing:
```
ValueError: Template is required for batch generation
ERROR - Error scoring batch 1: Failed to generate text: Template is required for batch generation
```

**Root Cause**:
```python
# search_service.py:214
template = prompt_service.get_by_type(user_id, PromptTemplateType.RERANKING)
# template can be None here!

# search_service.py:221-224
self._reranker = LLMReranker(
    llm_provider=llm_provider,
    user_id=user_id,
    prompt_template=template,  # ← None causes error in batch processing!
```

**Fix Needed**: Add validation after line 214:
```python
template = prompt_service.get_by_type(user_id, PromptTemplateType.RERANKING)
if template is None:
    logger.warning("No reranking template found for user, using simple reranker")
    self._reranker = SimpleReranker()
    return self._reranker
```

### 6. Excessive SQLAlchemy Logging
**Status**: ROOT CAUSE IDENTIFIED
**Location**: `backend/rag_solution/file_management/database.py:51`
**Issue**: SQLAlchemy is querying `pg_catalog.pg_class` repeatedly for every table (teams, users, llm_providers, etc.) with INFO level logging:
```
SELECT pg_catalog.pg_class.relname
FROM pg_catalog.pg_class JOIN pg_catalog.pg_namespace ...
WHERE pg_catalog.pg_class.relname = %(table_name)s ...
```

**Root Cause**:
```python
# database.py:51
engine = create_engine(_default_database_url, echo=not bool(os.environ.get("PYTEST_CURRENT_TEST")))
# echo=True enables SQL logging at INFO level, overriding logging_utils.py settings!
```

**Impact**:
- Log noise (thousands of duplicate lines)
- Overrides the `logging_utils.py` configuration that sets SQLAlchemy to CRITICAL
- Potential performance overhead from excessive logging

**Fix**: Change line 51 to `echo=False` or remove the parameter (defaults to False):
```python
engine = create_engine(_default_database_url)  # echo defaults to False
```

**Also in**:
- `database.py:65` - Same issue in `create_session_maker()`
- These override the careful logging setup in `core/logging_utils.py:71-77`

### 7. Redundant Database Query After File Upload (N+1 Pattern)
**Status**: IDENTIFIED
**Location**: `backend/rag_solution/services/file_management_service.py:47-49, 237-247`
**Issue**: After uploading a file and creating a DB record, the code queries the database again to retrieve the file path

**Flow**:
```python
# Line 35-47: upload_file() method
file_path = self._get_file_path(user_id, collection_id, file.filename)  # Compute path
# ... save file to disk ...
file_input = FileInput(...)  # Create input with file_path
self.create_file(file_input, user_id)  # INSERT into DB, then SELECT by ID
return str(file_path)  # Return locally computed path

# Later... get_file_path() is called:
# Line 237-247: get_file_path() method
file = self.get_file_by_name(collection_id, clean_filename)  # SELECT again!
return Path(file.file_path)
```

**Database Queries**:
1. `INSERT INTO files (...)` - Create record
2. `SELECT ... FROM files WHERE id = %(pk_1)s` - Refresh after INSERT (SQLAlchemy session.refresh())
3. `SELECT ... FROM files WHERE collection_id = ... AND filename = ...` - Re-fetch same data!

**Impact**:
- **2 unnecessary queries** per file upload (queries #2 and #3)
- Performance overhead on high-volume file uploads
- Classic N+1 anti-pattern

**Fix**: Return the FileOutput from `create_file()` and use it directly:
```python
# upload_file() should return FileOutput instead of str:
def upload_file(...) -> FileOutput:  # Changed return type
    ...
    file_output = self.create_file(file_input, user_id)  # Save return value
    return file_output  # Return the FileOutput with file_path

# Callers can use file_output.file_path directly instead of calling get_file_path()
```

**Alternative**: Cache the FileOutput in memory for a short period to avoid re-queries

### 8. Poor Question Generation Strategy - Only 8 Chunks of 1757 Processed
**Status**: CRITICAL ISSUE
**Location**: `backend/rag_solution/services/question_service.py:53-55, 264`
**Issue**: Question generation only processes 8 chunks out of entire document (0.45% coverage)

**Current Behavior**:
```python
# Line 53-55
self.max_chunks_to_process = getattr(settings, "max_chunks_for_questions", 8)

# Line 264
limited_texts = self._select_representative_chunks(texts, self.max_chunks_to_process)
```

**Example from logs** (1757 total chunks):
```
Selected 8 representative chunks using stratified sampling strategy
Sampled 8 representative chunks from 1757 total chunks
Generating 3 questions per chunk from 4 text chunks
```

**Problems**:
1. **Terrible document coverage**: 8 chunks / 1757 chunks = **0.45% of document**
2. **Missing critical content**: Revenue info (your test case) could easily be in the 99.5% not sampled
3. **Poor stratified sampling**: Even with stratified sampling, 8 samples from 1757 is statistically meaningless
4. **Then further reduced**: 8 chunks combined into 4 batches due to context limits

**Impact**:
- Generated questions don't represent the full document
- Critical information (like "IBM revenue in 2022") likely missed
- Retrieval quality suffers because suggested questions don't cover key topics

**Fix Options**:

**Option A - Increase sample size**:
```python
self.max_chunks_to_process = min(len(texts), 100)  # At least 100 chunks or 5% of doc
```

**Option B - Hierarchical summarization** (better):
```python
# 1. Divide document into sections (e.g., 100 chunks each)
# 2. Summarize each section
# 3. Generate questions from summaries + key chunks
# 4. Ensures full document coverage
```

**Option C - Multi-pass generation**:
```python
# 1. First pass: Extract key topics/entities from ALL chunks
# 2. Second pass: Generate questions covering identified topics
# 3. Ensures questions span entire document scope
```

**Investigation Needed**:
- Examine `_select_representative_chunks()` stratified sampling implementation in `question_service.py`
- Determine if stratification algorithm is effective with such small sample sizes (8 from 1757)
- Evaluate whether increasing sample size would make stratification more valuable
- Consider if stratification is appropriate for technical documents (financial reports, etc.)

**Evidence from logs** (stratified sampling in action):
```
Selected 8 representative chunks using stratified sampling strategy
Sampled 8 representative chunks from 1757 total chunks for better document coverage
Generating 3 questions per chunk from 4 text chunks
```

**Key Issue**: Stratified sampling might be well-implemented, but 0.45% sample size makes any sampling strategy ineffective.

### 9. Missing Variable in CoT Question Generation Template
**Status**: BUG IDENTIFIED
**Location**: `backend/rag_solution/services/question_service.py:418, 443-471`
**Issue**: CoT question generation templates expect `num_questions` variable but it's not provided

**Error from logs**:
```
WARNING - Failed to generate CoT questions with template 1: Missing required variable: 'num_questions'
WARNING - Failed to generate CoT questions with template 2: Missing required variable: 'num_questions'
WARNING - Failed to generate CoT questions with template 3: Missing required variable: 'num_questions'
Generated total 0 Chain of Thought questions
```

**Root Cause**:
```python
# Line 418: Standard questions GET the variable
standard_variables = {"num_questions": str(questions_per_chunk)}

# Line 443-471: CoT question generation MISSING the variable
# (Only passes document as context, no num_questions variable)
```

**Fix**: Add `num_questions` to CoT template variables (similar to standard questions)

**Impact**:
- All CoT questions fail to generate (0 generated)
- Only standard questions work
- Missing reasoning-focused questions that CoT provides

### 10. N+1 Query Pattern in Bulk Question Insert
**Status**: BUG IDENTIFIED
**Location**: `backend/rag_solution/repository/question_repository.py:76-80`
**Issue**: After bulk inserting questions using SQLAlchemy's `insertmanyvalues`, code loops through each question and calls `session.refresh()`, triggering individual SELECT queries

**Root Cause**:
```python
# Line 76-80
self.session.add_all(questions)  # Uses insertmanyvalues for bulk insert
self.session.commit()
for question in questions:
    self.session.refresh(question)  # ← Triggers individual SELECT query per question!
```

**Evidence from Logs** (15 questions inserted):
```
INSERT INTO questions (id, collection_id, question, ...) VALUES (?, ?, ?, ...) ... (15 rows)
SELECT questions.id, questions.collection_id, ... WHERE questions.id = ?  # Query 1
SELECT questions.id, questions.collection_id, ... WHERE questions.id = ?  # Query 2
SELECT questions.id, questions.collection_id, ... WHERE questions.id = ?  # Query 3
... (15 total SELECT queries)
```

**Impact**:
- **N additional queries** after bulk insert (where N = number of questions)
- Performance degradation on large question batches
- Classic N+1 anti-pattern
- Objects already have all data after bulk insert, so refreshes are unnecessary

**Fix Options**:

**Option A - Remove unnecessary refresh** (simplest):
```python
self.session.add_all(questions)
self.session.commit()
# Remove the refresh loop entirely - objects already have their data
return questions
```

**Option B - Batch refresh if needed** (if refresh is actually required):
```python
self.session.add_all(questions)
self.session.commit()
# Use expire_all() + single query instead of N queries
self.session.expire_all()
# Next access will trigger single query with WHERE id IN (...)
return questions
```

**Recommendation**: Option A - The refresh loop appears unnecessary since objects have all their data after insert.

### 11. Repeated Collection Queries During Collection Processing
**Status**: BUG IDENTIFIED
**Location**: Collection service/repository pattern
**Issue**: The same complex collection query with LEFT OUTER JOINs is being executed repeatedly during and after collection processing

**Evidence from Logs**:
The query pattern appears multiple times:
```sql
SELECT anon_1.collections_id, anon_1.collections_name, ..., files_1.id, files_1.user_id, ..., user_collection_1.user_id, ...
FROM (SELECT collections.id, collections.name, ... FROM collections WHERE collections.id = %(id_1)s::UUID LIMIT %(param_1)s) AS anon_1
LEFT OUTER JOIN files AS files_1 ON anon_1.collections_id = files_1.collection_id
LEFT OUTER JOIN user_collection AS user_collection_1 ON anon_1.collections_id = user_collection_1.collection_id
```

**Query Execution Timeline** (for same collection `0cde1ff6-f392-4271-9d44-c5e41bce32bd`):
1. `13:30:51.361` - After question generation completes
2. `13:30:51.365` - After COMMIT (status update to COMPLETED)
3. `13:30:51.385` - Again after status update
4. `13:30:55.722` - After batch query for chunks (4 seconds later)
5. `13:31:10.804` - On next HTTP request (15 seconds later)

**Impact**:
- Expensive query with 2 LEFT OUTER JOINs executed 5+ times for same collection
- No caching of collection object between operations
- Performance overhead during collection processing workflow
- Each query fetches files and user associations that likely haven't changed

**Root Cause**:
Collection object not being passed/cached between service calls - each operation re-fetches from database

**Fix Options**:

**Option A - Pass collection object** (preferred):
```python
# Instead of passing collection_id and re-fetching:
def process_collection(collection: Collection) -> None:
    # Use the already-loaded collection object

# Callers fetch once and pass the object
collection = collection_service.get_by_id(collection_id)
process_collection(collection)
```

**Option B - Add query result cache**:
```python
# Use @lru_cache or simple dict cache for short-lived requests
# Cache expires after operation completes
```

**Option C - Eager loading optimization**:
```python
# If re-fetching is necessary, use selectinload to optimize:
query = query.options(
    selectinload(Collection.files),
    selectinload(Collection.user_collections)
)
# This uses 3 queries total instead of N+1
```

**Recommendation**: Option A - Refactor to pass collection objects instead of IDs where the collection is already loaded.

### 12. Missing Chunk Metadata - chunk_number, document_name, page_number All Zero/Empty
**Status**: DATA QUALITY ISSUE
**Location**: Vector storage/chunk ingestion pipeline
**Issue**: Retrieved chunks have missing or incorrect metadata that prevents source attribution and document reconstruction

**Evidence from Search Logs**:
All 20 retrieved chunks show:
```python
'chunk_number': 0        # Always 0 instead of sequential numbering
'document_name': ''      # Empty instead of actual document filename
'page_number': 0         # Always 0 instead of actual page number
'document_id': '8f80671c-9622-45e9-bc2b-2555f6f8328d'  # This is present
'chunk_id': '...'        # This is present
'text': '...'            # This is present
```

**Example from logs** (search for "What was IBM revenue in 2022?"):
```
id: 461675756578967884, distance: 0.7873047590255737,
entity: {
  'chunk_number': 0,           # ← Should be sequential (0, 1, 2, ...)
  'document_name': '',          # ← Should be '2022-ibm-annual-report.txt'
  'document_id': '8f80671c-9622-45e9-bc2b-2555f6f8328d',
  'text': "IBM's consolidated financial results.",
  'chunk_id': 'c635a9ed-c782-47c4-999d-d9721003740c',
  'source': 'Source.OTHER',
  'page_number': 0             # ← Should be actual page number from PDF
}
```

**Impact**:
1. **No source attribution**: Users can't see which document the answer came from
2. **Can't reconstruct context**: Impossible to show surrounding chunks from same document
3. **Citation impossible**: Can't provide "See page X of document Y" references
4. **Poor UX**: Users don't know if answer is from their uploaded document or elsewhere
5. **Debugging difficult**: Can't trace which chunk came from which part of which document

**Related Issues**:
- GitHub Issue #442: "Restore source document names in chat responses" was supposedly FIXED in commit `5530411`
- Either the fix regressed or didn't fully address the root cause
- May be related to chunking pipeline not preserving metadata during ingestion

**Root Cause Investigation Needed**:
1. Check document ingestion/chunking pipeline - where metadata should be set
2. Verify Milvus schema has fields for chunk_number, document_name, page_number
3. Check if metadata is lost during:
   - File upload → chunking
   - Chunking → vector embedding
   - Embedding → Milvus insertion
4. Review how files are processed (especially Docling vs simple text extraction)

**Fix Strategy**:

**Phase 1 - Verify schema**:
```python
# Check Milvus collection schema includes metadata fields
# Ensure fields are not accidentally overwritten during insertion
```

**Phase 2 - Trace metadata flow**:
```python
# File upload: FileInput should include filename
# Chunking: Each chunk should preserve document_name, chunk_number
# Ingestion: Verify metadata is passed to vector DB
```

**Phase 3 - Fix data pipeline**:
```python
# Example fix in chunking:
chunks = []
for i, chunk_text in enumerate(document_chunks):
    chunks.append({
        'text': chunk_text,
        'chunk_number': i,  # ← Sequential numbering
        'document_name': file.filename,  # ← Actual filename
        'page_number': chunk_metadata.get('page', 0),  # ← From Docling
        'document_id': document_id,
        'chunk_id': str(uuid4())
    })
```

**Testing**:
After fix, verify chunks have:
- Sequential chunk_number (0, 1, 2, 3...)
- Correct document_name (e.g., "2022-ibm-annual-report.txt")
- Accurate page_number (from PDF metadata if available)

---

## Completed Tests 📋

### Embedding Model Comparison Test Results
**Status**: ✅ COMPLETED
**Goal**: Determine which embedding model provides best retrieval for "What was IBM revenue in 2022?"
**Models Tested**: 8 embedding models (IBM Slate, Granite, E5, MiniLM)

**CRITICAL FINDING**: 🚨 **Embedding model is NOT the root cause**

All 8 models performed identically:
- Revenue chunk ranked at **#14** (outside default top_k=5)
- Similarity score: **0.7069**
- 7/8 models gave correct answer (with top_k=20)
- 1/8 models (granite-107m) gave wrong answer despite same ranking

**Test Results Summary**:
| Model | Chunk Size | Rank | Score | Answer |
|-------|-----------|------|-------|--------|
| slate-125m-english-rtrvr | 750 chars | #14 | 0.7069 | ✅ |
| slate-125m-english-rtrvr-v2 | 750 chars | #14 | 0.7069 | ✅ |
| slate-30m-english-rtrvr | 750 chars | #14 | 0.7069 | ✅ |
| slate-30m-english-rtrvr-v2 | 750 chars | #14 | 0.7069 | ✅ |
| granite-107m-multilingual | 750 chars | #14 | 0.7069 | ❌ |
| granite-278m-multilingual | 750 chars | #14 | 0.7069 | ✅ |
| multilingual-e5-large | 500 chars | #14 | 0.7069 | ✅ |
| all-minilm-l6-v2 | 500 chars | #14 | 0.7069 | ✅ |

**Key Insights**:
1. **Embedding model NOT the problem**: All models rank revenue chunk at #14
2. **Root cause is deeper**: Likely chunking strategy, query processing, or semantic mismatch
3. **Increasing top_k helped**: With top_k=20, most models gave correct answers
4. **Need better retrieval strategy**: Hybrid search, query rewriting, or re-ranking required

**Detailed Results**: `/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend/embedding_model_comparison_results.json`

---

## In Progress 🔄

### 13. Poor Search Accuracy - Revenue Chunk Ranked #14 (All Embedding Models)
**Status**: CRITICAL ISSUE - ROOT CAUSE INVESTIGATION
**Priority**: 🔥 HIGHEST
**Location**: Search/retrieval pipeline
**Issue**: Question "What was IBM revenue in 2022?" ranks correct chunk at #14, outside default top_k=5

**Evidence**:
- All 8 embedding models tested rank revenue chunk at position #14
- Chunk contains: "For the year, IBM generated $60.5 billion in revenue..."
- Query: "What was IBM revenue in 2022?"
- Semantic similarity score: 0.7069 (relatively low)

**Why This Happens**:
1. **Semantic mismatch**: Query uses "revenue in 2022" but chunk says "For the year, IBM generated $60.5 billion"
   - No exact keyword match for "revenue" in that phrasing
   - "For the year" doesn't match "in 2022"

2. **Chunk size**: 750 chars (~300 tokens) may dilute signal
   - Relevant sentence buried in other context
   - Lower chunks ranked higher due to keyword density

3. **Query rewriting may hurt**: Current query rewriter adds "AND (relevant OR important OR key)"
   - Generic terms may not help with specific factual queries
   - Could be diluting the semantic signal

4. **No hybrid search**: Pure vector search without keyword/BM25 component
   - Missing exact keyword matches like "revenue" and "2022"

**Impact**:
- **Default top_k=5 misses correct answer**: Users get wrong/incomplete information
- **Poor user experience**: System appears unreliable for factual questions
- **Requires workarounds**: Only works with top_k=20 (expensive, slower)

**Investigation Plan**:

**Phase 1 - Analyze the chunks** (IMMEDIATE):
1. Read the actual chunk text at rank #14 - what does it say?
2. Compare with chunks ranked #1-13 - why are they ranked higher?
3. Look for keyword presence: does "revenue" appear in top-ranked chunks?
4. Check if rank #14 chunk has too much diluting context

**Phase 2 - Test fixes** (NEXT):
1. **Hybrid search**: Combine vector + BM25 keyword search
2. **Better query rewriting**: Remove generic terms, focus on key entities
3. **Smaller chunks**: Test 300-400 char chunks for better signal
4. **Reranking**: Fix Issue #5 (reranker template bug) and test LLM reranking

**Fix Options**:

**Option A - Hybrid Search** (RECOMMENDED):
```python
# Combine vector search + BM25 keyword search
# Example: 70% vector weight + 30% keyword weight
# Should boost chunks with exact "revenue" and "2022" matches
```

**Option B - Improve Query Rewriting**:
```python
# Remove generic expansion: "AND (relevant OR important OR key)"
# Extract entities: "IBM", "revenue", "2022"
# Expand with synonyms: "revenue" → "earnings", "sales"
```

**Option C - Reduce Chunk Size**:
```python
# Current: 750 chars (~300 tokens)
# Test: 400 chars (~160 tokens) - less dilution
# May improve signal-to-noise ratio
```

**Option D - Fix Reranker** (Issue #5):
```python
# LLM-based reranking can read all 20 chunks
# Identify most relevant to specific question
# Reorder before sending to generation
```

**Next Steps**:
1. Examine chunks ranked #1-14 to understand ranking
2. Test hybrid search implementation
3. Fix reranker template bug (Issue #5)
4. Experiment with chunk sizes

---

## Notes

- All chunking fixes allow embedding comparison test to proceed without token limit errors
- Test revealed embedding model is NOT the bottleneck - all perform identically
- Need to focus on retrieval strategy (hybrid search, reranking, query processing)
- CoT reasoning leak (#461) is separate - affects response quality not retrieval
