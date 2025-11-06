# Development Test Scripts

This document provides comprehensive documentation for all development test scripts located in `backend/dev_tests/`. These scripts are designed for manual testing, debugging, and feature exploration during development.

## Overview

The `backend/dev_tests/` directory contains standalone test scripts that are **NOT** part of the official pytest test suite. These scripts are used for:

- Manual testing of specific features
- Debugging production issues
- Performance testing and benchmarking
- Integration testing with external services
- Feature exploration and prototyping

## Directory Structure

```
backend/dev_tests/
├── README.md                           # Quick reference guide
├── manual/                             # Manual test scripts
│   ├── test_*.py                       # Individual test scripts
│   └── README.md                       # Manual tests documentation
├── examples/                           # Example scripts
│   └── cli/                            # CLI usage examples
└── test_entity_extraction_demo.py     # Entity extraction demonstration
```

## Prerequisites

Before running any test scripts, ensure you have:

1. **Environment Setup**: All required services running (see main README)
2. **Environment Variables**: Properly configured `.env` file
3. **Dependencies**: All Python dependencies installed via Poetry
4. **Data**: Test data or collections created as needed

### Quick Setup

```bash
# 1. Install dependencies
poetry install --with dev,test

# 2. Start infrastructure
make local-dev-infra

# 3. Configure environment
cp .env.example .env
# Edit .env with your credentials

# 4. Navigate to backend directory
cd backend
```

## Manual Test Scripts

All manual test scripts are located in `backend/dev_tests/manual/`. Run them from the `backend/` directory.

### Chain of Thought (CoT) Testing

#### test_cot_comparison.py
**Purpose**: Compare Chain of Thought vs regular search performance and quality.

**Prerequisites**:
- Running RAG backend
- Configured collection with documents
- Valid user credentials

**Usage**:
```bash
cd backend
python dev_tests/manual/test_cot_comparison.py
```

**Expected Output**:
- Side-by-side comparison of CoT vs non-CoT results
- Performance metrics (latency, tokens)
- Quality assessment

**Use Cases**:
- Evaluating CoT benefit for specific queries
- Performance benchmarking
- Debugging CoT reasoning steps

---

#### test_cot_llm_integration.py
**Purpose**: Test Chain of Thought integration with different LLM providers.

**Prerequisites**:
- Multiple LLM provider credentials (WatsonX, OpenAI, etc.)
- Configured pipeline with LLM settings

**Usage**:
```bash
cd backend
python dev_tests/manual/test_cot_llm_integration.py
```

**Expected Output**:
- CoT reasoning steps for each provider
- Provider-specific performance metrics
- Error handling validation

---

#### test_cot_manual.py
**Purpose**: Manual CoT testing with interactive prompts.

**Prerequisites**:
- Running backend services
- Test collection created

**Usage**:
```bash
cd backend
python dev_tests/manual/test_cot_manual.py
```

**Expected Output**:
- Interactive query input
- Step-by-step CoT reasoning
- Final synthesized answer

---

#### test_cot_with_documents.py
**Purpose**: Test CoT reasoning with specific document sets.

**Prerequisites**:
- Collection with known documents
- Document metadata available

**Usage**:
```bash
cd backend
python dev_tests/manual/test_cot_with_documents.py
```

**Expected Output**:
- CoT reasoning across multiple documents
- Document attribution
- Source citations

---

#### test_cot_workflow.py
**Purpose**: Complete end-to-end CoT workflow testing.

**Prerequisites**:
- Fully configured RAG environment
- Test collection with diverse documents

**Usage**:
```bash
cd backend
python dev_tests/manual/test_cot_workflow.py
```

**Expected Output**:
- Complete workflow execution
- Timing breakdown for each stage
- Quality metrics

---

### Document Processing

#### test_docling_config.py
**Purpose**: Test Docling document processing configuration.

**Prerequisites**:
- Docling library installed
- Sample documents (PDF, DOCX, etc.)

**Usage**:
```bash
cd backend
python dev_tests/manual/test_docling_config.py
```

**Expected Output**:
- Docling configuration validation
- Document parsing results
- Extracted text and metadata

