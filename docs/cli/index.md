# RAG CLI

The RAG CLI is a comprehensive command-line interface for interacting with the RAG Modulo system. It provides a complete set of tools for managing collections, documents, search operations, user authentication, LLM providers, and pipelines through a streamlined command-line experience.

> **Status**: The CLI is **fully functional** as of the latest updates. All major features including authentication, collection management, document upload, and search operations are working correctly.

## Overview

RAG CLI enables developers and administrators to:

- **Authenticate** with IBM OIDC providers and manage tokens
- **Manage Collections** - create, list, update, and configure document collections
- **Upload Documents** - add and process documents for retrieval
- **Execute Searches** - perform semantic search, hybrid search, and RAG queries
- **Administer Users** - manage user accounts and permissions
- **Configure Providers** - manage LLM providers and their settings
- **Manage Pipelines** - create and configure search pipelines
- **System Health** - check system status and run diagnostics
- **Configuration** - manage CLI profiles and settings

## Quick Start

### Prerequisites

- RAG Modulo backend running (default: `http://localhost:8000`)
- Valid IBM OIDC credentials (for production) or mock authentication enabled (for development)
- Python 3.8+ environment

### Installation

```bash
# Install from source
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo/backend
poetry install

# Activate environment
poetry shell
```

### First Steps

1. **Check CLI availability**:
   ```bash
   rag-cli --help
   ```

2. **Authenticate** (Production):
   ```bash
   rag-cli auth login
   ```

   Or for development/testing:
   ```bash
   export TESTING=true
   export SKIP_AUTH=true
   ```

3. **Create a collection**:
   ```bash
   rag-cli collections create "My Documents" --description "Personal collection"
   ```

4. **Upload a document**:
   ```bash
   rag-cli documents upload <collection-id> /path/to/document.pdf
   ```

5. **Search your collection**:
   ```bash
   rag-cli search query <collection-id> "What is machine learning?"
   ```

   > **Note**: The CLI automatically retrieves user context and pipeline configuration from the authentication session.

## Specialized CLIs

For focused workflows, use the specialized CLI tools:

### rag-search
Direct search interface for quick queries without the overhead of the full CLI:

```bash
# Direct search
rag-search "What is AI?" --collection abc123

# Semantic search
rag-search "Explain quantum computing" --collection abc123 --semantic

# Hybrid search
rag-search "Find similar docs" --collection abc123 --hybrid
```

### rag-admin
Administrative operations for user and system management:

```bash
# User management
rag-admin users list --role admin
rag-admin users create user@example.com --name "John Doe" --role admin

# System health
rag-admin health check --api --database --vector-db

# Configuration
rag-admin config validate --api-url http://localhost:8000
```

4. **Verify connection**:
   ```bash
   ./rag-cli auth status
   ```

### Basic Workflow

```bash
# Create a collection
./rag-cli collections create "My Documents" --description "Personal knowledge base"

# Upload documents
./rag-cli documents upload COLLECTION_ID ./my-document.pdf --title "Important Document"

# Search your collection
./rag-cli search query COLLECTION_ID "What are the key findings?"
```

## Architecture

### Component Structure

The CLI follows a modular architecture with clear separation of concerns:

```
rag_modulo/cli/
├── main.py              # Entry point and argument parsing
├── client.py            # HTTP API client with retry logic
├── auth.py             # Authentication manager
├── config.py           # Configuration and profile management
├── output.py           # Output formatting (table, json, csv, yaml)
├── exceptions.py       # Custom exception types
└── commands/           # Command modules
    ├── base.py         # Base command class
    ├── auth.py         # Authentication commands
    ├── collections.py  # Collection management
    ├── documents.py    # Document operations
    ├── search.py       # Search functionality (FIXED)
    ├── users.py        # User management
    ├── providers.py    # LLM provider management
    ├── pipelines.py    # Pipeline configuration
    ├── health.py       # System health checks
    └── config.py       # Configuration commands
```

### Data Flow

The CLI communicates with the RAG Modulo backend through RESTful APIs:

```
┌─────────────┐    HTTP/REST    ┌─────────────────┐
│   RAG CLI   │ ──────────────> │  Backend API    │
│             │                 │  (FastAPI)      │
└─────────────┘                 └─────────────────┘
       │                               │
       │ Local Storage                 │ Services
       │ (auth tokens)                 │
       ▼                               ▼
┌─────────────┐                 ┌─────────────────┐
│ ~/.rag/     │                 │ PostgreSQL      │
│ config.json │                 │ Milvus          │
└─────────────┘                 │ Document Store  │
                                └─────────────────┘
```

### Authentication Flow

The CLI now properly handles user context for all operations:

1. **Authentication**: User authenticates via OIDC or mock auth
2. **User Context**: CLI retrieves user info from `/api/auth/me`
3. **Pipeline Resolution**: Fetches user's default pipeline if needed
4. **Request Execution**: Includes full context in API calls

## Key Features

### Authentication
- **IBM OIDC Integration**: Seamless authentication with IBM identity providers
- **Token Management**: Automatic token refresh and secure local storage
- **Multi-Profile Support**: Configure multiple environments (dev, staging, prod)

### Collection Management
- **Create Collections**: Define document repositories with custom settings
- **Vector Database Support**: Choose from Milvus, ChromaDB, and other backends
- **Privacy Controls**: Public and private collection management

