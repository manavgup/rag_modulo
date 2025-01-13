#!/usr/bin/env python3
"""
Script to help categorize and move tests to their appropriate directories.
"""
import os
import shutil
from pathlib import Path

def categorize_tests():
    # Base test directory
    base_dir = Path('backend/tests')
    
    # Test categories and their corresponding files/patterns
    categories = {
        'unit': [
            'unit/test_core_config.py',
            'unit/test_llm_parameters.py',
            'unit/test_provider_config.py',
            'unit/test_prompt_template.py',
            'unit/test_watsonx.py',
            'data/test_data_helper.py',
            'test_postgresql_connection.py',
            'test_milvus_connection.py',
        ],
        'integration': [
            'integration/test_user_flow.py',
            'vectordbs/test_weaviate_store.py',
            'vectordbs/test_milvus_store.py',
            'vectordbs/test_elasticsearch_store.py',
            'vectordbs/test_pinecone_store.py',
            'vectordbs/test_chromadb_store.py',
            'test_provider_initialization.py',
        ],
        'service': [
            'service/test_generator.py',
            'service/test_provider_factory.py',
            'service/test_search_service.py',
            'service/test_question_service.py',
            'service/test_pipeline.py',
            'services/test_runtime_config_service.py',
            'retrieval/test_factories.py',
            'retrieval/test_retriever.py',
            'query_rewriting/test_query_rewriter.py',
            'evaluation/test_mlflow.py',
        ],
        'api': [
            'api/test_user_router.py',
            'api/test_collection_router.py',
            'api/test_api.py',
            'api/test_health_router.py',
            'router/test_user_team_router.py',
            'router/test_search_router.py',
            'router/test_file_router.py',
            'router/test_router.py',
            'router/test_user_collection_router.py',
            'router/test_team_router.py',
        ],
        'model': [
            'vectordbs/test_models.py',
            'collection/test_collection.py',
            'file/test_file.py',
            'user/test_user.py',
            'team/test_team.py',
            'user_collection/test_user_collection.py',
            'user_team/test_user_team.py',
        ],
        'data_ingestion': [
            'data_ingestion/test_excel_processor.py',
            'data_ingestion/test_chunking.py',
            'data_ingestion/test_pdf_processor.py',
            'data_ingestion/test_document_processor.py',
            'data_ingestion/test_ingestion.py',
            'data_ingestion/test_word_processor.py',
            'data_ingestion/test_txt_processor.py',
        ],
        'vectordb': [
            'vectordbs/test_base_store.py',
            'vectordbs/test_vector_store.py',
        ]
    }
    
    # Create directories if they don't exist
    for category in categories:
        category_dir = base_dir / category
        category_dir.mkdir(exist_ok=True)
        print(f"Created directory: {category_dir}")
    
    def safe_move(src: Path, dst: Path) -> None:
        """Safely move a file, creating parent directories if needed."""
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            print(f"Moving {src} to {dst}")
            if not dst.exists():
                shutil.move(str(src), str(dst))
            else:
                print(f"Warning: {dst} already exists, skipping...")
        else:
            print(f"Warning: Could not find {src}")
    
    # Move files to appropriate directories
    for category, file_patterns in categories.items():
        for file_pattern in file_patterns:
            src = base_dir / file_pattern
            dst = base_dir / category / Path(file_pattern).name
            safe_move(src, dst)
    
    # Clean up empty directories after moving
    for dirpath, dirnames, filenames in os.walk(base_dir, topdown=False):
        dir_path = Path(dirpath)
        if dir_path != base_dir and not any(dir_path.iterdir()):
            try:
                dir_path.rmdir()
                print(f"Removed empty directory: {dir_path}")
            except OSError as e:
                print(f"Could not remove directory {dir_path}: {e}")

if __name__ == '__main__':
    categorize_tests()