**Use Cases**:
- Validating Docling configuration
- Testing document format support
- Debugging parsing issues

---

#### test_docling_debug.py
**Purpose**: Debug Docling document processing issues.

**Prerequisites**:
- Problem documents that failed processing
- Docling debug logs enabled

**Usage**:
```bash
cd backend
python dev_tests/manual/test_docling_debug.py
```

**Expected Output**:
- Detailed parsing logs
- Error diagnostics
- Suggested fixes

---

#### test_pdf_comparison.py
**Purpose**: Compare different PDF parsing strategies.

**Prerequisites**:
- Sample PDF documents
- Multiple parsing libraries installed

**Usage**:
```bash
cd backend
python dev_tests/manual/test_pdf_comparison.py
```

**Expected Output**:
- Parsing results from multiple libraries
- Quality comparison
- Performance metrics

---

### Embedding & Retrieval

#### test_embedding_direct.py
**Purpose**: Direct embedding API testing without RAG pipeline.

**Prerequisites**:
- Embedding service configured
- LLM provider credentials (WatsonX, OpenAI, etc.)

**Usage**:
```bash
cd backend
python dev_tests/manual/test_embedding_direct.py
```

**Expected Output**:
- Raw embedding vectors
- Embedding dimensions
- Performance metrics (latency, throughput)

**Use Cases**:
- Validating embedding model configuration
- Testing different embedding providers
- Benchmarking embedding performance

---

#### test_embedding_retrieval.py
**Purpose**: Test embedding-based document retrieval.

**Prerequisites**:
- Vector database (Milvus) running
- Collection with embedded documents
- Query examples

**Usage**:
```bash
cd backend
python dev_tests/manual/test_embedding_retrieval.py
```

**Expected Output**:
- Retrieved documents with similarity scores
- Retrieval latency
- Relevance assessment

**Use Cases**:
- Debugging retrieval quality
- Testing vector similarity thresholds
- Evaluating retrieval performance

---

#### test_embedding_models.py
**Purpose**: Test and compare different WatsonX embedding models.

**Prerequisites**:
- WatsonX API credentials
- Sample PDF document for testing
- Multiple embedding models configured

**Usage**:
```bash
cd backend
python dev_tests/manual/test_embedding_models.py
```

**Expected Output**:
- Comparison of embedding models
- Maximum supported chunk lengths
- Embedding dimensions for each model
- Recommended model selection

**Use Cases**:
- Selecting optimal embedding model
- Determining maximum chunk sizes
- Benchmarking embedding performance

---

#### test_embeddings.py / test_embeddings_simple.py
**Purpose**: Simple embedding service testing.

**Prerequisites**:
- Embedding service running
- Test text samples

**Usage**:
```bash
cd backend
python dev_tests/manual/test_embeddings.py
# or
python dev_tests/manual/test_embeddings_simple.py
```

**Expected Output**:
- Embedding vectors
- Service health check
- Basic performance metrics

---

### Search & Query

#### test_query_enhancement_demo.py
**Purpose**: Demonstrate query enhancement and rewriting.

**Prerequisites**:
- Query rewriting service configured
- LLM provider for query enhancement

**Usage**:
```bash
cd backend
python dev_tests/manual/test_query_enhancement_demo.py
```

**Expected Output**:
- Original query
- Enhanced/rewritten query
- Query expansion terms
- Improvement metrics

**Use Cases**:
- Understanding query enhancement pipeline
- Testing query rewriting strategies
- Evaluating query improvement quality

---

#### test_search_no_cot.py
**Purpose**: Test search without Chain of Thought reasoning.

**Prerequisites**:
- RAG backend running
- Test collection with documents

**Usage**:
```bash
cd backend
python dev_tests/manual/test_search_no_cot.py
```

**Expected Output**:
- Direct search results (no CoT)
- Response time
- Answer quality

**Use Cases**:
- Baseline performance measurement
- Comparing CoT vs non-CoT
- Testing fast search path

---

#### test_regular_search.py
**Purpose**: Standard RAG search testing.

**Prerequisites**:
- Fully configured RAG environment
- Test queries prepared

