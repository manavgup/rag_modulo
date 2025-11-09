# API Authentication

RAG Modulo provides secure API authentication using JWT (JSON Web Tokens).

## Authentication Methods

### JWT Token Authentication

The primary authentication method uses bearer tokens in the Authorization header.

```bash
Authorization: Bearer <your-jwt-token>
```

### Obtaining a Token

#### User Registration

```bash
POST /api/auth/register
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password",
  "email": "user@example.com"
}
```

**Response**:
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "username": "user@example.com",
  "email": "user@example.com"
}
```

#### User Login

```bash
POST /api/auth/login
Content-Type: application/json

{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

## Using Authentication

### API Requests

Include the JWT token in all authenticated API requests:

```bash
curl -X POST https://api.example.com/api/search \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is machine learning?",
    "collection_id": "123e4567-e89b-12d3-a456-426614174000",
    "user_id": "123e4567-e89b-12d3-a456-426614174000"
  }'
```

### Python Client

```python
import requests

# Obtain token
login_response = requests.post(
    "https://api.example.com/api/auth/login",
    json={"username": "user@example.com", "password": "secure_password"}
)
token = login_response.json()["access_token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
response = requests.post(
    "https://api.example.com/api/search",
    headers=headers,
    json={
        "question": "What is machine learning?",
        "collection_id": "123e4567-e89b-12d3-a456-426614174000",
        "user_id": "123e4567-e89b-12d3-a456-426614174000"
    }
)
```

## Token Expiration

- **Default Expiration**: 1 hour (3600 seconds)
- **Refresh**: Request a new token before expiration
- **Configuration**: Set via `JWT_EXPIRATION` environment variable

## Security Best Practices

### Environment Variables

Never hardcode credentials. Use environment variables:

```bash
export JWT_SECRET_KEY="your-secret-key-here"
export JWT_ALGORITHM="HS256"
export JWT_EXPIRATION=3600
```

See `.env.example` for full configuration.

### Token Storage

- **Client-side**: Store tokens securely (e.g., httpOnly cookies, secure storage)
- **Never**: Commit tokens to version control
- **Rotate**: Regularly rotate JWT secret keys

### HTTPS Required

Always use HTTPS in production to protect tokens in transit.

## Error Responses

### Invalid Token

```json
{
  "detail": "Invalid authentication credentials"
}
```

HTTP Status: `401 Unauthorized`

### Expired Token

```json
{
  "detail": "Token has expired"
}
```

HTTP Status: `401 Unauthorized`

### Missing Token

```json
{
  "detail": "Not authenticated"
}
```

HTTP Status: `401 Unauthorized`

## Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Auth Service

    Client->>API: POST /auth/login (credentials)
    API->>Auth Service: Validate credentials
    Auth Service-->>API: User validated
    API-->>Client: JWT token

    Client->>API: GET /api/collections (with token)
    API->>Auth Service: Validate token
    Auth Service-->>API: Token valid
    API-->>Client: Collections data
```

## CLI Authentication

See [CLI Authentication](../cli/authentication.md) for command-line usage.

## See Also

- [API Endpoints](endpoints.md) - Available API endpoints
- [API Schemas](schemas.md) - Request/response schemas
- [Error Handling](error-handling.md) - Error response format
