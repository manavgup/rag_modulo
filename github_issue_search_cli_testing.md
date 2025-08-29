# 🔍 Create CLI-based Search Quality Testing Framework

## 📋 Summary
Develop a comprehensive CLI-based testing framework to diagnose and improve the quality of our RAG search results. Currently, search results are suboptimal, and we need systematic testing to identify issues in document processing, chunking, query rewriting, retrieval, and answer generation.

## 🎯 Problem Statement

### Current Issues
- **Suboptimal search results** reported during recent testing
- **No systematic way** to test search quality without the full web interface
- **Multiple potential failure points** in the RAG pipeline:
  - Document ingestion and chunking strategy
  - Query rewriting effectiveness  
  - Vector retrieval accuracy
  - Context formatting and LLM generation
  - Evaluation metrics accuracy

### Why CLI Testing is Critical
- **Faster iteration** - Test changes without UI dependencies
- **Detailed debugging** - Access to internal pipeline metrics
- **Automated quality assurance** - Scriptable for CI/CD integration
- **Component isolation** - Test each RAG stage independently

## 🔬 Current RAG Pipeline Analysis

Based on codebase analysis, our RAG pipeline consists of:

### 1. **Search Entry Point**
```python
# SearchService.search() -> PipelineService.execute_pipeline()
- Input: SearchInput(question, collection_id, pipeline_id, user_id)
- Output: SearchOutput(answer, documents, query_results, rewritten_query, evaluation)
```

### 2. **Pipeline Execution Flow**
```python
# PipelineService.execute_pipeline() sequence:
1. _validate_configuration() - Check pipeline config and LLM parameters
2. _get_templates() - Retrieve RAG and evaluation prompt templates  
3. _prepare_query() - Clean input query
4. query_rewriter.rewrite() - Apply query rewriting strategies
5. _retrieve_documents() - Vector/hybrid retrieval from Milvus
6. _format_context() - Format retrieved chunks for LLM
7. _generate_answer() - LLM generation with context
8. _evaluate_response() - Quality evaluation of generated answer
```

### 3. **Key Components to Test**

#### **Query Rewriting** (`query_rewriting/query_rewriter.py`)
- `SimpleQueryRewriter`: Adds "AND (relevant OR important OR key)"
- `HypotheticalDocumentEmbedding`: Uses WatsonX for query expansion
- **Potential Issues**: Over-expansion, irrelevant terms

#### **Document Retrieval** (`retrieval/retriever.py`)
- `VectorRetriever`: Pure semantic search
- `KeywordRetriever`: BM25-based search  
- `HybridRetriever`: Combines both with configurable weights
- **Potential Issues**: Poor embedding quality, wrong retrieval strategy

#### **Document Processing** (`data_ingestion/ingestion.py`)
- Chunking strategy and overlap settings
- Metadata extraction and storage
- **Potential Issues**: Poor chunking boundaries, lost context

#### **Answer Generation** 
- Context formatting from retrieved chunks
- LLM prompt template effectiveness
- **Potential Issues**: Poor context, ineffective prompts

## ✅ Proposed CLI Testing Framework

### 1. **Create CLI Search Command**

```python
# backend/cli/search_test.py
import asyncio
import click
import json
from uuid import UUID
from sqlalchemy.orm import Session
from rag_solution.services.search_service import SearchService
from rag_solution.schemas.search_schema import SearchInput
from rag_solution.file_management.database import get_db

@click.group()
def search():
    """RAG search testing commands."""
    pass

@search.command()
@click.option('--query', '-q', required=True, help='Search query to test')
@click.option('--collection-id', '-c', required=True, help='Collection UUID')
@click.option('--pipeline-id', '-p', required=True, help='Pipeline UUID') 
@click.option('--user-id', '-u', required=True, help='User UUID')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed pipeline metrics')
@click.option('--output', '-o', type=click.Path(), help='Save results to JSON file')
async def test(query, collection_id, pipeline_id, user_id, verbose, output):
    """Test search query and analyze results."""
    # Implementation details...
```

### 2. **Pipeline Component Testing**

```python
@search.command()
@click.option('--query', '-q', required=True)
@click.option('--collection-id', '-c', required=True)
def test_components(query, collection_id):
    """Test individual pipeline components."""
    
    # Test 1: Query Rewriting
    print("🔄 Testing Query Rewriting...")
    rewriter = QueryRewriter({})
    rewritten = rewriter.rewrite(query)
    print(f"Original: {query}")
    print(f"Rewritten: {rewritten}")
    
    # Test 2: Document Retrieval
    print("\n📚 Testing Document Retrieval...")
    # Retrieval testing logic...
    
    # Test 3: Context Formatting
    print("\n📝 Testing Context Formatting...")
    # Context testing logic...
```

### 3. **Quality Metrics Collection**

```python
@search.command() 
@click.option('--queries-file', '-f', required=True, help='JSON file with test queries')
@click.option('--collection-id', '-c', required=True)
def batch_test(queries_file, collection_id):
    """Run batch testing with quality metrics."""
    
    # Load test queries with expected answers
    with open(queries_file) as f:
        test_cases = json.load(f)
    
    results = []
    for case in test_cases:
        result = await test_single_query(case)
        results.append({
            'query': case['query'],
            'expected': case.get('expected_answer'),
            'actual': result.answer,
            'retrieval_score': calculate_retrieval_score(result),
            'answer_quality': evaluate_answer_quality(result),
            'execution_time': result.metadata['execution_time'],
            'chunks_retrieved': result.metadata['num_chunks']
        })
    
    # Generate quality report
    generate_quality_report(results)
```

### 4. **Makefile Integration**