**Usage**:
```bash
cd backend
python dev_tests/manual/test_regular_search.py
```

**Expected Output**:
- Search results
- Retrieved documents
- Generated answer
- Performance metrics

---

#### test_search_api_direct.py / test_search_comparison.py
**Purpose**: Direct API testing and search comparison.

**Prerequisites**:
- Backend API running
- Test collections created

**Usage**:
```bash
cd backend
python dev_tests/manual/test_search_api_direct.py
# or
python dev_tests/manual/test_search_comparison.py
```

**Expected Output**:
- API response validation
- Search result comparison
- Performance benchmarks

---

#### test_workforce_search.py
**Purpose**: Test search on workforce-related documents.

**Prerequisites**:
- Workforce dataset ingested
- Domain-specific test queries

**Usage**:
```bash
cd backend
python dev_tests/manual/test_workforce_search.py
```

**Expected Output**:
- Domain-specific search results
- Answer accuracy assessment

---

### Pipeline & Configuration

#### test_pipeline_quick.py / test_pipeline_simple.py
**Purpose**: Quick pipeline configuration testing.

**Prerequisites**:
- Pipeline configured
- Basic test setup

**Usage**:
```bash
cd backend
python dev_tests/manual/test_pipeline_quick.py
# or
python dev_tests/manual/test_pipeline_simple.py
```

**Expected Output**:
- Pipeline validation
- Configuration verification
- Quick smoke test results

---

#### test_settings_only.py
**Purpose**: Test configuration settings loading and validation.

**Prerequisites**:
- `.env` file configured
- Settings module available

**Usage**:
```bash
cd backend
python dev_tests/manual/test_settings_only.py
```

**Expected Output**:
- Loaded configuration values
- Validation results
- Missing/invalid settings warnings

**Use Cases**:
- Debugging configuration issues
- Validating environment variables
- Testing settings precedence

---

### Conversation Testing

#### test_conversation_api_direct.py / test_conversation_direct_api.py
**Purpose**: Direct conversation API testing.

**Prerequisites**:
- Conversation service running
- User authentication configured

**Usage**:
```bash
cd backend
python dev_tests/manual/test_conversation_api_direct.py
```

**Expected Output**:
- Conversation creation
- Message exchange
- Context retention validation

---

#### test_conversation_simulation.py
**Purpose**: Simulate multi-turn conversation scenarios.

**Prerequisites**:
- Conversation history enabled
- Test conversation flows defined

**Usage**:
```bash
cd backend
python dev_tests/manual/test_conversation_simulation.py
```

**Expected Output**:
- Multi-turn conversation results
- Context tracking
- Conversation flow validation

---

#### test_conversation_with_documents.py
**Purpose**: Test conversations with document context.

**Prerequisites**:
- Documents ingested
- Conversation service configured

**Usage**:
```bash
cd backend
python dev_tests/manual/test_conversation_with_documents.py
```

**Expected Output**:
- Conversation with document grounding
- Source attribution
- Context-aware responses

---

#### test_conversation_with_mock_auth.py
**Purpose**: Test conversations with mocked authentication.

**Prerequisites**:
- Mock authentication configured
- Test users created

**Usage**:
```bash
cd backend
python dev_tests/manual/test_conversation_with_mock_auth.py
```

**Expected Output**:
- Authenticated conversation flow
- User-specific responses
- Permission validation

---

### Audio & Podcasts

#### test_elevenlabs_api.py
**Purpose**: Verify ElevenLabs API integration for text-to-speech.

**Prerequisites**:
- ElevenLabs API key configured
- Network access to ElevenLabs API

**Usage**:
```bash
cd backend
python dev_tests/manual/test_elevenlabs_api.py
```

**Expected Output**:
- API key validation
- Available voices list
- Connection test results

**Use Cases**:
- Validating ElevenLabs API credentials
- Testing voice availability
- Debugging TTS integration

---

#### test_podcast_script_generation.py
**Purpose**: Test AI-powered podcast script generation.

**Prerequisites**:
- LLM provider configured
- Sample documents for podcast content

