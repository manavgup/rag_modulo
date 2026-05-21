# Development and Testing Tools

This directory contains development utilities, manual test scripts, and experimental code that is NOT part of the official test suite.

## Structure

### `/manual/`
Manual test scripts for testing specific features or debugging issues:

**Chain of Thought (CoT) Testing**:
- `test_cot_comparison.py` - Compare Chain of Thought vs regular search
- `test_cot_llm_integration.py` - Test CoT with LLM provider integration
- `test_cot_manual.py` - Manual CoT testing
- `test_cot_with_documents.py` - Test CoT with document retrieval
- `test_cot_workflow.py` - Complete CoT workflow testing

**Document Processing**:
- `test_docling_config.py` - Docling configuration testing
- `test_docling_debug.py` - Debug Docling processing issues
- `test_pdf_comparison.py` - Compare PDF parsing strategies

**Embedding & Retrieval**:
- `test_embedding_direct.py` - Direct embedding API tests
- `test_embedding_models.py` - Test different WatsonX embedding models
- `test_embedding_retrieval.py` - Embedding retrieval validation
- `test_embeddings.py` - Embedding service testing
- `test_embeddings_simple.py` - Simple embedding tests

**Search & Query**:
- `test_query_enhancement_demo.py` - Query enhancement demonstration
- `test_regular_search.py` - Regular search testing
- `test_search_api_direct.py` - Direct search API testing
- `test_search_comparison.py` - Compare search implementations
- `test_search_no_cot.py` - Search without Chain of Thought
- `test_workforce_search.py` - Workforce-specific search testing

**Conversation Testing**:
- `test_conversation_api_direct.py` - Direct conversation API testing
- `test_conversation_direct_api.py` - Alternative conversation API testing
- `test_conversation_simulation.py` - Multi-turn conversation simulation
- `test_conversation_with_documents.py` - Conversations with document context
- `test_conversation_with_mock_auth.py` - Conversations with mocked auth

**Pipeline & Configuration**:
- `test_pipeline_quick.py` - Quick pipeline testing
- `test_pipeline_simple.py` - Simple pipeline validation
- `test_settings_only.py` - Settings configuration testing

**Audio & Podcasts**:
- `test_elevenlabs_api.py` - ElevenLabs API integration testing
- `test_podcast_script_generation.py` - Podcast script generation

**Debugging**:
- `debug_rag_failure.py` - Debug RAG pipeline failures
- `compare_search.py` - Compare search implementations

### `/examples/`
Example scripts demonstrating CLI and API usage:
- `/cli/` - CLI usage examples and interactive workflows

### Root Scripts
- `test_entity_extraction_demo.py` - Entity extraction demonstration

## Usage

These scripts are designed to be run manually from the backend directory:

```bash
cd backend

# Run a manual test
python dev_tests/manual/test_cot_comparison.py

# Run embedding model comparison
python dev_tests/manual/test_embedding_models.py

# Run ElevenLabs API test
python dev_tests/manual/test_elevenlabs_api.py

# Run a CLI example
python dev_tests/examples/cli/test_workflow.py

# Run entity extraction demo
python dev_tests/test_entity_extraction_demo.py
```

## Prerequisites

Before running scripts:

1. **Environment Setup**: Services running (see main README)
2. **Environment Variables**: Configured `.env` file
3. **Dependencies**: Installed via Poetry (`poetry install --with dev,test`)
4. **Test Data**: Collections and documents created as needed

## Important Notes

- These are NOT pytest tests - they are standalone scripts
- They may require specific environment variables or running services
- They are used for development, debugging, and feature exploration
- The official test suite is in the `tests/` directory
- For detailed documentation, see `docs/development/dev-test-scripts.md`

## Documentation

For comprehensive documentation including prerequisites, expected outputs, and use cases for each script, see:

📖 **[Development Test Scripts Documentation](../../docs/development/dev-test-scripts.md)**
