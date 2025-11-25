# Deprecation Notice: watsonx.py

## Status: LEGACY - Scheduled for Removal

The `backend/vectordbs/utils/watsonx.py` file is a **duplicate** of the modern provider implementation at `backend/rag_solution/generation/providers/watsonx.py`.

## Current Usage

This legacy file is still used by:

1. `backend/rag_solution/evaluation/llm_as_judge_evals.py` - Uses `generate_batch`, `generate_text`, `get_model`
2. `backend/rag_solution/data_ingestion/chunking.py` - Uses `get_tokenization` (deprecated function)
3. `backend/rag_solution/query_rewriting/query_rewriter.py` - Uses `generate_text`
4. `backend/tests/unit/test_settings_dependency_injection.py` - Test file

## Migration Plan

### Phase 1: Create Utility Wrappers (Recommended)

Create utility functions in the provider file that don't require user context for evaluation/utility use cases.

### Phase 2: Update Imports

Update all files to import from the provider file instead.

### Phase 3: Remove Duplicate

Delete `backend/vectordbs/utils/watsonx.py` once all imports are migrated.

## Why Keep It For Now?

These are utility functions used in:

- **Evaluation pipelines** (llm_as_judge_evals.py) - Runs outside normal request flow
- **Data ingestion** (chunking.py) - Preprocessing, no user context
- **Query rewriting** (query_rewriter.py) - Utility function

These don't have user context required by the modern LLMProviderFactory pattern.

## Recommendation

**DO NOT** remove this file until:

1. Utility wrapper functions are created in the provider
2. All imports are updated and tested
3. Evaluation and ingestion pipelines are verified to work

## Date: 2025-01-25

## Issue: Duplicate watsonx.py files identified during RAG improvements