**Usage**:
```bash
cd backend
python dev_tests/manual/test_podcast_script_generation.py
```

**Expected Output**:
- Generated podcast script
- Script structure (intro, body, outro)
- Voice cues and timing

---

### Debugging

#### debug_rag_failure.py
**Purpose**: Debug RAG pipeline failures and errors.

**Prerequisites**:
- RAG pipeline configured
- Failure scenario reproduced

**Usage**:
```bash
cd backend
python dev_tests/manual/debug_rag_failure.py
```

**Expected Output**:
- Detailed error traces
- Pipeline stage breakdown
- Root cause analysis
- Suggested fixes

**Use Cases**:
- Investigating production failures
- Understanding pipeline bottlenecks
- Debugging complex RAG issues

---

#### compare_search.py
**Purpose**: Compare different search implementations.

**Prerequisites**:
- Multiple search implementations available
- Test query set prepared

**Usage**:
```bash
cd backend
python dev_tests/manual/compare_search.py
```

**Expected Output**:
- Side-by-side comparison
- Performance metrics
- Quality assessment

---

## Other Test Scripts

### test_entity_extraction_demo.py
**Purpose**: Demonstrate entity extraction capabilities.

**Location**: `backend/dev_tests/test_entity_extraction_demo.py`

**Prerequisites**:
- Entity extraction service configured
- Sample documents with entities

**Usage**:
```bash
cd backend
python dev_tests/test_entity_extraction_demo.py
```

**Expected Output**:
- Extracted entities (persons, organizations, locations)
- Entity types and confidence scores
- Entity relationships

---

## Common Patterns

### Running Scripts

All scripts should be run from the `backend/` directory:

```bash
cd backend
python dev_tests/manual/<script_name>.py
```

### Environment Variables

Most scripts require environment variables to be configured. Check `.env.example` for required variables:

```bash
# Core settings
WATSONX_API_KEY=your_api_key
WATSONX_PROJECT_ID=your_project_id

# Vector database
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530

# LLM providers
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key

# Audio services
ELEVENLABS_API_KEY=your_elevenlabs_key
```

### Modifying Scripts

When modifying test scripts:

1. Keep imports at the top
2. Use type hints
3. Add docstrings
4. Follow existing patterns
5. Test before committing
6. Update documentation

### Creating New Test Scripts

To create a new test script:

```python
#!/usr/bin/env python3
"""Brief description of what this script tests."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config import get_settings

def main():
    """Main test function."""
    settings = get_settings()

    # Your test code here
    print("Running test...")

if __name__ == "__main__":
    main()
```

## Troubleshooting

### Common Issues

#### Import Errors
**Problem**: `ModuleNotFoundError: No module named 'rag_solution'`

**Solution**: Ensure you're running from the `backend/` directory and Python path is set correctly:
```bash
cd backend
python -c "import sys; print(sys.path)"
```

#### Environment Variables Not Loaded
**Problem**: Scripts can't find API keys or configuration

**Solution**: Verify `.env` file exists and is properly formatted:
```bash
cat .env | grep API_KEY
```

#### Service Connection Failures
**Problem**: Can't connect to Milvus, PostgreSQL, etc.

**Solution**: Verify services are running:
```bash
make local-dev-status
docker compose ps
```

#### Permission Errors
**Problem**: Can't read files or write outputs

**Solution**: Check file permissions:
```bash
ls -la backend/dev_tests/manual/
chmod +x backend/dev_tests/manual/test_*.py
```

## Best Practices

### When to Use Test Scripts

- **Manual Testing**: Validating features before writing pytest tests
- **Debugging**: Investigating production issues with simplified setups
- **Performance**: Benchmarking specific components
- **Integration**: Testing external service integrations
- **Exploration**: Trying new features or libraries

### When NOT to Use Test Scripts

- **CI/CD**: Use pytest tests in `tests/` directory instead
- **Automated Testing**: Write proper pytest tests with fixtures
- **Production**: Never run test scripts in production environments
- **Monitoring**: Use proper monitoring tools, not test scripts

### Script Maintenance

