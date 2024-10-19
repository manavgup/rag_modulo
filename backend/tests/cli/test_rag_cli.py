import pytest
import json
from unittest.mock import patch, MagicMock
from rag_solution.cli.rag_cli import load_config, main, process_non_streaming, process_streaming, print_evaluation_metrics
from rag_solution.pipeline.pipeline import Pipeline

@pytest.fixture
def sample_config():
    return {
        "vector_db": "milvus",
        "collection_name": "test_collection",
        "embedding_model": "test_model",
        "embedding_dim": 768
    }

@pytest.fixture
def sample_result():
    return {
        "original_query": "What is RAG?",
        "rewritten_query": "What is Retrieval-Augmented Generation (RAG)?",
        "retrieved_documents": [
            {"id": "doc1", "score": 0.95, "content": "RAG stands for Retrieval-Augmented Generation..."},
            {"id": "doc2", "score": 0.85, "content": "Retrieval-Augmented Generation (RAG) is a technique..."}
        ],
        "response": "RAG (Retrieval-Augmented Generation) is a technique that combines retrieval of relevant information with text generation.",
        "evaluation": {
            "relevance": 0.92,
            "coherence": 0.88,
            "factual_accuracy": 0.95
        }
    }

def test_load_config(tmp_path):
    config_file = tmp_path / "test_config.json"
    config_data = {"key": "value"}
    with open(config_file, "w") as f:
        json.dump(config_data, f)
    
    loaded_config = load_config(str(config_file))
    assert loaded_config == config_data

def test_load_config_file_not_found():
    with pytest.raises(FileNotFoundError):
        load_config("non_existent_file.json")

def test_load_config_invalid_json(tmp_path):
    config_file = tmp_path / "invalid_config.json"
    with open(config_file, "w") as f:
        f.write("invalid json")
    
    with pytest.raises(json.JSONDecodeError):
        load_config(str(config_file))

@patch("rag_solution.cli.rag_cli.Pipeline")
@patch("rag_solution.cli.rag_cli.load_config")
@patch("argparse.ArgumentParser.parse_args")
def test_main(mock_parse_args, mock_load_config, mock_pipeline, capsys, sample_config, sample_result):
    mock_parse_args.return_value = MagicMock(query="What is RAG?", config="config.json", prompt_config="prompt_config.json", stream=False, show_evaluation=True)
    mock_load_config.return_value = sample_config
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.process.return_value = sample_result
    mock_pipeline.return_value = mock_pipeline_instance

    main()

    captured = capsys.readouterr()
    assert "Original Query: What is RAG?" in captured.out
    assert "Rewritten Query: What is Retrieval-Augmented Generation (RAG)?" in captured.out
    assert "Retrieved Documents:" in captured.out
    assert "Generated Response: RAG (Retrieval-Augmented Generation) is a technique" in captured.out
    assert "Evaluation Metrics:" in captured.out

@patch("rag_solution.cli.rag_cli.Pipeline")
def test_process_non_streaming(mock_pipeline, capsys, sample_result):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.process.return_value = sample_result
    
    process_non_streaming(mock_pipeline_instance, "What is RAG?", True)

    captured = capsys.readouterr()
    assert "Original Query: What is RAG?" in captured.out
    assert "Rewritten Query: What is Retrieval-Augmented Generation (RAG)?" in captured.out
    assert "Retrieved Documents:" in captured.out
    assert "Generated Response: RAG (Retrieval-Augmented Generation) is a technique" in captured.out
    assert "Evaluation Metrics:" in captured.out

@patch("rag_solution.cli.rag_cli.Pipeline")
def test_process_streaming(mock_pipeline, capsys):
    mock_pipeline_instance = MagicMock()
    mock_pipeline_instance.process_stream.return_value = [
        {"response_chunk": "RAG "},
        {"response_chunk": "stands for "},
        {"response_chunk": "Retrieval-Augmented Generation."},
        {"retrieved_documents": [{"id": "doc1", "score": 0.95, "content": "RAG is a technique..."}]},
        {"evaluation": {"relevance": 0.92, "coherence": 0.88}}
    ]
    
    process_streaming(mock_pipeline_instance, "What is RAG?", True)

    captured = capsys.readouterr()
    assert "Streaming response:" in captured.out
    assert "RAG stands for Retrieval-Augmented Generation." in captured.out
    assert "Retrieved Documents:" in captured.out
    assert "Evaluation Metrics:" in captured.out

def test_print_evaluation_metrics(capsys):
    evaluation = {
        "relevance": 0.92,
        "coherence": 0.88,
        "factual_accuracy": 0.95,
        "detailed_metrics": {
            "precision": 0.9,
            "recall": 0.85
        }
    }
    
    print_evaluation_metrics(evaluation)

    captured = capsys.readouterr()
    assert "relevance: 0.92" in captured.out
    assert "coherence: 0.88" in captured.out
    assert "factual_accuracy: 0.95" in captured.out
    assert "detailed_metrics:" in captured.out
    assert "precision: 0.9" in captured.out
    assert "recall: 0.85" in captured.out

if __name__ == "__main__":
    pytest.main()