# TODO Items

## Service Layer Migration

### 1. Evaluation System Updates
The evaluation system needs to be migrated to use our service architecture:

1. Create EvaluationService:
   - Implement repository pattern
   - Add validation schemas
   - Support async operations
   - Handle error cases

2. Update Evaluator:
   - Use LLMProviderService
   - Use PromptTemplateService
   - Use proper error handling
   - Support configuration

3. Add Template Support:
   - Create evaluation templates
   - Add template validation
   - Support context strategies
   - Handle template errors

4. Testing Updates:
   - Add service tests
   - Update integration tests
   - Add error case tests
   - Test template usage

### 2. Pipeline Service Completion

1. Query Rewriting:
   - Move to service layer
   - Add repository pattern
   - Support configuration
   - Add validation

2. Document Management:
   - Improve initialization
   - Better error handling
   - Support async loading
   - Add cleanup

3. Retriever Integration:
   - Use service pattern
   - Add configuration
   - Support multiple strategies
   - Handle errors

4. Testing:
   - Add service tests
   - Test error cases
   - Test configuration
   - Integration tests

### 3. Text Generation Service Refactoring

1. Create GenerationService:
   - Centralize text generation logic
   - Handle parameter lookup and prompt formatting
   - Manage provider selection and configuration
   - Provide clean interface for other services (QuestionService, SearchService, EvaluationService)

2. Simplify LLMProvider:
   - Focus only on text generation with formatted prompts and parameters
   - Remove service dependencies (llm_provider_service, llm_parameters_service, prompt_template_service)
   - Remove user-specific logic
   - Accept model_id directly instead of looking it up by user_id

3. Benefits:
   - Centralized text generation logic
   - Easier to add new RAG components
   - Reduced code duplication
   - Easier testing
   - Better separation of concerns
   - Follows single responsibility principle

4. Migration Plan:
   - Create GenerationService
   - Update LLMProvider implementations
   - Migrate QuestionService to use GenerationService
   - Update tests
   - Add integration tests
   - Document new design

### 4. Service Layer Improvements

1. Error Handling:
   - Consistent error types
   - Better error messages
   - Error propagation
   - Error recovery

2. Configuration:
   - Runtime configuration
   - Service configuration
   - Template management
   - Provider settings

3. Performance:
   - Add caching
   - Optimize queries
   - Improve concurrency
   - Monitor usage

4. Security:
   - Access control
   - Input validation
   - Output sanitization
   - Audit logging

### Current Implementation Notes

#### Legacy Code Cleanup
- pipeline.py is now deprecated in favor of pipeline_service.py
- Added deprecation warning to pipeline.py
- Keep pipeline.py temporarily for reference
- Plan removal after full service migration verification
- Update any remaining imports to use pipeline_service.py

#### CLI Tools Deprecation
- generator.py and rag_cli.py are deprecated and will be removed
- These tools use file-based configuration (prompt_config.json) instead of database-driven approach
- Need to create new CLI tools that:
  - Use the service layer architecture
  - Support database-driven templates
  - Handle authentication and authorization
  - Provide better error handling and logging
  - Support all features of the main application
- Plan migration path for users of these tools

#### Deprecation Handling
- Suppress deprecation warnings in tests using:
  ```python
  import warnings
  import pytest

  @pytest.mark.filterwarnings("ignore::DeprecationWarning")
  def test_legacy_pipeline():
      # Test code here
  ```
- Or use pytest.ini configuration:
  ```ini
  [pytest]
  filterwarnings =
      ignore::DeprecationWarning:rag_solution.pipeline.pipeline
  ```
- Document deprecation timeline in release notes
- Monitor usage through warning logs

#### Evaluation System
- Currently uses direct watsonx.utils
- Needs service layer migration
- Requires template support
- Needs better error handling

#### Pipeline System
- Migrated to service architecture
- Using pipeline_service.py
- Fully integrated with services
- Supporting templates and configuration

#### Service Layer
- Adding new services
- Improving error handling
- Adding configuration
- Enhancing security

### Migration Benefits

1. Consistency:
   - Unified service pattern
   - Standard error handling
   - Consistent configuration
   - Better maintainability

2. Functionality:
   - Better error handling
   - Improved configuration
   - Enhanced security
   - Better performance

3. Development:
   - Easier testing
   - Better documentation
   - Simpler maintenance
   - Faster development

4. Operations:
   - Better monitoring
   - Easier debugging
   - Improved reliability
   - Simpler deployment

## Future Improvements

### 1. Service Features
- Version control for configurations
- Service health monitoring
- Performance metrics
- Usage analytics

### 2. Template System
- Template versioning
- Template inheritance
- Dynamic validation
- Template marketplace

### 3. Provider System
- Provider versioning
- Provider metrics
- Auto-scaling
- Load balancing

### 4. Security
- Enhanced encryption
- Key rotation
- Access policies
- Security monitoring

### 5. Testing
- Performance testing
- Load testing
- Security testing
- Integration testing

### 6. Documentation
- API documentation
- Service documentation
- Configuration guides
- Development guides

This work should be done in separate PRs to keep changes focused and manageable.
