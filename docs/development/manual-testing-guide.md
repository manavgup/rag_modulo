# Manual Testing Guide

**Last Updated**: 2025-11-05
**Purpose**: Guide for using manual test scripts in `backend/dev_tests/manual/`

---

## Overview

The `backend/dev_tests/manual/` directory contains debugging and validation scripts used during development. These scripts are **not** part of the automated CI/CD pipeline but are valuable for:

- **Debugging production issues** - Reproduce and investigate bugs
- **Performance testing** - Measure and compare component performance
- **Integration validation** - Test end-to-end workflows manually
- **Feature development** - Quick iteration during development

---

## Prerequisites

```bash
# Ensure you're in the project root
cd /path/to/rag_modulo

# Activate virtual environment
poetry shell

# Ensure all dependencies installed
poetry install --with dev,test

# Ensure infrastructure running
make local-dev-infra  # Start Postgres, Milvus, MinIO, MLFlow
```

---

## Test Scripts Reference

### Embedding Tests

#### `test_embedding_direct.py`
**Purpose**: Test embedding generation directly via WatsonX API

**Use Case**: Debug embedding generation issues, verify API connectivity

**Usage**:
```bash
python backend/dev_tests/manual/test_embedding_direct.py
```

**What it tests**:
- Direct WatsonX embedding API calls
- Embedding vector dimensions
- Token handling and truncation
- API error handling

**Expected Output**:
```
✓ Connected to WatsonX API
✓ Generated embedding: [768 dimensions]
✓ Embedding vector: [-0.012, 0.045, -0.089, ...]
```

**When to use**:
- WatsonX API connectivity issues
- Embedding dimension mismatches
- Token truncation debugging

---

#### `test_embedding_retrieval.py`
**Purpose**: Test embedding generation through RAG retrieval pipeline

**Use Case**: Debug end-to-end embedding → retrieval flow

**Usage**:
```bash
python backend/dev_tests/manual/test_embedding_retrieval.py
```

**What it tests**:
- Embedding generation in retrieval context
- Vector database query execution
- Similarity score calculation
- Chunk metadata retrieval

**Expected Output**:
```
✓ Query embedded: "What is IBM Watson?"
✓ Retrieved 10 chunks
✓ Top chunk: score=0.842, page=30, text="IBM Watson is..."
```

**When to use**:
- Retrieval accuracy issues
- Similarity score debugging
- Vector database connectivity issues

---

#### `test_search_comparison.py`
**Purpose**: Compare search results between different code paths (API vs. direct)

**Use Case**: Validate embedding consistency across different execution paths

**Critical for**: Debugging RAG accuracy issues (like the TRUNCATE_INPUT_TOKENS bug)

**Usage**:
```bash
python backend/dev_tests/manual/test_search_comparison.py
```

**What it tests**:
- API path: Frontend → Backend API → Search
- Direct path: Direct service invocation
- Embedding vector consistency
- Retrieved chunk consistency

**Expected Output**:
```
API Path Results:
  Top chunk: page=30, score=0.800, text="..."
  Embedding: [0.012, -0.045, ...]

Direct Path Results:
  Top chunk: page=30, score=0.800, text="..."
  Embedding: [0.012, -0.045, ...]

✓ CONSISTENT: Both paths retrieve same chunks
✓ CONSISTENT: Embedding vectors match
```

**When to use**:
- Investigate search result inconsistencies
- Validate embedding bug fixes
- Compare API vs. service layer behavior

---

### Pipeline Tests

#### `test_pipeline_quick.py`
**Purpose**: Quick validation of RAG pipeline stages

**Use Case**: Rapid testing during pipeline development

**Usage**:
```bash
python backend/dev_tests/manual/test_pipeline_quick.py
```

**What it tests**:
- Query enhancement stage
- Retrieval stage
- Reranking stage
- Generation stage

**Expected Output**:
```
Stage 1: Query Enhancement
  Original: "What is Watson?"
  Enhanced: "What is IBM Watson? What are Watson's key capabilities?"

Stage 2: Retrieval
  Retrieved: 10 chunks

Stage 3: Reranking
  Reranked: 5 chunks (cross-encoder scores)

Stage 4: Generation
  Answer: "IBM Watson is a suite of AI tools..."

✓ Pipeline completed in 2.3 seconds
```

**When to use**:
- Pipeline stage debugging
- Performance profiling
- Integration testing during development

---

#### `test_pipeline_simple.py`
**Purpose**: Minimal pipeline test with mock data

**Use Case**: Isolate pipeline logic without external dependencies

**Usage**:
```bash
python backend/dev_tests/manual/test_pipeline_simple.py
```

**What it tests**:
- Pipeline orchestration logic
- Stage transitions
- Error handling
- Mock data processing

**When to use**:
- Unit-level pipeline testing
- Isolate pipeline bugs from service layer
- Fast iteration during development

---

### Search Tests

#### `test_search_no_cot.py`
**Purpose**: Test search without Chain of Thought reasoning

**Use Case**: Baseline search performance measurement

**Usage**:
```bash
python backend/dev_tests/manual/test_search_no_cot.py
```

