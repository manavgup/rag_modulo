# RAG Search Quality Testing CLI

A comprehensive command-line interface for testing and diagnosing the quality of RAG (Retrieval-Augmented Generation) search results.

## Overview

This CLI tool provides systematic testing capabilities to identify and diagnose issues in the RAG pipeline, including:
- Document processing and chunking
- Query rewriting effectiveness
- Vector retrieval accuracy
- Context formatting
- LLM answer generation
- Quality evaluation metrics

## Installation

The CLI is included with the backend package. Ensure you have the backend dependencies installed:

```bash
cd backend
poetry install
```

## Usage

### Basic Search Test

Test a single search query:

```bash
# Using the Makefile (recommended)
make search-test QUERY="What is machine learning?" COLLECTION_ID="uuid-here" USER_ID="uuid-here"

# With verbose output
make search-test QUERY="What is machine learning?" COLLECTION_ID="uuid-here" USER_ID="uuid-here" VERBOSE=true

# Save results to file
make search-test QUERY="What is machine learning?" COLLECTION_ID="uuid-here" USER_ID="uuid-here" OUTPUT=results.json

# Direct CLI usage
cd backend
python -m cli.search_test test \
    --query "What is machine learning?" \
    --collection-id "uuid-here" \
    --user-id "uuid-here" \
    --verbose
```

### Component Testing

Test individual pipeline components:

```bash
# Test query rewriting and retrieval
make search-components QUERY="What is machine learning?" COLLECTION_ID="uuid-here"

# Test with different rewriting strategy
make search-components QUERY="What is machine learning?" COLLECTION_ID="uuid-here" STRATEGY=hypothetical

# Direct CLI usage
python -m cli.search_test test-components \
    --query "What is machine learning?" \
    --collection-id "uuid-here" \
    --strategy simple
```

### Batch Testing

Run quality tests on multiple queries:

```bash
# Using default test queries
make search-batch COLLECTION_ID="uuid-here" USER_ID="uuid-here"

# Using custom queries file
make search-batch COLLECTION_ID="uuid-here" USER_ID="uuid-here" QUERIES_FILE=my_queries.json

# Save batch results
make search-batch COLLECTION_ID="uuid-here" USER_ID="uuid-here" OUTPUT=batch_results.json

# Direct CLI usage
python -m cli.search_test batch-test \
    --queries-file test_data/search_queries.json \
    --collection-id "uuid-here" \
    --user-id "uuid-here" \
    --output batch_results.json
```

## Test Query Format

Create a JSON file with test queries:

```json
{
  "test_queries": [
    {
      "query": "What is machine learning?",
      "category": "definition",
      "expected_keywords": ["algorithm", "data", "prediction"],
      "complexity": "low"
    },
    {
      "query": "How do neural networks work?",
      "category": "explanation",
      "expected_keywords": ["layers", "neurons", "weights"],
      "complexity": "high"
    }
  ]
}
```

## Output Format

### Single Query Test Output

The tool displays:
- **Generated Answer**: The RAG system's response
- **Search Metrics**: Execution time, documents retrieved, evaluation scores
- **Retrieved Documents** (verbose mode): Document details with scores
- **Pipeline Metadata** (verbose mode): Internal pipeline metrics

### Batch Test Output

The batch testing provides:
- **Summary Statistics**: Success rate, average quality score
- **Performance Metrics**: Average execution times
- **Category Breakdown**: Performance by query category
- **Failed Queries**: List of queries that failed with errors

### JSON Output

Results can be saved to JSON for further analysis:

```json
{
  "query": "What is machine learning?",
  "answer": "Machine learning is...",
  "execution_time": 2.34,
  "documents_count": 5,
  "rewritten_query": "What is machine learning AND (relevant OR important)",
  "evaluation": {
    "score": 85,
    "feedback": "Answer is comprehensive and accurate"
  },
  "documents": [...],
  "query_results": [...]
}
```

## Quality Metrics

The tool calculates several quality metrics:

1. **Answer Quality Score** (0-100%):
   - Answer existence (25%)
   - Document retrieval success (25%)
   - Keyword coverage (25%)
   - Evaluation score (25%)

2. **Retrieval Metrics**:
   - Precision (% of relevant documents)
   - Average similarity score
   - Score variance

3. **Performance Metrics**:
   - End-to-end execution time
   - Component-level timing
   - Document count

## Debugging Features

### Verbose Mode

Use `-v` or `--verbose` flag to see:
- Raw retrieved chunks with scores
- Formatted context sent to LLM
- LLM parameters used
- Detailed error messages

### Component Isolation

Test individual components to identify bottlenecks:
- Query rewriting effectiveness
- Retrieval quality
- Context formatting

### Error Diagnosis

Clear error messages help identify:
- Configuration issues
- Missing collections or pipelines
- LLM provider errors
- Database connection problems

## Examples

### Example 1: Testing Search Quality

```bash
# Test with a known collection
make search-test \
    QUERY="What are the key features of Scotia Enterprise Platforms?" \
    COLLECTION_ID="123e4567-e89b-12d3-a456-426614174000" \
    USER_ID="987fcdeb-51a2-43f1-b123-426614174000" \
    VERBOSE=true
```

### Example 2: Batch Quality Assessment

```bash
# Run comprehensive quality tests
make search-batch \
    COLLECTION_ID="123e4567-e89b-12d3-a456-426614174000" \
    USER_ID="987fcdeb-51a2-43f1-b123-426614174000" \
    OUTPUT=quality_report.json
```

### Example 3: Component Debugging

```bash
# Debug retrieval issues
make search-components \
    QUERY="cloud computing benefits" \
    COLLECTION_ID="123e4567-e89b-12d3-a456-426614174000" \
    STRATEGY=simple
```

## Troubleshooting

### Common Issues

1. **Collection not found**:
   - Verify the collection UUID is correct
   - Ensure the collection has been created and indexed

2. **No results returned**:
   - Check if documents have been ingested into the collection
   - Verify the vector store is properly initialized
   - Try different query rewriting strategies

3. **LLM errors**:
   - Verify LLM provider credentials are configured
   - Check pipeline configuration for valid LLM parameters
   - Ensure the selected model is available

4. **Database connection errors**:
   - Verify PostgreSQL is running
   - Check database connection settings in .env
   - Ensure the backend services are running

## Integration with CI/CD

Add to your CI pipeline for automated quality testing:

```yaml
# .github/workflows/search-quality.yml
- name: Run Search Quality Tests
  run: |
    make search-batch \
      COLLECTION_ID=${{ secrets.TEST_COLLECTION_ID }} \
      USER_ID=${{ secrets.TEST_USER_ID }} \
      OUTPUT=search_quality_report.json

    # Check quality threshold
    python -c "
    import json
    with open('search_quality_report.json') as f:
        results = json.load(f)
    avg_quality = sum(r['quality_score'] for r in results) / len(results)
    assert avg_quality >= 70, f'Quality score {avg_quality}% below threshold'
    "
```

## Performance Benchmarks

Target metrics for optimal search quality:

- **Retrieval precision**: >80% relevant chunks
- **Answer completeness**: >90% information coverage
- **Response time**: <5 seconds end-to-end
- **Source attribution**: >95% accurate citations
- **Quality score**: >70% average across test queries

## Contributing

To add new test capabilities:

1. Add new commands to `cli/search_test.py`
2. Add utility functions to `cli/utils.py`
3. Update test queries in `test_data/search_queries.json`
4. Add Makefile targets for easy access
5. Update this documentation

## License

See the main project LICENSE file.
