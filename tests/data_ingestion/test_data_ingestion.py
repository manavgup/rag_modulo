from rag_solution.data_ingestion.chunking import get_chunking_method

def test_chunk_text():
    text = "This is a long text that needs to be chunked. It has multiple sentences and should be split into smaller chunks."
    chunking_method = get_chunking_method()
    chunks = chunking_method(text)
    assert len(chunks) > 0

    for chunk in chunks:
        assert len(chunk) > 0 