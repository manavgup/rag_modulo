# RAG Modulo API Endpoints Documentation

## Current Backend API Endpoints

### 1. Authentication (`/auth`)
- `GET /auth/oidc-config` - Get OIDC configuration
- `POST /auth/token` - Get access token
- `GET /auth/login` - Login endpoint
- `GET /auth/callback` - OAuth callback
- `POST /auth/logout` - Logout
- `GET /auth/userinfo` - Get user info
- `GET /auth/me` - Get current user
- `GET /auth/check-auth` - Check authentication status
- `GET /auth/session` - Get session info
- `POST /auth/cli/start` - Start CLI authentication
- `POST /auth/cli/token` - Get CLI token
- `POST /auth/device/start` - Start device flow auth
- `POST /auth/device/poll` - Poll device flow status

### 2. Users (`/users`)
- `POST /users/` - Create user
- `GET /users/` - List users
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user
- `PUT /users/{user_id}/preferred/{provider_id}` - Set preferred provider
- `GET /users/{user_id}/preferred` - Get preferred provider

#### User Prompts
- `GET /users/{user_id}/prompts` - Get user prompts
- `POST /users/{user_id}/prompts` - Create prompt
- `PUT /users/{user_id}/prompts/{prompt_id}` - Update prompt
- `DELETE /users/{user_id}/prompts/{prompt_id}` - Delete prompt
- `PUT /users/{user_id}/prompts/{prompt_id}/default` - Set default prompt
- `GET /users/{user_id}/prompts/default` - Get default prompt

#### User Pipelines
- `GET /users/{user_id}/pipelines` - Get user pipelines
- `POST /users/{user_id}/pipelines` - Create pipeline
- `PUT /users/{user_id}/pipelines/{pipeline_id}` - Update pipeline
- `DELETE /users/{user_id}/pipelines/{pipeline_id}` - Delete pipeline
- `PUT /users/{user_id}/pipelines/{pipeline_id}/default` - Set default pipeline

#### User LLM Providers
- `GET /users/{user_id}/llm-providers` - Get user LLM providers
- `POST /users/{user_id}/llm-providers` - Add LLM provider
- `PUT /users/{user_id}/llm-providers/{provider_id}` - Update LLM provider
- `DELETE /users/{user_id}/llm-providers/{provider_id}` - Remove LLM provider
- `PUT /users/{user_id}/llm-providers/{provider_id}/default` - Set default provider
- `GET /users/{user_id}/llm-providers/default` - Get default provider
- `POST /users/{user_id}/llm-providers/test` - Test provider
- `PUT /users/{user_id}/llm-providers/{provider_id}/credentials` - Update credentials
- `DELETE /users/{user_id}/llm-providers/{provider_id}/credentials` - Delete credentials
- `GET /users/{user_id}/llm-providers/{provider_id}/models` - Get available models
- `GET /users/{user_id}/llm-providers/type/{provider_type}` - Get providers by type

#### User Collections
- `GET /users/{user_id}/collections` - Get user collections
- `DELETE /users/{user_id}/collections/{collection_id}` - Delete user collection

#### User Files
- `POST /users/{user_id}/files/collections/{collection_id}` - Upload files to collection
- `DELETE /users/{user_id}/files/collections/{collection_id}/files/{file_id}` - Delete file from collection

### 3. Collections (`/collections`)
- `POST /collections/debug-form-data` - Debug form data
- `POST /collections/debug-form-data-with-db` - Debug with DB
- `GET /collections/` - List collections
- `GET /collections/{collection_id}` - Get collection details
- `POST /collections/` - Create collection
- `POST /collections/{collection_id}/upload` - Upload files to collection
- `GET /collections/{collection_id}/files` - Get collection files
- `POST /collections/{collection_id}/files/{file_id}/process` - Process file
- `GET /collections/{collection_id}/stats` - Get collection statistics
- `DELETE /collections/{collection_id}` - Delete collection
- `DELETE /collections/{collection_id}/files` - Delete all files
- `DELETE /collections/{collection_id}/files/{file_id}` - Delete specific file
- `GET /collections/{collection_id}/documents` - Get documents
- `DELETE /collections/{collection_id}/documents/{document_id}` - Delete document
- `GET /collections/{collection_id}/status` - Get collection status
- `GET /collections/{collection_id}/download` - Download collection
- `DELETE /collections/{collection_id}/vectors` - Delete vectors
- `PUT /collections/{collection_id}` - Update collection

### 4. Search (`/search`)
- `POST /search/search` - Perform search with RAG

