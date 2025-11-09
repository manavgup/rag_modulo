# Frequently Asked Questions (FAQ)

## General

### What is RAG Modulo?

RAG Modulo is a production-ready Retrieval-Augmented Generation platform that provides enterprise-grade document processing, intelligent search, and AI-powered question answering with advanced Chain of Thought (CoT) reasoning.

### What LLM providers are supported?

- WatsonX (IBM)
- OpenAI
- Anthropic

See [API Documentation](api/index.md) for configuration details.

### What vector databases are supported?

- Milvus (default)
- Elasticsearch
- Pinecone
- Weaviate
- ChromaDB

See [Getting Started](getting-started.md) for setup instructions.

## Installation & Setup

### How do I install RAG Modulo?

See the [Installation Guide](installation.md) for detailed instructions.

### What are the system requirements?

- Python 3.12+
- Docker & Docker Compose
- PostgreSQL
- Vector database (Milvus recommended)

See [Installation](installation.md) for full requirements.

### How do I run locally without Docker?

Use the local development mode:
```bash
make local-dev-setup
make local-dev-infra
make local-dev-backend
make local-dev-frontend
```

See [Development Workflow](development/workflow.md) for details.

## Usage

### How do I upload documents?

Documents can be uploaded via:
- Web interface (drag & drop)
- CLI: `rag-cli documents upload`
- REST API: `POST /api/documents`

See [Getting Started](getting-started.md#uploading-documents).

### What document formats are supported?

- PDF
- Word (DOCX)
- Text (TXT, MD)
- HTML
- CSV/Excel (via IBM Docling)
- Images (with OCR via Docling)

### How does Chain of Thought reasoning work?

CoT reasoning breaks complex questions into smaller sub-questions, answers each step, and synthesizes a comprehensive final answer with source attribution.

See [Chain of Thought Guide](features/chain-of-thought/index.md).

## Development

### How do I run tests?

```bash
make test-atomic      # Fast schema tests (~5 sec)
make test-unit-fast   # Unit tests (~30 sec)
make test-integration # Integration tests (~2 min)
make test-all         # All tests
```

See [Testing Guide](testing/index.md).

### How do I contribute?

See the [Contributing Guide](contributing.md).

### Where are the development docs?

- [Development Workflow](development/workflow.md)
- [Code Quality Standards](development/code-quality-standards.md)
- [Architecture](architecture/index.md)

## Troubleshooting

### Common issues?

See [Troubleshooting Guide](troubleshooting/common-issues.md).

### Where can I get help?

- Review [Troubleshooting](troubleshooting/common-issues.md)
- Check [GitHub Issues](https://github.com/manavgup/rag_modulo/issues)
- See [Development Docs](development/index.md)

## Performance

### How many tests does the project have?

947+ automated tests covering unit, integration, and end-to-end scenarios.

### What's the test coverage?

Minimum 60% coverage required. See [Testing Guide](testing/index.md).

### How fast are CI/CD pipelines?

~2-3 minutes for typical PRs after optimization (was ~15 min before).

See [CI/CD Documentation](development/ci-cd-security.md).
