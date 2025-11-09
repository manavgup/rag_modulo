#!/bin/bash
# Script to create GitHub issues from RAG system review
# Run this script to create issues for all identified production gaps

set -e  # Exit on error

echo "Creating GitHub issues for RAG production gaps..."
echo ""

# Issue 1: Structured Output (HIGH PRIORITY)
echo "Creating Issue #1: Structured Output..."
gh issue create \
  --title "Implement Structured Output with JSON Schema Validation" \
  --label "enhancement,high-priority,llm-providers" \
  --assignee "@me" \
  --body "$(cat ISSUE_001_structured_output.md)"

# Issue 2: Document Summarization (HIGH PRIORITY)
echo "Creating Issue #2: Document Summarization..."
gh issue create \
  --title "Implement System-Wide Document Summarization Mode" \
  --label "enhancement,high-priority,rag-pipeline,summarization" \
  --assignee "@me" \
  --body "$(cat ISSUE_002_document_summarization.md)"

# Issue 3: Multi-turn Conversational Grounding (MEDIUM PRIORITY)
echo "Creating Issue #3: Multi-turn Conversational Grounding..."
gh issue create \
  --title "Enhance Multi-turn Conversational Grounding" \
  --label "enhancement,medium-priority,conversation" \
  --body "## Problem Statement

Current system enhances **questions** with conversation context but doesn't ground **answers** in prior assistant responses.