### Document Processing
- **Multi-Format Support**: PDF, DOCX, TXT, and more
- **Chunking Strategies**: Configurable text segmentation
- **Metadata Management**: Rich document tagging and categorization

### Search & Retrieval
- **Semantic Search**: Vector-based similarity search
- **RAG Queries**: Generate answers using retrieved context
- **Result Filtering**: Fine-tune results with relevance controls

## Configuration

The CLI uses a configuration file located at `~/.rag/config.json`:

```json
{
  "profiles": {
    "default": {
      "api_url": "http://localhost:8000",
      "timeout": 30,
      "auth": {
        "provider": "ibm",
        "client_id": "your-client-id"
      }
    }
  },
  "active_profile": "default"
}
```

## Implementation Status

### ✅ Fully Implemented Features

- **Authentication System**: OIDC login, token management, profile support
- **User Management**: Create, list, update, delete users
- **Collection Management**: Full CRUD operations, sharing, status tracking
- **Document Management**: Upload, batch upload, reprocess, export
- **Search Operations**: Query, explain, batch, semantic, hybrid search
- **Provider Management**: List, configure, test LLM providers
- **Pipeline Management**: Create, update, delete, test pipelines
- **System Health**: Health checks, monitoring, diagnostics
- **Configuration**: Profile management, settings, import/export

### ❌ Not Yet Implemented

- **Team Management**: Team creation, member management, role assignment
  - No `teams.py` command module exists yet
  - Team-related parameters in user commands are placeholders

### Recent Fixes

The search functionality has been completely fixed to properly:
- Retrieve user context from `/api/auth/me`
- Fetch user's default pipeline automatically
- Call the correct `/api/search` endpoint with proper schema
- No hardcoded UUIDs or user IDs

## Testing Coverage

The CLI has comprehensive test coverage across the testing pyramid:

### Test Structure

```
tests/
├── atomic/
│   └── test_cli_core.py      # Pure logic tests, no dependencies
├── unit/
│   ├── test_cli_client.py    # API client tests with mocks
│   └── test_cli_atomic.py    # Command and config tests
├── integration/
│   └── test_cli_integration.py # Service integration tests
└── e2e/
    └── test_cli_e2e.py       # Complete workflow tests
```

### Running Tests

```bash
# Run all CLI tests
pytest tests/ -k cli

# Run specific test levels
pytest tests/atomic/test_cli_core.py
pytest tests/unit/test_cli_client.py
pytest tests/integration/test_cli_integration.py
pytest tests/e2e/test_cli_e2e.py

# Run with coverage
pytest tests/ -k cli --cov=rag_solution.cli
```

## Development Mode

For development and testing, use mock authentication:

```bash
# Enable mock authentication
export TESTING=true
export SKIP_AUTH=true

# Optional: Set specific mock token
export MOCK_TOKEN="dev-0000-0000-0000"

# Run CLI commands without real authentication
rag-cli collections list
rag-cli search query <collection_id> "test query"
```

### Mock Authentication Behavior

When mock authentication is enabled:
1. Automatically creates a mock user if not exists
2. Initializes default LLM provider and pipeline
3. Sets up required prompt templates
4. All commands work without real OIDC authentication

## Common Workflows

### Complete Document Processing Workflow

```bash
# 1. Setup and authenticate
rag-cli auth login

# 2. Create a collection
COLLECTION_ID=$(rag-cli collections create "Research Papers" \
  --description "ML research papers" \
  --output json | jq -r '.id')

# 3. Upload documents
rag-cli documents upload $COLLECTION_ID \
  paper1.pdf paper2.pdf paper3.pdf

# 4. Monitor processing
rag-cli collections status $COLLECTION_ID --wait

# 5. Search the collection
rag-cli search query $COLLECTION_ID \
  "What are the latest advances in transformer models?"

# 6. Get search explanation
rag-cli search explain $COLLECTION_ID \
  "transformer architecture improvements" \
  --show-retrieval --show-rewriting
```

### Batch Operations

```bash
# Batch document upload
rag-cli documents batch-upload $COLLECTION_ID \
  --directory ./documents/ \
  --pattern "*.pdf"

# Batch search
rag-cli search batch $COLLECTION_ID \
  --queries "query1" "query2" "query3" \
  --output-file results.json
```

## Troubleshooting

### Search Not Working

If search returns errors about missing pipeline_id or user_id:

1. **Ensure you're authenticated**:
   ```bash
   rag-cli auth status
   ```

2. **Check user has default pipeline**:
   ```bash
   rag-cli pipelines list
   ```

3. **For testing, use mock auth**:
   ```bash
   export TESTING=true
   export SKIP_AUTH=true
   ```

### Collection Processing Stuck

If documents aren't being processed:

1. **Check collection status**:
   ```bash
   rag-cli collections status <collection_id>
   ```

2. **Check system health**:
   ```bash
   rag-cli health check
   ```

3. **View backend logs**:
   ```bash
   docker compose logs backend
   ```

## Next Steps

- [Installation Guide](installation.md) - Detailed setup instructions
- [Authentication](authentication.md) - Configure IBM OIDC authentication
- [Commands Reference](commands/index.md) - Complete command documentation
- [Configuration](configuration.md) - Advanced configuration options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Support

For issues and feature requests, please visit our [GitHub repository](https://github.com/manavgup/rag_modulo/issues).
