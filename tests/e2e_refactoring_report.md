# E2E Test Refactoring Report

## File: test_search_debug_edge_cases.py

- Total lines: 1833
- Total tests: 55
- Test classes: 9
- Test functions: 55

## Test Categories

### Atomic Tests (1)

- test_llm_config

### Unit Tests (0)

### Integration Tests (1)

- test_db

### E2E Tests (53)

- test_user
- test_empty_collection
- test_pipeline_config
- test_search_api_endpoint_basic_functionality
- test_search_document_ingestion_and_indexing
- test_search_llm_generation_with_context
- test_search_results_format_consistency
- test_search_with_different_query_types
- test_search_pipeline_execution_flow
- test_search_with_config_metadata
- test_search_vector_store_integration
- test_search_llm_provider_integration
- test_search_response_time_performance
- test_search_with_multiple_documents_retrieval
- test_search_uses_correct_collection
- test_search_with_invalid_collection_id
- test_search_with_malformed_collection_id
- test_search_with_documents_in_collection
- test_search_with_empty_collection
- test_search_document_indexing_verification
- test_search_results_display_format
- test_search_results_with_rewritten_query
- test_search_results_evaluation_metrics
- test_search_with_malformed_queries
- test_search_with_missing_required_fields
- test_search_with_invalid_pipeline_id
- test_search_with_invalid_user_id
- test_search_error_message_clarity
- test_search_timeout_handling
- test_search_concurrent_requests
- test_document_count_db_matches_vector_store
- test_collection_names_consistent_across_systems
- test_retrieved_document_ids_exist_in_metadata
- test_no_orphaned_documents_in_vector_store
- test_empty_collection_returns_graceful_message
- test_invalid_collection_id_returns_404
- test_malformed_query_returns_400_with_clear_error
- test_vector_store_connection_failure_returns_503
- test_search_with_empty_collection
- test_search_with_invalid_collection_id
- test_search_with_malformed_query
- test_search_with_very_long_query
- test_search_with_special_characters_in_query
- test_search_with_unicode_characters_in_query
- test_search_with_sql_injection_attempt
- test_search_with_xss_attempt
- test_search_with_very_short_query
- test_search_with_numeric_query
- test_search_with_whitespace_only_query
- test_search_results_display_formatting
- test_search_document_indexing_verification
- test_search_collection_selection_validation
- test_search_error_message_quality
