# RAG CLI

The RAG CLI is a comprehensive command-line interface for interacting with the RAG Modulo system. It provides a complete set of tools for managing collections, documents, search operations, user authentication, LLM providers, and pipelines through a streamlined command-line experience.

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
- Valid IBM OIDC credentials
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

2. **Authenticate**:
   ```bash
   rag-cli auth login
   ```

3. **Create a collection**:
   ```bash
   rag-cli collections create "My Documents" --description "Personal collection"
   ```

4. **Upload a document**:
   ```bash
   rag-cli documents upload /path/to/document.pdf --collection <collection-id>
   ```

5. **Search your collection**:
   ```bash
   rag-cli search query "What is machine learning?" --collection <collection-id>
   ```

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

## Next Steps

- [Installation Guide](installation.md) - Detailed setup instructions
- [Authentication](authentication.md) - Configure IBM OIDC authentication
- [Commands Reference](commands/index.md) - Complete command documentation
- [Configuration](configuration.md) - Advanced configuration options
- [Troubleshooting](troubleshooting.md) - Common issues and solutions

## Support

For issues and feature requests, please visit our [GitHub repository](https://github.com/manavgup/rag_modulo/issues).
