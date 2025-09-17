# API Documentation

This section contains comprehensive documentation for the RAG Modulo API and its simplified architecture.

## Search API

### Core Components

- **[Search API](search_api.md)** - Complete search API documentation with automatic pipeline resolution
- **[Search Schemas](search_schemas.md)** - Data structures for search requests and responses

### Key Features

**Simplified Pipeline Resolution**: The search API now automatically handles pipeline selection based on user context, eliminating client-side pipeline management complexity.

**Breaking Changes from Legacy API**:
- Removed `pipeline_id` from SearchInput schema
- Added automatic pipeline resolution in SearchService
- Simplified CLI interface without pipeline parameters
- Enhanced error handling for configuration issues

## Service Architecture

### Backend Services

- **[Service Configuration](service_configuration.md)** - Service-based configuration system
- **[Provider Configuration](provider_configuration.md)** - LLM provider and model management
- **[Prompt Templates](prompt_templates.md)** - Template management system
- **[Question Suggestion](question_suggestion.md)** - Intelligent query suggestions

### Development Documentation

Development-specific documentation has been moved to:
- **[Backend Development](../development/backend/)** - Guidelines and development tasks

## Migration Guide

### From Legacy API

**Before (Legacy)**:
```python
# Client had to manage pipeline selection
pipeline_id = get_user_pipeline(user_id, collection_id)
search_input = SearchInput(
    question="What is ML?",
    collection_id=collection_id,
    user_id=user_id,
    pipeline_id=pipeline_id  # Client-managed
)
```

**After (Current)**:
```python
# Backend handles pipeline selection automatically
search_input = SearchInput(
    question="What is ML?",
    collection_id=collection_id,
    user_id=user_id
    # No pipeline_id needed
)
```

### Schema Changes

1. **SearchInput Schema**:
   - ✅ Removed `pipeline_id` field
   - ✅ Added `extra="forbid"` validation
   - ✅ Simplified field requirements

2. **Service Layer**:
   - ✅ Added automatic pipeline resolution
   - ✅ Enhanced error handling
   - ✅ Improved user experience

3. **CLI Interface**:
   - ✅ Removed pipeline parameters
   - ✅ Simplified command structure
   - ✅ Automatic configuration

## Testing

### Test Coverage

- **Unit Tests**: Schema validation, service logic, pipeline resolution
- **Integration Tests**: End-to-end search flow, database integration
- **API Tests**: Endpoint validation, error handling

### Running Tests

```bash
# Schema and service tests
pytest backend/tests/unit/test_search_service_pipeline_resolution.py

# Integration tests
pytest backend/tests/integration/test_search_integration.py

# API endpoint tests
pytest backend/tests/api/test_search_endpoints.py
```

## Performance Considerations

### Automatic Pipeline Creation

- First search for new users triggers pipeline creation
- Pipeline creation includes LLM provider validation
- Default configurations applied automatically
- All operations logged for audit

### Caching Strategy

- Response caching based on search input hash
- Pipeline resolution results cached per user
- Configurable cache TTL (default: 1 hour)

## Security

### Access Control

- User authentication required for all operations
- Collection access validation
- Pipeline isolation between users
- Audit logging for all search activities

### Input Validation

- Strict schema validation with `extra="forbid"`
- Query length and content validation
- Configuration parameter range checking
- SQL injection prevention

## Error Handling

### Common Error Scenarios

1. **Configuration Errors**:
   - No LLM provider configured
   - Invalid provider credentials
   - Missing pipeline configuration

2. **Access Errors**:
   - Collection not found or access denied
   - User authentication failures
   - Rate limiting violations

3. **Validation Errors**:
   - Invalid search input format
   - Parameter out of range
   - Malformed configuration metadata

### Error Response Format

```json
{
    "detail": "Error description",
    "error_code": "STANDARDIZED_ERROR_CODE",
    "timestamp": "2023-12-07T10:30:00Z",
    "request_id": "req-unique-id",
    "user_id": "user-uuid-if-available"
}
```

## Future Enhancements

### Planned Improvements

1. **Enhanced Pipeline Resolution**:
   - Context-aware pipeline selection
   - Collection-specific optimizations
   - A/B testing support

2. **Advanced Search Features**:
   - Multi-collection search
   - Streaming responses
   - Real-time suggestions

3. **Performance Optimizations**:
   - Parallel processing
   - Predictive caching
   - Resource optimization

4. **Analytics and Monitoring**:
   - Search quality metrics
   - Performance dashboards
   - Usage analytics

## Support

For additional help:
- Check the [troubleshooting guide](../cli/troubleshooting.md)
- Review [configuration options](../configuration.md)
- See [development workflow](../development/workflow.md)

---

**Last Updated**: December 2023
**API Version**: 2.0 (Simplified Pipeline Resolution)