**What it tests**:
- Basic search flow (no CoT)
- Standard RAG pipeline execution
- Baseline answer quality
- Performance without reasoning overhead

**Expected Output**:
```
Query: "What percentage of IBM's workforce consists of women?"
Answer: "30% of IBM's workforce consists of women."
Sources: [Page 30, Page 45]
Time: 1.2 seconds
```

**When to use**:
- Compare performance with/without CoT
- Baseline answer quality metrics
- Simple search debugging

---

#### `test_workforce_search.py`
**Purpose**: Test search on specific workforce demographics query

**Use Case**: Reproduce the embedding bug (workforce query returning financial data)

**Usage**:
```bash
python backend/dev_tests/manual/test_workforce_search.py
```

**What it tests**:
- Specific query: "What percentage of IBM's workforce consists of women?"
- Expected: Page 30 (workforce data)
- Previously broken: Page 96 (financial data)

**Expected Output**:
```
Query: "What percentage of IBM's workforce consists of women?"
Top Chunk:
  Page: 30
  Score: 0.800
  Text: "Women make up 30% of IBM's workforce..."
  Source: IBM Annual Report 2023

✓ CORRECT: Retrieved workforce data (not financial data)
```

**When to use**:
- Validate embedding bug fix (TRUNCATE_INPUT_TOKENS)
- Regression testing for RAG accuracy
- Benchmark for correct retrieval behavior

---

### Configuration Tests

#### `test_docling_config.py`
**Purpose**: Test Docling document processor configuration

**Use Case**: Debug document processing issues

**Usage**:
```bash
python backend/dev_tests/manual/test_docling_config.py
```

**What it tests**:
- Docling configuration loading
- Document type detection
- Processing pipeline setup
- Tokenizer initialization

**Expected Output**:
```
✓ Docling config loaded
✓ Supported formats: PDF, DOCX, HTML, MD
✓ Tokenizer: intfloat/e5-large-v2
✓ Max tokens: 512 (with safety margin)
```

**When to use**:
- Document processing failures
- Tokenizer configuration issues
- Format detection problems

---

#### `test_query_enhancement_demo.py`
**Purpose**: Demonstrate query enhancement capabilities

**Use Case**: Show query rewriting and expansion features

**Usage**:
```bash
python backend/dev_tests/manual/test_query_enhancement_demo.py
```

**What it tests**:
- Query rewriting strategies
- Semantic expansion
- Context-aware enhancement
- Multiple query variations

**Expected Output**:
```
Original Query: "Watson AI"

Enhanced Queries:
1. "What is IBM Watson AI?"
2. "What are Watson's AI capabilities?"
3. "How does Watson artificial intelligence work?"
4. "IBM Watson AI features and benefits"

Context-Aware (with conversation history):
1. "Tell me more about Watson AI capabilities"
2. "What Watson AI features were discussed earlier?"
```

**When to use**:
- Demo query enhancement to stakeholders
- Debug query rewriting logic
- Validate enhancement quality

---

### Utility Scripts

#### `compare_search.py`
**Purpose**: Utility for comparing multiple search results

**Use Case**: A/B testing different search configurations

**Usage**:
```bash
python backend/dev_tests/manual/compare_search.py \
    --query "What is Watson?" \
    --config-a baseline.json \
    --config-b optimized.json
```

**What it tests**:
- Side-by-side search comparison
- Configuration impact analysis
- Answer quality differences
- Performance differences

**Expected Output**:
```
Configuration A (baseline.json):
  Answer: "IBM Watson is..."
  Sources: 3 documents
  Time: 2.1 seconds
  Relevance: 0.82

Configuration B (optimized.json):
  Answer: "IBM Watson is a comprehensive AI platform..."
  Sources: 5 documents
  Time: 1.8 seconds
  Relevance: 0.91

Winner: Configuration B (higher relevance, faster)
```

**When to use**:
- A/B testing search configurations
- Optimize search parameters
- Validate performance improvements

---

## Common Workflows

### 1. Debugging Embedding Issues

```bash
# Step 1: Test direct embedding generation
python backend/dev_tests/manual/test_embedding_direct.py

# Step 2: Test embedding in retrieval context
python backend/dev_tests/manual/test_embedding_retrieval.py

# Step 3: Compare API vs. direct paths
python backend/dev_tests/manual/test_search_comparison.py
```

### 2. Validating Search Accuracy

```bash
# Step 1: Test baseline search (no CoT)
python backend/dev_tests/manual/test_search_no_cot.py

# Step 2: Test specific problematic query
python backend/dev_tests/manual/test_workforce_search.py

# Step 3: Compare multiple configurations
python backend/dev_tests/manual/compare_search.py \
    --query "workforce demographics" \
    --config-a before_fix.json \
    --config-b after_fix.json
```

### 3. Pipeline Development Iteration

```bash
# Quick validation during development
python backend/dev_tests/manual/test_pipeline_quick.py

# Full pipeline test
python backend/dev_tests/manual/test_pipeline_simple.py
```

### 4. Regression Testing After Bug Fix

