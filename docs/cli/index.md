# RAG CLI

The RAG CLI is a command-line interface for interacting with the RAG Modulo system. It provides a comprehensive set of tools for managing collections, documents, search operations, and user authentication through a streamlined command-line experience.

## Overview

RAG CLI enables developers and administrators to:

- **Authenticate** with IBM OIDC providers
- **Manage Collections** - create, list, and configure document collections
- **Upload Documents** - add and process documents for retrieval
- **Execute Searches** - perform semantic search and RAG queries
- **Administer Users** - manage user accounts and permissions

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
   ./rag-cli --help
   ```

2. **Configure connection**:
   ```bash
   ./rag-cli config set-url http://localhost:8000
   ```

3. **Authenticate**:
   ```bash
   ./rag-cli auth login
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
