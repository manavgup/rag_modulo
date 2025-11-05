# Manual Test Scripts

These scripts are used for manual testing and debugging during development.

## Embedding Tests
- `test_embedding_direct.py` - Direct embedding API tests
- `test_embedding_retrieval.py` - Retrieval path tests
- `test_search_comparison.py` - Compare search paths

## Pipeline Tests
- `test_pipeline_quick.py` - Quick pipeline validation
- `test_pipeline_simple.py` - Simple pipeline test

## Search Tests
- `test_search_no_cot.py` - Search without Chain of Thought
- `test_workforce_search.py` - Workforce data search test
- `compare_search.py` - Search comparison utility

## Configuration Tests
- `test_docling_config.py` - Docling configuration test
- `query_enhancement_demo.py` - Query enhancement demo

## Usage
Run from project root:
```bash
cd /path/to/rag_modulo
python backend/dev_tests/manual/test_embedding_direct.py
```

## Documentation
See `docs/development/manual-testing-guide.md` for comprehensive documentation of all scripts, including:
- Detailed usage instructions
- Expected outputs
- Common workflows
- Troubleshooting tips
