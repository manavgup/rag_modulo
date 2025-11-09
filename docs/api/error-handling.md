# Error Handling

This page documents error handling patterns and response formats in the RAG Modulo API.

## Error Response Format

All API errors return JSON responses with a consistent structure:

```json
{
  "detail": "Error description",
  "error_code": "ERROR_CODE",
  "field": "field_name"
}
```

For validation errors with multiple issues:

```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "collection_id"],
      "msg": "Field required"
    },
    {
      "type": "extra_forbidden",
      "loc": ["body", "invalid_field"],
      "msg": "Extra inputs are not permitted"
    }
  ]
}
```

## HTTP Status Codes

### Success Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 200 | OK | Successful GET, PUT, PATCH |
| 201 | Created | Successful POST creating resource |
| 204 | No Content | Successful DELETE |

### Client Error Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 400 | Bad Request | Invalid request syntax or parameters |
| 401 | Unauthorized | Missing or invalid authentication |
| 403 | Forbidden | Valid auth but insufficient permissions |
| 404 | Not Found | Resource does not exist |
| 409 | Conflict | Resource conflict (duplicate, state) |
| 422 | Unprocessable Entity | Validation errors |
| 429 | Too Many Requests | Rate limit exceeded |

### Server Error Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service temporarily unavailable |

## Common Error Scenarios

### Authentication Errors

#### Invalid Token

**Request**:
```bash
GET /api/collections
Authorization: Bearer invalid_token
```

**Response**: `401 Unauthorized`
```json
{
  "detail": "Invalid authentication credentials"
}
```

#### Missing Token

**Request**:
```bash
GET /api/collections
```

**Response**: `401 Unauthorized`
```json
{
  "detail": "Not authenticated"
}
```

#### Expired Token

**Request**:
```bash
GET /api/collections
Authorization: Bearer expired_token
```

**Response**: `401 Unauthorized`
```json
{
  "detail": "Token has expired"
}
```

### Validation Errors

#### Missing Required Field

**Request**:
```bash
POST /api/search
{
  "question": "What is ML?"
}
```

**Response**: `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "missing",
      "loc": ["body", "collection_id"],
      "msg": "Field required",
      "input": null
    },
    {
      "type": "missing",
      "loc": ["body", "user_id"],
      "msg": "Field required",
      "input": null
    }
  ]
}
```

#### Invalid Field Type