### 5. Chat (`/chat`)
#### Sessions
- `POST /chat/sessions` - Create chat session
- `GET /chat/sessions/{session_id}` - Get session
- `PUT /chat/sessions/{session_id}` - Update session
- `DELETE /chat/sessions/{session_id}` - Delete session
- `GET /chat/sessions` - List all sessions

#### Messages
- `POST /chat/sessions/{session_id}/messages` - Add message
- `GET /chat/sessions/{session_id}/messages` - Get messages
- `POST /chat/sessions/{session_id}/process` - Process message with AI

#### Session Features
- `GET /chat/sessions/{session_id}/statistics` - Get session statistics
- `GET /chat/sessions/{session_id}/export` - Export conversation
- `GET /chat/sessions/{session_id}/suggestions` - Get suggestions
- `POST /chat/sessions/{session_id}/summaries` - Create summary
- `GET /chat/sessions/{session_id}/summaries` - Get summaries
- `POST /chat/sessions/{session_id}/context-summarization` - Summarize context
- `GET /chat/sessions/{session_id}/context-threshold` - Get context threshold
- `POST /chat/sessions/{session_id}/conversation-suggestions` - Get conversation suggestions
- `POST /chat/sessions/{session_id}/enhanced-export` - Enhanced export

### 6. LLM Providers (`/llm-providers`)
- `POST /llm-providers/` - Create provider
- `GET /llm-providers/` - List providers
- `GET /llm-providers/{provider_id}` - Get provider
- `PUT /llm-providers/{provider_id}` - Update provider
- `DELETE /llm-providers/{provider_id}` - Delete provider

#### Models
- `POST /llm-providers/models/` - Create model
- `GET /llm-providers/models/provider/{provider_id}` - Get models by provider
- `GET /llm-providers/models/type/{model_type}` - Get models by type
- `GET /llm-providers/models/{model_id}` - Get model
- `PUT /llm-providers/models/{model_id}` - Update model
- `DELETE /llm-providers/models/{model_id}` - Delete model
- `GET /llm-providers/{provider_id}/with-models` - Get provider with models

### 7. Teams (`/teams`)
- `POST /teams/` - Create team
- `PUT /teams/{team_id}` - Update team
- `GET /teams/{team_id}` - Get team
- `PUT /teams/{team_id}/users/{user_id}` - Add user to team
- `DELETE /teams/{team_id}/users/{user_id}` - Remove user from team
- `GET /teams/` - List teams
- `GET /teams/{team_id}/users` - Get team users
- `POST /teams/{team_id}/invite` - Invite user to team

### 8. Token Warnings (`/token-warnings`)
- `GET /token-warnings/check` - Check token warnings
- `GET /token-warnings/configuration` - Get configuration
- `GET /token-warnings/logs` - Get warning logs
- `PUT /token-warnings/configuration` - Update configuration
- `GET /token-warnings/stats` - Get statistics
- `DELETE /token-warnings/logs` - Clear logs
- `DELETE /token-warnings/logs/{log_id}` - Delete specific log

### 9. Health (`/health`)
- `GET /health/` - Health check endpoint

## Frontend API Service Structure

The frontend should implement the following service structure:

```typescript
// src/services/api.ts
const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Service modules
- authService.ts      // Authentication related
- userService.ts       // User management
- collectionService.ts // Collection operations
- searchService.ts     // Search and RAG
- chatService.ts       // Chat sessions
- llmService.ts        // LLM provider management
- teamService.ts       // Team management
```

## WebSocket Endpoints (To Be Implemented)

For real-time features, implement WebSocket connections:

```typescript
// src/services/websocket.ts
const WS_BASE_URL = process.env.REACT_APP_WS_URL || 'ws://localhost:8000';

// WebSocket events
- chat.message        // Real-time chat messages
- collection.status   // Collection processing status
- search.progress     // Search progress updates
- notification.new    // System notifications
```

## API Integration Priority

1. **Phase 1 - Core Features** (Immediate)
   - Authentication (`/auth/*`)
   - Collections (`/collections/*`)
   - Search (`/search/*`)
   - Chat (`/chat/*`)

2. **Phase 2 - User Management**
   - User profiles (`/users/*`)
   - User preferences
   - User collections

3. **Phase 3 - Advanced Features**
   - LLM Providers (`/llm-providers/*`)
   - Teams (`/teams/*`)
   - Token warnings

## Notes

- All endpoints require authentication except `/health` and `/auth/login`
- Use JWT tokens in Authorization header: `Bearer <token>`
- File uploads use multipart/form-data
- JSON responses follow consistent schema with `status`, `data`, and `error` fields
- Pagination supported on list endpoints with `?page=1&size=10`
- Filtering supported with query parameters
