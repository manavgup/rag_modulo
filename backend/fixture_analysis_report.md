# Fixture Analysis Report
==================================================

## Summary
- Total fixtures: 66
- Duplicate fixtures: 4

## Fixture Distribution by Type
- centralized: 43
- e2e: 7
- integration: 8
- scattered: 8

## Duplicate Fixtures
### complex_test_pdf_path
Found in 2 files:
- integration/test_document_processors.py
- data_ingestion/test_pdf_processor.py

### mock_watsonx_imports
Found in 2 files:
- evaluation/test_evaluator.py
- evaluation/test_evaluation.py

### base_llm_parameters
Found in 2 files:
- fixtures/llm_parameter.py
- fixtures/llm.py

### mock_jwt_verification
Found in 2 files:
- e2e/test_auth_router.py
- e2e/test_health_router.py

## Fixtures by File
### api/base_test.py
Fixtures (1): setup

### conftest.py
Fixtures (2): capture_logs, configure_logging

### data_ingestion/test_pdf_processor.py
Fixtures (3): complex_test_pdf_path, pdf_processor, ibm_annual_report_path

### e2e/conftest.py
Fixtures (6): full_database_setup, full_llm_provider_setup, full_vector_store_setup, base_user_e2e, base_collection_e2e, base_team_e2e

### e2e/test_health_router.py
Fixtures (1): mock_jwt_verification

### evaluation/test_evaluation.py
Fixtures (1): mock_watsonx_imports

### fixtures/collections.py
Fixtures (4): base_collection, base_suggested_question, vector_store, indexed_documents

### fixtures/db.py
Fixtures (2): db_engine, db_session

### fixtures/files.py
Fixtures (1): base_file

### fixtures/llm.py
Fixtures (3): base_llm_parameters, provider_factory, get_watsonx

### fixtures/llm_model.py
Fixtures (2): base_model_input, ensure_watsonx_models

### fixtures/llm_parameter.py
Fixtures (1): default_llm_parameters_input

### fixtures/llm_provider.py
Fixtures (1): base_provider_input

### fixtures/pipelines.py
Fixtures (2): default_pipeline_config, base_pipeline_config

### fixtures/prompt_template.py
Fixtures (7): base_rag_prompt_template_input, base_question_gen_template_input, base_prompt_template_input, base_prompt_template, base_rag_prompt_template, base_question_gen_template, base_multiple_prompt_templates

### fixtures/services.py
Fixtures (17): session_mock_settings, collection_service, mock_pipeline_service, user_collection_service, file_service, question_service, search_service, team_service, session_llm_provider_service, session_llm_model_service, session_db, session_user_service, session_llm_parameters_service, session_prompt_template_service, ensure_watsonx_provider, init_providers, base_user

### fixtures/teams.py
Fixtures (3): base_team, user_team, base_user_team

### integration/conftest.py
Fixtures (3): test_database_url, test_milvus_config, test_minio_config

### integration/test_document_processors.py
Fixtures (2): sample_excel_path, processor_type

### integration/test_ingestion.py
Fixtures (1): vector_store_with_collection

### integration/test_user_flow.py
Fixtures (1): mock_oauth_client

### integration/test_vectordbs.py
Fixtures (1): store_type

### test_ci_environment.py
Fixtures (1): setup_environment