### Current State
✅ ConversationService (1,597 lines) with:
- Entity extraction from history
- Context-aware question enhancement
- Conversation history passed to search via \`config_metadata\`

❌ **Critical Gap: Answer Grounding**
- Previous assistant responses NOT passed to LLM during generation
- May contradict or duplicate previous answers
- No turn-level deduplication

### Solution
Pass full conversation history (including assistant responses) to LLM during generation.

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #3 for complete implementation details.

**Priority:** MEDIUM | **Effort:** 6-9 days"

# Issue 4: Function Calling / Tool Use (MEDIUM PRIORITY)
echo "Creating Issue #4: Function Calling / Tool Use..."
gh issue create \
  --title "Implement Function Calling and Tool Use with WatsonX" \
  --label "enhancement,medium-priority,llm-providers,agents" \
  --body "## Problem Statement

WatsonX API supports function calling but it's not integrated in our providers.

### WatsonX API Capabilities (CONFIRMED)
From https://ibm.github.io/watsonx-ai-python-sdk/v1.4.4/fm_model.html:
- ✅ Function calling via \`chat()\` with \`tools\` parameter
- ✅ Tool choice (mandatory invocation)
- ✅ Multi-turn conversations

### What's Missing
1. No tool registry - No central location for available tools
2. No tool schemas - No Pydantic models defining tools
3. No tool execution - No way to invoke tools and return results
4. No agent loop - No ReAct-style iterative tool use

### Use Cases Enabled
- \"Search for IBM stock price and compare to financial reports\"
- \"Calculate Q1 revenue and generate summary\"
- \"Query database and cross-reference with support tickets\"

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #4 for complete implementation details.

**Priority:** MEDIUM | **Effort:** 8-12 days"

# Issue 5: Hybrid Search (MEDIUM PRIORITY)
echo "Creating Issue #5: Hybrid Search..."
gh issue create \
  --title "Implement Hybrid Search (Semantic + Keyword BM25)" \
  --label "enhancement,medium-priority,retrieval,vector-db" \
  --body "## Problem Statement

Current system uses semantic search only. Missing keyword/BM25 for exact matches.

### Current State
- Elasticsearch index has \`text\` field (supports full-text search)
- **BUT**: Only using \`script_score\` with cosine similarity
- No BM25, no keyword boosting, no hybrid queries

### Poor Retrieval For
- Exact phrases or quotes
- Product codes, IDs, dates
- Named entities (people, companies)

### Solution
Implement Elasticsearch hybrid query combining:
1. Semantic search (vector similarity)
2. Keyword search (BM25)
3. Adaptive weight selection based on query characteristics

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #5 for complete implementation details.

**Priority:** MEDIUM | **Effort:** 5-7 days"

# Issue 6: Query Result Caching (HIGH PRIORITY)
echo "Creating Issue #6: Query Result Caching..."
gh issue create \
  --title "Implement Query Result Caching with Redis" \
  --label "enhancement,high-priority,performance,cost-optimization" \
  --body "## Problem Statement

No caching layer = redundant LLM calls, high costs, slow responses.

### Impact
- **Performance:** Redundant LLM calls for popular queries
- **Cost:** Repeated embedding generation (WatsonX API calls)
- **Latency:** Slow response times for common questions

### Solution: 3-Layer Caching
1. **Embedding Cache** - Cache embeddings to avoid API calls (24h TTL)
2. **Query Result Cache** - Semantic similarity matching (95% threshold, 1h TTL)
3. **LLM Response Cache** - Cache for identical prompts (1h TTL)

### Expected Impact
- 50% cost reduction
- 3x faster responses for cached queries
- Cache hit rate: 60%+ for common queries

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #6 for complete implementation details.

**Priority:** HIGH | **Effort:** 4-6 days"

# Issue 7: User Feedback Collection (HIGH PRIORITY)
echo "Creating Issue #7: User Feedback Collection..."
gh issue create \
  --title "Implement User Feedback Collection System" \
  --label "enhancement,high-priority,user-experience,analytics" \
  --body "## Problem Statement

No feedback system = no continuous improvement mechanism.

### What's Missing
1. No feedback table (ratings, corrections, hallucination reports)
2. No feedback API endpoints
3. No feedback-driven improvements (RLHF, hard negative mining)
4. No analytics dashboard

### Solution
1. **Database Schema:** AnswerFeedback table with ratings, corrections, issue flags
2. **API Endpoints:** Submit feedback, get analytics
3. **Feedback Learning:** Mine hard negatives, retrain embeddings, update reranker

### Use Cases
- User rates answer (thumbs up/down, 1-5 stars)
- User submits correction
- User flags hallucination
- Analytics: feedback trends, hallucination rate

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #7 for complete implementation details.

**Priority:** HIGH | **Effort:** 5-7 days"

# Issue 8: RAG-Specific Evaluation Metrics (MEDIUM PRIORITY)
echo "Creating Issue #8: RAG-Specific Evaluation Metrics..."
gh issue create \
  --title "Implement Advanced RAG Evaluation Metrics" \
  --label "enhancement,medium-priority,evaluation,quality" \
  --body "## Problem Statement

Current metrics are basic (HitRate, MRR, cosine similarity). Missing advanced RAG metrics.

### Current State
✅ Cosine similarity (relevance, coherence, faithfulness)
✅ LLM-as-Judge (basic faithfulness)
✅ HitRate, MRR

### Missing Metrics
❌ **Answer Groundedness** - Verify each claim has source
❌ **Hallucination Detection** - Identify unsupported statements
❌ **Answer Completeness** - Check all sub-questions addressed
❌ **NDCG, MAP** - Advanced ranking metrics
❌ **BERTScore** - Semantic similarity to reference
❌ **Token Efficiency** - Cost vs. quality tradeoff

### Solution
Implement comprehensive RAG metrics suite with groundedness scoring, hallucination detection, and ranking quality metrics.

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #8 for complete implementation details.

**Priority:** MEDIUM | **Effort:** 4-6 days"

# Issue 9: Distributed Tracing (HIGH PRIORITY)
echo "Creating Issue #9: Distributed Tracing..."
gh issue create \
  --title "Implement Distributed Tracing with OpenTelemetry" \
  --label "enhancement,high-priority,observability,devops" \
  --body "## Problem Statement

No distributed tracing = cannot debug production issues, no visibility into performance.

### What's Missing
- No OpenTelemetry instrumentation
- No trace context propagation
- No span creation for pipeline stages
- No LLM observability (prompts, tokens, latency)

### Impact
- Cannot identify bottlenecks (which stage is slow?)
- No request tracing across services
- Difficult to debug production issues
- No latency breakdown (embedding 20%, retrieval 30%, LLM 50%)

### Solution
Integrate OpenTelemetry with:
1. Span instrumentation for all pipeline stages
2. LLM call tracing (prompts, tokens, parameters)
3. Vector search tracing
4. Export to Jaeger/Tempo/etc.

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #9 for complete implementation details.

**Priority:** HIGH | **Effort:** 6-8 days"

# Issue 10: Cost Optimization (LOW PRIORITY)
echo "Creating Issue #10: Cost Optimization..."
gh issue create \
  --title "Implement Intelligent Cost Optimization" \
  --label "enhancement,low-priority,cost-optimization,performance" \
  --body "## Problem Statement

Missing intelligent cost optimization strategies.

### Current State
✅ Token usage tracking
✅ Basic batch processing
✅ Rate limiting

### Missing
❌ Intelligent model selection (query complexity → model size)
❌ Prompt caching (Anthropic Claude)
❌ Context compression (remove irrelevant sections)
❌ Tiered retrieval (cheap BM25 → expensive semantic)
❌ Budget management (per-user limits, alerts)

### Expected Impact
- 40% cost reduction
- Intelligent model selection saves 30%
- Prompt caching saves 90% on cached tokens

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #10 for complete implementation details.

**Priority:** LOW | **Effort:** 5-7 days"

# Issue 11: PII Detection / Data Governance (CRITICAL PRIORITY)
echo "Creating Issue #11: PII Detection / Data Governance..."
gh issue create \
  --title "Implement PII Detection and Data Governance" \
  --label "enhancement,critical-priority,security,compliance" \
  --body "## Problem Statement

**CRITICAL:** No PII protection = legal/compliance risk (GDPR, HIPAA, SOC2).

### What's Missing
1. No PII detection at ingestion (SSN, credit cards, emails, phone numbers)
2. No PII redaction/masking
3. No document-level access control
4. No chunk-level security
5. No audit logging
6. No data retention policies
7. No compliance features (GDPR right to be forgotten)

### Legal Risk
- Inadvertent PII exposure in search results
- GDPR violations (up to 4% of annual revenue)
- HIPAA violations (PHI protection)
- Cannot use for healthcare, finance, government sectors

### Solution
Multi-layer PII protection:
1. PII scanning at document ingestion
2. Automatic redaction/masking
3. Document-level access control
4. Audit logging for all data access
5. Data classification (PUBLIC, CONFIDENTIAL, RESTRICTED)

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #11 for complete implementation details.

**Priority:** CRITICAL | **Effort:** 8-10 days"

# Issue 12: Document Versioning (LOW PRIORITY)
echo "Creating Issue #12: Document Versioning..."
gh issue create \
  --title "Implement Document Versioning and Temporal Queries" \
  --label "enhancement,low-priority,versioning,compliance" \
  --body "## Problem Statement

No document versioning = cannot track changes, no temporal queries, no audit trails.

### What's Missing
1. No version tracking (no version number, no history)
2. No temporal queries (\"documents as of Dec 2023\")
3. No change tracking (no diff between versions)
4. No vector store versioning (old chunks deleted on update)
5. No audit trail (who changed what when)

### Use Cases Blocked
- Cannot answer: \"What did the policy say 6 months ago?\"
- No compliance audit trails (GDPR, SOC2 require this)
- Cannot track document evolution
- Risk of data loss on updates

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #12 for complete implementation details.

**Priority:** LOW | **Effort:** 6-8 days"

# Issue 13: Multi-Modal Query Support (LOW PRIORITY)
echo "Creating Issue #13: Multi-Modal Query Support..."
gh issue create \
  --title "Implement Multi-Modal Query Support (Vision + Text)" \
  --label "enhancement,low-priority,multi-modal,vision" \
  --body "## Problem Statement

DoclingProcessor extracts images but they're not queryable.

### Current State
✅ Image extraction from PDFs/DOCX (DoclingProcessor)
✅ Table and figure extraction

❌ No vision model integration
❌ No image-based queries
❌ No image embeddings (CLIP)
❌ No visual Q&A

### Use Cases Blocked
- Cannot ask: \"What's in this chart?\" with image upload
- Cannot search: \"Find similar diagrams to this image\"
- Cannot analyze charts, diagrams, screenshots in documents

### Solution
1. Integrate vision models (OpenAI GPT-4V, Anthropic Claude 3)
2. Add image embeddings (CLIP)
3. Multi-modal retrieval (text query → image results)
4. Image storage and serving endpoints

See \`RAG_SYSTEM_GAPS_ANALYSIS.md\` Gap #13 for complete implementation details.

**Priority:** LOW | **Effort:** 10-14 days"

echo ""
echo "✅ All issues created successfully!"
echo ""
echo "Summary:"
echo "- 6 HIGH/CRITICAL priority issues"
echo "- 5 MEDIUM priority issues"
echo "- 2 LOW priority issues"
echo ""
echo "View all issues: gh issue list --label enhancement"
