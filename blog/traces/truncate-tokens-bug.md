# The TRUNCATE_INPUT_TOKENS Bug

*One config parameter. All search results broken. Thousands of tests green.*

**PR**: [#564](https://github.com/manavgup/rag_modulo/pull/564)
**Severity**: Critical — all RAG search returned wrong results
**Time to detect**: Unknown (weeks to months)
**Time to fix**: Hours once identified

## The Bug

In `backend/vectordbs/utils/watsonx.py`, the WatsonX embedding configuration
included:

```python
TRUNCATE_INPUT_TOKENS: 3
```

This truncated every search query to **3 tokens** before generating embeddings.

## Impact

The query *"What percentage of IBM's workforce consists of women?"* (12 tokens)
was embedded as roughly *"What percentage of"*. The semantic content — IBM,
workforce, women — was destroyed.

Wrong embeddings → wrong vector similarity → wrong chunks retrieved → wrong answers.

**Comparison test** (`backend/dev_tests/manual/test_search_comparison.py`):

| Path | Query | Top result | Score |
|---|---|---|---|
| API path (with truncation) | "workforce women" | Page 96 (financial data) | 0.697 |
| Direct Milvus (no truncation) | "workforce women" | Page 30 (workforce data) | 0.800 |

The API path returned a completely unrelated page because the truncated embedding
had lost the semantic signal.

## Why It Went Undetected

**Every unit test mocked the embedding service.** The test suite had ~1,738 tests
at the time. Every one that touched search used `Mock()` for the embedding client.
No test generated real embeddings against real text. The suite was 100% green.

The bug was only found when someone manually ran `test_search_comparison.py` —
a dev test that called both the API path and the direct Milvus path with the
same query and compared the results.

## The Fix

Remove `TRUNCATE_INPUT_TOKENS` entirely. WatsonX has built-in token limits
that preserve semantic information. The parameter was a premature optimization
that destroyed the very thing it was supposed to optimize.

**Regression test added** (`tests/unit/services/test_watsonx.py`):

```python
def test_get_wx_embeddings_client_no_truncation_in_defaults(self, integration_settings):
    """Test that default embed_params does NOT include TRUNCATE_INPUT_TOKENS.

    This validates the fix for the embedding truncation bug where
    TRUNCATE_INPUT_TOKENS: 3 was destroying semantic meaning.
    """
    ...
        assert EmbedParams.TRUNCATE_INPUT_TOKENS not in params
```

The production code in `backend/vectordbs/utils/watsonx.py` also carries
a comment documenting the incident.

## Lessons

1. **If you mock your external services in every test, you can ship a bug that
   breaks core functionality and your entire suite will be green.** Integration
   tests against real embeddings are not optional for RAG systems.

2. **Configuration parameters need their own tests.** A one-line config value
   (`TRUNCATE_INPUT_TOKENS: 3`) had more impact than any 500-line feature PR.
   Test the defaults, not just the logic.

3. **Keep manual comparison tests.** `test_search_comparison.py` was the only
   thing that caught this. It compares API results against direct infrastructure
   results. This class of test doesn't fit in CI (needs real Milvus), but it's
   essential for RAG quality gates.
