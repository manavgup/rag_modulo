"""
DEPRECATED: This module is deprecated and will be removed in a future version.
A new CLI tool using the service layer architecture will be created to replace
this standalone utility. This module currently uses file-based configuration
(prompt_config.json) instead of the database-driven approach used by the main
application.
"""

import warnings

warnings.warn(
    "The rag_cli.py module is deprecated and will be removed in a future version. "
    "A new CLI tool using the service layer architecture will replace this utility.",
    DeprecationWarning,
    stacklevel=2
)

import argparse
import json
from typing import Dict, Any
from rag_solution.pipeline.pipeline import Pipeline
from core.config import settings

def load_config(config_path: str) -> Dict[str, Any]:
    with open(config_path, 'r') as f:
        return json.load(f)

def main():
    parser = argparse.ArgumentParser(description="RAG Pipeline CLI")
    parser.add_argument("query", help="The query to process")
    parser.add_argument("--config", default="config.json", help="Path to the configuration file")
    parser.add_argument("--prompt-config", default="prompt_config.json", help="Path to the prompt configuration file")
    parser.add_argument("--stream", action="store_true", help="Enable streaming output")
    parser.add_argument("--show-evaluation", action="store_true", help="Show evaluation metrics")
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except FileNotFoundError:
        print(f"Config file not found: {args.config}")
        return
    except json.JSONDecodeError:
        print(f"Invalid JSON in config file: {args.config}")
        return

    pipeline = Pipeline(config, args.prompt_config)

    if args.stream:
        process_streaming(pipeline, args.query, args.show_evaluation)
    else:
        process_non_streaming(pipeline, args.query, args.show_evaluation)

def process_non_streaming(pipeline: Pipeline, query: str, show_evaluation: bool):
    result = pipeline.process(query)

    if 'error' in result:
        print(f"Error: {result['error']}")
    else:
        print("Original Query:", result['original_query'])
        print("Rewritten Query:", result['rewritten_query'])
        print("\nRetrieved Documents:")
        for i, doc in enumerate(result['retrieved_documents'], 1):
            print(f"{i}. ID: {doc['id']}, Score: {doc['score']}")
            print(f"   Content: {doc['content'][:100]}...")  # Print first 100 characters
        print("\nGenerated Response:", result['response'])
        
        if show_evaluation:
            print("\nEvaluation Metrics:")
            print_evaluation_metrics(result['evaluation'])

def process_streaming(pipeline: Pipeline, query: str, show_evaluation: bool):
    print("Streaming response:")
    for chunk in pipeline.process_stream(query):
        if 'error' in chunk:
            print(f"Error: {chunk['error']}")
        elif 'response_chunk' in chunk:
            print(chunk['response_chunk'], end='', flush=True)
        elif 'retrieved_documents' in chunk:
            print("\nRetrieved Documents:")
            for i, doc in enumerate(chunk['retrieved_documents'], 1):
                print(f"{i}. ID: {doc['id']}, Score: {doc['score']}")
                print(f"   Content: {doc['content'][:100]}...")  # Print first 100 characters
        elif 'evaluation' in chunk and show_evaluation:
            print("\nEvaluation Metrics:")
            print_evaluation_metrics(chunk['evaluation'])
    print()  # Print a newline after the streaming response

def print_evaluation_metrics(evaluation: Dict[str, Any]):
    for metric, value in evaluation.items():
        if isinstance(value, dict):
            print(f"  {metric}:")
            for sub_metric, sub_value in value.items():
                print(f"    {sub_metric}: {sub_value}")
        else:
            print(f"  {metric}: {value}")

if __name__ == "__main__":
    main()