- **Review Quarterly**: Check if scripts are still relevant
- **Update Documentation**: Keep this guide current
- **Remove Obsolete Scripts**: Delete scripts for deprecated features
- **Keep Scripts Simple**: One purpose per script
- **Use Poetry**: Don't install additional dependencies outside Poetry

## Performance Benchmarking

### Performance Test Scripts

Several scripts include performance metrics:

- `test_cot_comparison.py` - CoT vs non-CoT performance
- `test_search_comparison.py` - Different search strategies
- `test_embedding_models.py` - Embedding model performance
- `test_pdf_comparison.py` - PDF parsing performance

### Interpreting Results

When benchmarking, consider:

1. **Warm-up**: First run may be slower (model loading, cache warming)
2. **Consistency**: Run multiple times and calculate averages
3. **Environment**: Local vs CI vs production performance differs
4. **Concurrency**: Single-threaded tests don't reflect production load

### Example Benchmark Output

```
Test: CoT vs Non-CoT Search
Query: "What was IBM's revenue in 2020?"

Non-CoT Search:
  Latency: 8.2s
  Tokens: 450
  Quality: 7/10

CoT Search:
  Latency: 22.5s
  Tokens: 1,250
  Quality: 9/10

Verdict: CoT provides 28% quality improvement at 2.7x latency cost
```

## Integration with Main Test Suite

These development test scripts complement the main pytest test suite:

| Test Type | Location | Purpose | CI/CD |
|-----------|----------|---------|-------|
| Unit Tests | `tests/unit/` | Fast, isolated tests | ✅ Always |
| Integration Tests | `tests/integration/` | Service interactions | ✅ Always |
| E2E Tests | `tests/e2e/` | Full system tests | ✅ On merge |
| Dev Tests | `backend/dev_tests/` | Manual exploration | ❌ Manual only |

## Related Documentation

- **Main README**: `README.md` - Project overview and setup
- **Testing Guide**: `docs/testing/index.md` - Comprehensive testing documentation
- **CLI Guide**: `docs/cli/index.md` - Command-line interface usage
- **Development Guide**: `docs/development/workflow.md` - Development process
- **API Documentation**: `docs/api/index.md` - API reference

## Contributing

When adding new test scripts:

1. **Choose the right location**:
   - Manual testing → `backend/dev_tests/manual/`
   - Examples → `backend/dev_tests/examples/`
   - Experiments → `experiments/` (for prototypes)

2. **Follow naming conventions**:
   - `test_<feature>_<aspect>.py` - e.g., `test_cot_comparison.py`
   - Use descriptive names
   - No spaces or special characters

3. **Document your script**:
   - Add docstring at top
   - Include prerequisites
   - Document expected output
   - Add to this documentation

4. **Keep it simple**:
   - One primary purpose per script
   - Clear, readable code
   - Minimal dependencies
   - Easy to modify

5. **Make it reproducible**:
   - Use environment variables for config
   - Include example outputs in comments
   - Document any required test data

## Getting Help

If you encounter issues with test scripts:

1. **Check this documentation** - Most common issues are covered
2. **Review script docstrings** - Scripts have inline documentation
3. **Check main documentation** - `docs/` has comprehensive guides
4. **Ask the team** - Slack/Teams channels for questions
5. **Create an issue** - GitHub issues for bugs or improvements

## Appendix

### Quick Reference

```bash
# Start infrastructure
make local-dev-infra

# Run a test script
cd backend
python dev_tests/manual/test_<name>.py

# Check services
make local-dev-status

# View logs
make local-dev-logs

# Stop services
make local-dev-stop
```

### Environment Setup Checklist

- [ ] Poetry dependencies installed
- [ ] `.env` file configured
- [ ] Infrastructure services running
- [ ] Test collections created
- [ ] LLM provider credentials valid
- [ ] Vector database accessible

### Common Commands

```bash
# Install dependencies
poetry install --with dev,test

# Format code
poetry run ruff format backend/dev_tests/

# Lint code
poetry run ruff check backend/dev_tests/

# Type check
poetry run mypy backend/dev_tests/
```

---

**Document Version**: 1.0
**Last Updated**: 2025-11-06
**Maintained By**: RAG Development Team
