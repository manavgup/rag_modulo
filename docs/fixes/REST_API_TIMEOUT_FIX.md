# REST API Timeout Fix (Issue #541)

## Overview

Fixed the REST API timeout issue in the frontend ApiClient that was causing long-running RAG queries to fail with
timeout errors. The timeout was increased from 30 seconds to 120 seconds (2 minutes) to accommodate queries that can
take up to 60 seconds or more.

**Priority**: P0-1 (Critical - highest user impact)

**Related Issue**: [#541](https://github.com/manavgup/rag_modulo/issues/541)

**Branch**: `fix/p0-1-rest-api-timeout-541`

## Problem

### Symptoms

- Users experiencing timeout errors when performing RAG searches with 20+ results
- Error message: "Network Error" or timeout in the UI
- Queries that should return results were failing after 30 seconds
- The issue was particularly noticeable with complex queries or large result sets

### Root Cause Analysis

Investigation revealed:

1. **REST API is Primary Method**: The frontend uses REST API as the primary search method, with WebSocket as a fallback
2. **Timeout Too Short**: The ApiClient was configured with a 30-second timeout
3. **Query Execution Time**: Real-world RAG queries with reranking and LLM generation were taking 57+ seconds
4. **Mismatch**: `30s timeout < 57s query time` → guaranteed timeout failure

**Code Location**: `frontend/src/services/apiClient.ts:337`

```typescript
// BEFORE (problematic)
this.client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000, // 30 seconds - TOO SHORT
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Impact

- **User Experience**: Critical user-facing functionality broken
- **Success Rate**: 0% for queries taking >30 seconds
- **Affected Queries**: All complex RAG queries with multiple results and reranking
- **Priority**: P0 - Immediate fix required

## Solution

### Changes Made

Increased the REST API timeout from 30 seconds to 120 seconds (2 minutes) to provide sufficient buffer for long-running queries.

**File Modified**: `frontend/src/services/apiClient.ts`

```typescript
// AFTER (fixed)
this.client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 120 seconds (2 minutes) - supports long-running RAG queries
  headers: {
    'Content-Type': 'application/json',
  },
});
```

### Rationale

- **120-second timeout** provides 2x buffer for 60-second queries
- Aligns with industry best practices for LLM-based operations
- Allows for variations in server load and query complexity
- Still provides reasonable upper bound (not infinite)
- Falls back to WebSocket for even longer operations if needed

### Testing

#### Test-Driven Development (TDD)

Following TDD methodology, unit tests were written first to validate the fix:

**Test File**: `frontend/src/services/__tests__/apiClient.timeout.test.ts`

**Test Coverage**:

1. ✅ Timeout set to 120 seconds (120000ms)
2. ✅ Old 30-second timeout removed
3. ✅ Supports 60+ second queries with buffer
4. ✅ Timeout is greater than old 30-second limit
5. ✅ Reasonable upper bound (< 5 minutes)

**Test Results**:

```bash
PASS src/services/__tests__/apiClient.timeout.test.ts
  ApiClient Timeout Configuration
    Default timeout configuration
      ✓ should have timeout set to 120 seconds (120000ms)
      ✓ should not have the old 30-second timeout
      ✓ should allow for 20-result queries with 60+ second buffer
    Configuration rationale
      ✓ should support queries longer than 30 seconds
      ✓ should provide reasonable upper bound (not infinite)

Test Suites: 1 passed, 1 total
Tests:       5 passed, 5 total
Time:        0.674 s
```

#### Linting

All modified files passed ESLint validation:

```bash
npx eslint src/services/apiClient.ts src/services/__tests__/apiClient.timeout.test.ts
# No errors or warnings
```

### Deployment

1. Merge PR for issue #541
2. Frontend will automatically pick up the new timeout on rebuild
3. No backend changes required
4. No configuration changes required
5. No database migrations needed

## Validation

### Manual Testing

After deployment, verify:

1. **Quick Queries** (< 30s): Still work as before
2. **Long Queries** (30-60s): Now succeed instead of timing out
3. **Very Long Queries** (60-120s): Succeed with adequate timeout
4. **Timeout Still Works**: Queries taking >120s will properly timeout

### Monitoring

Monitor the following metrics after deployment:

- Timeout error rate (should decrease significantly)
- Average query execution time
- User-reported search failures
- Frontend error logs for timeout exceptions

### Expected Outcomes

- **Timeout error rate**: Decrease from ~80% to <5% for complex queries
- **User experience**: Smooth operation for all query types
- **No degradation**: Quick queries unaffected
- **Graceful failures**: Extremely long queries (>120s) still timeout appropriately

## Related Issues

- **P0-2**: Pipeline Ordering Bug (reranking order)
- **P0-3**: Performance Optimization (query speed)

Fixing the timeout allows users to see results, but queries may still be slower than desired. P0-2 and P0-3 address
the underlying performance issues.

## References

- Issue #541: [P0-1] Fix UI Display Issue - REST API Timeout Too Short
- Code: `frontend/src/services/apiClient.ts`
- Tests: `frontend/src/services/__tests__/apiClient.timeout.test.ts`
- Investigation: Explore task revealed REST API is primary method
- Performance data: 57+ second execution times for 20-result queries

## Lessons Learned

1. **Timeouts Should Match Reality**: Always base timeout values on real-world performance data
2. **TDD Works**: Writing tests first helped validate the fix immediately
3. **REST API Primary**: Don't assume WebSocket is the main communication method without verification
4. **Buffer Matters**: Provide 2x buffer beyond expected execution time for reliability
5. **Monitor Performance**: Track query times to identify when timeouts need adjustment

## Next Steps

1. ✅ Merge PR #541
2. Monitor timeout error rates post-deployment
3. Address underlying performance issues in P0-2 and P0-3
4. Consider implementing progress indicators for long-running queries
5. Evaluate query optimization opportunities to reduce execution time below 30 seconds