```makefile
# Add to Makefile
## RAG Search Testing
search-test:
	@echo "$(CYAN)🔍 Testing RAG search functionality...$(NC)"
	cd backend && python -m cli.search_test test \
		--query "What is machine learning?" \
		--collection-id "$(COLLECTION_ID)" \
		--pipeline-id "$(PIPELINE_ID)" \
		--user-id "$(USER_ID)" \
		--verbose
	@echo "$(GREEN)✅ Search test completed$(NC)"

search-batch:
	@echo "$(CYAN)📊 Running batch search quality tests...$(NC)"
	cd backend && python -m cli.search_test batch-test \
		--queries-file ./test_data/search_queries.json \
		--collection-id "$(COLLECTION_ID)"
	@echo "$(GREEN)✅ Batch testing completed$(NC)"

search-components:
	@echo "$(CYAN)🔧 Testing individual RAG components...$(NC)"
	cd backend && python -m cli.search_test test-components \
		--query "What is machine learning?" \
		--collection-id "$(COLLECTION_ID)"
	@echo "$(GREEN)✅ Component testing completed$(NC)"
```

## 🎯 Success Criteria

### Functional Requirements
- [ ] ✅ **CLI command** successfully executes end-to-end search
- [ ] 📊 **Detailed metrics** for each pipeline stage (timing, scores, chunks)
- [ ] 🔍 **Component isolation** testing (query rewriting, retrieval, generation)
- [ ] 📋 **Batch testing** with multiple queries and quality scoring
- [ ] 💾 **Result persistence** to JSON for analysis and comparison
- [ ] 🚀 **Makefile integration** for easy execution

### Quality Diagnostics  
- [ ] 📈 **Retrieval quality metrics**:
  - Number of relevant chunks retrieved
  - Average similarity scores
  - Document coverage (unique docs vs total chunks)
- [ ] 🎯 **Query rewriting effectiveness**:
  - Before/after query comparison
  - Impact on retrieval results
- [ ] 💬 **Answer generation quality**:
  - Response completeness and accuracy
  - Source attribution quality
  - Evaluation scores from built-in evaluator
- [ ] ⏱️ **Performance metrics**:
  - End-to-end execution time
  - Component-level timing breakdown
  - Resource usage indicators

### Debugging Capabilities
- [ ] 🔍 **Verbose mode** showing:
  - Raw retrieved chunks with scores
  - Formatted context sent to LLM
  - LLM parameters and template used
  - Evaluation criteria and scores
- [ ] 📊 **Comparison mode** between:
  - Different query rewriting strategies
  - Different retrieval methods (vector vs hybrid)
  - Different LLM parameters
- [ ] 📝 **Error diagnosis**:
  - Clear error messages for each failure point
  - Suggestions for configuration improvements
  - Pipeline health checks

## 🛠️ Implementation Plan

### Phase 1: Core CLI Framework (Week 1)
1. **Create CLI module structure**
   ```
   backend/cli/
   ├── __init__.py
   ├── search_test.py  # Main search testing commands
   └── utils.py        # Helper functions and metrics
   ```

2. **Implement basic search command**
   - Single query testing with full pipeline execution
   - JSON output format with all metrics
   - Makefile integration

3. **Add component testing**
   - Query rewriter testing
   - Document retrieval testing  
   - Context formatting verification

### Phase 2: Quality Metrics (Week 2)
1. **Develop quality scoring algorithms**
   - Retrieval relevance scoring
   - Answer completeness metrics
   - Source attribution accuracy

2. **Implement batch testing**
   - JSON test case format
   - Parallel execution for performance
   - Statistical quality reporting

3. **Add comparison capabilities**
   - A/B testing between configurations
   - Historical performance tracking

### Phase 3: Advanced Diagnostics (Week 3)
1. **Enhanced debugging features**
   - Pipeline visualization
   - Interactive component testing
   - Configuration recommendations

2. **Integration with existing test suite**
   - Pytest integration for automated testing
   - CI/CD pipeline quality gates
   - Performance regression detection

## 📊 Expected Quality Improvements

### Immediate Benefits
- **Systematic diagnosis** of current search quality issues
- **Faster iteration** on RAG parameter tuning
- **Clear performance baselines** for future improvements

### Long-term Impact
- **Automated quality assurance** preventing search quality regressions
- **Data-driven optimization** of chunking, retrieval, and generation
- **Comprehensive testing** before deploying RAG improvements

## 🔗 Test Data Requirements

### Sample Query Collections
```json
{
  "test_queries": [
    {
      "query": "What is machine learning?",
      "category": "definition",
      "expected_docs": ["intro_to_ml.pdf"],
      "expected_keywords": ["algorithm", "data", "prediction"]
    },
    {
      "query": "How do neural networks work?", 
      "category": "explanation",
      "expected_docs": ["deep_learning.pdf"],
      "complexity": "high"
    }
  ]
}
```

### Quality Benchmarks
- **Retrieval precision**: Target >80% relevant chunks
- **Answer completeness**: Target >90% information coverage
- **Response time**: Target <5 seconds end-to-end
- **Source attribution**: Target >95% accurate citations

## 📋 Acceptance Criteria
- [ ] CLI commands execute without errors in containerized environment
- [ ] Detailed search quality metrics are captured and displayed
- [ ] Component-level testing isolates specific pipeline issues
- [ ] Batch testing processes multiple queries with quality scoring
- [ ] Results are exportable to JSON for further analysis
- [ ] Makefile targets integrate seamlessly with existing workflow
- [ ] Documentation includes usage examples and interpretation guide
- [ ] Initial quality baseline is established with current search performance

## 🏷️ Labels
- `enhancement`
- `search-quality`  
- `cli-tools`
- `rag-pipeline`
- `testing`