**Request**:
```bash
POST /api/search
{
  "question": "What is ML?",
  "collection_id": "not-a-uuid",
  "user_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Response**: `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "uuid_parsing",
      "loc": ["body", "collection_id"],
      "msg": "Input should be a valid UUID"
    }
  ]
}
```

#### Extra Fields Not Allowed

**Request**:
```bash
POST /api/search
{
  "question": "What is ML?",
  "collection_id": "123e4567-e89b-12d3-a456-426614174000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "invalid_field": "value"
}
```

**Response**: `422 Unprocessable Entity`
```json
{
  "detail": [
    {
      "type": "extra_forbidden",
      "loc": ["body", "invalid_field"],
      "msg": "Extra inputs are not permitted"
    }
  ]
}
```

### Resource Not Found

**Request**:
```bash
GET /api/collections/00000000-0000-0000-0000-000000000000
```

**Response**: `404 Not Found`
```json
{
  "detail": "Collection not found",
  "error_code": "COLLECTION_NOT_FOUND",
  "collection_id": "00000000-0000-0000-0000-000000000000"
}
```

### Permission Errors

**Request**:
```bash
DELETE /api/collections/123e4567-e89b-12d3-a456-426614174000
```

**Response**: `403 Forbidden`
```json
{
  "detail": "You do not have permission to delete this collection",
  "error_code": "INSUFFICIENT_PERMISSIONS"
}
```

### Rate Limiting

**Request** (after exceeding rate limit):
```bash
POST /api/search
```

**Response**: `429 Too Many Requests`
```json
{
  "detail": "Rate limit exceeded. Try again in 60 seconds.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

**Headers**:
```
Retry-After: 60
X-RateLimit-Limit: 20
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1609459260
```

### Server Errors

#### Internal Server Error

**Response**: `500 Internal Server Error`
```json
{
  "detail": "An unexpected error occurred",
  "error_code": "INTERNAL_ERROR",
  "request_id": "req_abc123"
}
```

#### Service Unavailable

**Response**: `503 Service Unavailable`
```json
{
  "detail": "Service temporarily unavailable. Please try again later.",
  "error_code": "SERVICE_UNAVAILABLE"
}
```

## Error Codes Reference

| Error Code | HTTP Status | Description |
|------------|-------------|-------------|
| AUTHENTICATION_FAILED | 401 | Invalid credentials |
| TOKEN_EXPIRED | 401 | JWT token expired |
| INSUFFICIENT_PERMISSIONS | 403 | User lacks required permissions |
| COLLECTION_NOT_FOUND | 404 | Collection does not exist |
| DOCUMENT_NOT_FOUND | 404 | Document does not exist |
| PIPELINE_NOT_FOUND | 404 | Pipeline does not exist |
| VALIDATION_ERROR | 422 | Request validation failed |
| DUPLICATE_COLLECTION | 409 | Collection name already exists |
| RATE_LIMIT_EXCEEDED | 429 | Too many requests |
| INTERNAL_ERROR | 500 | Unexpected server error |
| SERVICE_UNAVAILABLE | 503 | Service temporarily down |

## Client Error Handling

### Python Example

```python
import requests
from requests.exceptions import HTTPError, RequestException

def handle_api_request(url, method="GET", **kwargs):
    """Make API request with comprehensive error handling."""
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    except HTTPError as e:
        status_code = e.response.status_code
        error_data = e.response.json()

        if status_code == 401:
            print("Authentication failed. Please login again.")
        elif status_code == 403:
            print("Permission denied:", error_data.get("detail"))
        elif status_code == 404:
            print("Resource not found:", error_data.get("detail"))
        elif status_code == 422:
            print("Validation errors:")
            for error in error_data.get("detail", []):
                print(f"  - {error['loc']}: {error['msg']}")
        elif status_code == 429:
            retry_after = error_data.get("retry_after", 60)
            print(f"Rate limited. Retry after {retry_after} seconds.")
        else:
            print(f"HTTP error {status_code}:", error_data.get("detail"))

        return None

    except RequestException as e:
        print(f"Request failed: {e}")
        return None

# Usage
result = handle_api_request(
    "http://localhost:8000/api/search",
    method="POST",
    headers={"Authorization": f"Bearer {token}"},
    json=search_query
)
```

### JavaScript Example

```javascript
async function handleApiRequest(url, options = {}) {
  try {
    const response = await fetch(url, options);

    if (!response.ok) {
      const errorData = await response.json();

      switch (response.status) {
        case 401:
          console.error("Authentication failed");
          break;
        case 403:
          console.error("Permission denied:", errorData.detail);
          break;
        case 404:
          console.error("Resource not found:", errorData.detail);
          break;
        case 422:
          console.error("Validation errors:", errorData.detail);
          break;
        case 429:
          console.error(`Rate limited. Retry after ${errorData.retry_after}s`);
          break;
        default:
          console.error(`Error ${response.status}:`, errorData.detail);
      }

      return null;
    }

    return await response.json();

  } catch (error) {
    console.error("Request failed:", error);
    return null;
  }
}

// Usage
const result = await handleApiRequest('/api/search', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify(searchQuery)
});
```

## Retry Strategies

### Exponential Backoff

```python
import time
from requests.exceptions import HTTPError

def api_call_with_retry(url, max_retries=3, **kwargs):
    """Make API call with exponential backoff retry."""
    for attempt in range(max_retries):
        try:
            response = requests.request(**kwargs, url=url)
            response.raise_for_status()
            return response.json()

        except HTTPError as e:
            if e.response.status_code == 429:
                # Rate limited - use Retry-After header
                retry_after = int(e.response.headers.get('Retry-After', 60))
                print(f"Rate limited. Waiting {retry_after}s...")
                time.sleep(retry_after)
            elif e.response.status_code >= 500:
                # Server error - exponential backoff
                wait_time = 2 ** attempt
                print(f"Server error. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                # Client error - don't retry
                raise

        except requests.exceptions.RequestException:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                print(f"Request failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                raise

    raise Exception("Max retries exceeded")
```

## Best Practices

1. **Always Check Status Codes**: Don't assume 200 OK
2. **Handle Validation Errors**: Display field-specific errors to users
3. **Implement Retry Logic**: For rate limits and server errors
4. **Log Error Details**: Include request_id for debugging
5. **Use Timeouts**: Prevent hanging requests
6. **Graceful Degradation**: Provide fallback behavior

## See Also

- [API Endpoints](endpoints.md) - Available endpoints
- [API Schemas](schemas.md) - Request/response schemas
- [Authentication](authentication.md) - Authentication guide
- [Examples](examples.md) - API usage examples