```bash
# Example: After fixing embedding truncation bug

# 1. Verify embedding consistency
python backend/dev_tests/manual/test_search_comparison.py

# 2. Verify correct chunk retrieval
python backend/dev_tests/manual/test_workforce_search.py

# 3. Compare before/after performance
python backend/dev_tests/manual/compare_search.py \
    --config-a with_truncation.json \
    --config-b without_truncation.json
```

---

## Environment Variables

Some scripts require environment variables:

```bash
# WatsonX API (for embedding tests)
export WATSONX_URL="https://..."
export WATSONX_APIKEY="..."
export WATSONX_PROJECT_ID="..."

# Database (for retrieval tests)
export COLLECTIONDB_HOST="localhost"
export COLLECTIONDB_PORT="5432"
export COLLECTIONDB_NAME="rag_modulo"
export COLLECTIONDB_USER="..."
export COLLECTIONDB_PASS="..."

# Vector Database (for search tests)
export MILVUS_HOST="localhost"
export MILVUS_PORT="19530"
```

**Pro Tip**: Use `.env` file in project root (already loaded by `python-dotenv`)

---

## Troubleshooting

### Script fails with "ModuleNotFoundError"

**Cause**: Virtual environment not activated or dependencies not installed

**Fix**:
```bash
poetry shell
poetry install --with dev,test
```

### Script fails with "Connection refused"

**Cause**: Infrastructure not running (Postgres, Milvus, etc.)

**Fix**:
```bash
make local-dev-infra      # Start infrastructure
make local-dev-status     # Check status
```

### Embedding tests fail with "401 Unauthorized"

**Cause**: WatsonX API credentials not configured

**Fix**:
```bash
# Add to .env file
WATSONX_APIKEY=your_api_key_here
WATSONX_PROJECT_ID=your_project_id_here
```

### Search tests return no results

**Cause**: Vector database empty or collection not created

**Fix**:
```bash
# Ingest test documents first
./rag-cli collection create test_collection
./rag-cli document ingest test_collection /path/to/docs/
```

---

## Adding New Test Scripts

### Template for New Script

```python
#!/usr/bin/env python3
"""
Short description of what this script tests.

Usage:
    python backend/dev_tests/manual/test_my_feature.py

Purpose:
    - What problem does this solve?
    - When should developers use this?
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from core.config import get_settings
from backend.rag_solution.services.my_service import MyService

def main():
    """Main test logic."""
    print("Testing my feature...")

    # Setup
    settings = get_settings()
    service = MyService(settings)

    # Test logic
    result = service.do_something()

    # Validation
    assert result is not None, "Result should not be None"
    print(f"✓ Test passed: {result}")

if __name__ == "__main__":
    main()
```

### Checklist for New Scripts

- [ ] Add docstring explaining purpose and usage
- [ ] Include clear print statements for output
- [ ] Add assertions for validation
- [ ] Handle errors gracefully
- [ ] Document in `backend/dev_tests/manual/README.md`
- [ ] Document in `docs/development/manual-testing-guide.md` (this file)

---

## Best Practices

### 1. Clear Output

**Good**:
```python
print("✓ Embedding generated: 768 dimensions")
print(f"  Vector: {embedding[:5]}...")
print(f"  Took: {elapsed:.2f} seconds")
```

**Bad**:
```python
print(embedding)  # Dumps huge array to console
```

### 2. Error Handling

**Good**:
```python
try:
    result = api_call()
except APIError as e:
    print(f"✗ API call failed: {e}")
    sys.exit(1)
```

**Bad**:
```python
result = api_call()  # Crashes on error
```

### 3. Validation

**Good**:
```python
assert len(results) > 0, "Expected at least 1 result"
assert results[0].score > 0.7, f"Score too low: {results[0].score}"
print("✓ All validations passed")
```

**Bad**:
```python
# No validation, just print results
```

### 4. Documentation

**Good**:
```python
"""
Test embedding consistency across API and direct paths.

This script reproduces the TRUNCATE_INPUT_TOKENS bug by comparing
embeddings generated via the API (which had truncation) vs. direct
service calls (which didn't have truncation).

Expected: Both paths should generate identical embeddings.
"""
```

**Bad**:
```python
# Test embeddings
```

---

## Integration with Automated Tests

Manual tests complement automated tests:

| Test Type | Purpose | When to Run |
|-----------|---------|-------------|
| **Unit Tests** | Test individual functions | Every commit (CI/CD) |
| **Integration Tests** | Test service interactions | Every PR (CI/CD) |
| **Manual Tests** | Debug, explore, validate | During development |
| **E2E Tests** | Test full workflows | Before release |

**Manual tests are NOT a replacement for automated tests.**

Use manual tests to:
- Investigate bugs quickly
- Prototype new features
- Validate fixes before writing formal tests
- Performance profiling

Then convert findings into proper automated tests.

---

## Related Documentation

- **Testing Strategy**: `docs/testing/index.md`
- **Development Workflow**: `docs/development/workflow.md`
- **RAG Pipeline**: `docs/architecture/rag-pipeline.md`
- **Embedding System**: `docs/architecture/embeddings.md`

---

**Last Updated**: 2025-11-05
**Maintainer**: Development Team
**Questions**: See `docs/development/contributing.md` for how to get help
