# RAG Modulo Documentation

Welcome to the comprehensive documentation for **RAG Modulo** - an AI-powered document processing and search platform that combines advanced retrieval-augmented generation (RAG) capabilities with modern web technologies.

## 🚀 Quick Start

Get up and running with RAG Modulo in minutes:

```bash
# Clone the repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# One-command development setup
make dev-setup

# Start coding!
```

## 📖 What is RAG Modulo?

RAG Modulo is a comprehensive platform that enables:

- **Document Processing**: Upload and process various document formats (PDF, DOCX, TXT, etc.)
- **Intelligent Search**: AI-powered semantic search across your document collection
- **Vector Storage**: Efficient storage and retrieval using Milvus vector database
- **AI Integration**: Seamless integration with IBM WatsonX for embeddings and AI capabilities
- **Modern CLI**: Command-line interface for automation and scripting
- **Web Interface**: User-friendly web application for document management

## 🏗️ Architecture

RAG Modulo is built with modern, scalable technologies:

- **Backend**: FastAPI (Python) with Pydantic 2.0
- **Frontend**: React with modern JavaScript/TypeScript
- **Database**: PostgreSQL for metadata storage
- **Vector Database**: Milvus for semantic search
- **AI Services**: IBM WatsonX for embeddings and AI capabilities
- **Storage**: MinIO for object storage
- **Containerization**: Docker and Docker Compose

## 🛠️ Development

### For Developers

- **[Development Guide](development/README.md)** - Complete development setup and workflow
- **[Environment Setup](development/environment-setup.md)** - Detailed environment configuration
- **[Contributing Guidelines](development/contributing.md)** - How to contribute to the project
- **[Development Workflow](DEVELOPMENT_WORKFLOW.md)** - Streamlined development process

### Key Features

- ✅ **Hot Reloading**: Changes reflect immediately
- ✅ **File Watching**: Auto-rebuild on file changes
- ✅ **Debug Mode**: Enhanced debugging capabilities
- ✅ **Test Mode**: Isolated test environment
- ✅ **Profiling**: Performance monitoring
- ✅ **VS Code Integration**: Complete dev container support

## 🚀 Deployment

### For DevOps Engineers

- **[Deployment Guide](deployment/README.md)** - Comprehensive deployment instructions
- **[Production Deployment](deployment/production.md)** - Production-ready configuration
- **[Cloud Deployment](deployment/cloud.md)** - AWS, GCP, Azure deployment guides
- **[Monitoring](deployment/monitoring.md)** - Monitoring and observability setup

### Deployment Options

- **Local Development**: Docker Compose with hot reload
- **Production**: Optimized containers with security hardening
- **Cloud Platforms**: Kubernetes, Docker Swarm, cloud services
- **CI/CD Integration**: Automated deployment pipelines

## 🖥️ CLI

### Command Line Interface

- **[CLI Overview](cli/index.md)** - Introduction to the CLI
- **[Installation](cli/installation.md)** - CLI installation guide
- **[Authentication](cli/authentication.md)** - Authentication setup
- **[Commands](cli/commands/index.md)** - Available CLI commands
- **[Configuration](cli/configuration.md)** - CLI configuration options

### CLI Features

- **Multi-entry Points**: `rag-cli`, `rag-search`, `rag-admin`
- **Rich Output**: Formatted console output with colors and tables
- **Configuration Management**: Profile-based configuration
- **Authentication**: JWT-based authentication with IBM OIDC
- **API Integration**: Full integration with backend API routes

## 📚 API Reference

### REST API Documentation

- **[API Overview](api/README.md)** - Introduction to the API
- **[Authentication](api/authentication.md)** - API authentication methods
- **[Endpoints](api/endpoints.md)** - Complete API endpoint reference
- **[Schemas](api/schemas.md)** - Request/response schemas

### API Features

- **RESTful Design**: Standard REST API patterns
- **OpenAPI Documentation**: Interactive API documentation
- **Authentication**: JWT-based authentication
- **Rate Limiting**: Built-in rate limiting
- **Error Handling**: Comprehensive error responses

## 🧪 Testing

### Testing Strategy

- **[Test Overview](tests/README.md)** - Testing philosophy and strategy
- **[Running Tests](tests/running.md)** - How to run tests
- **[Test Data](tests/data.md)** - Test data management
- **[CI/CD Testing](tests/ci-cd.md)** - Continuous integration testing

### Test Types

- **Atomic Tests**: Fast, isolated unit tests (70%)
- **Unit Tests**: Component-level testing (20%)
- **Integration Tests**: Service integration testing (8%)
- **End-to-End Tests**: Full workflow testing (2%)

## 🔧 Troubleshooting

### Common Issues

- **[Common Issues](troubleshooting.md)** - Frequently encountered problems
- **[Debugging Guide](debugging.md)** - Debugging techniques and tools
- **[Performance Issues](performance.md)** - Performance optimization guide

## 📖 Additional Resources

- **[Changelog](changelog.md)** - Version history and changes
- **[FAQ](faq.md)** - Frequently asked questions
- **[Glossary](glossary.md)** - Technical terms and definitions
- **[Contributing](CONTRIBUTING.md)** - How to contribute to the project

## 🎯 Getting Help

### Support Channels

- **GitHub Issues**: [Report bugs and request features](https://github.com/manavgup/rag_modulo/issues)
- **GitHub Discussions**: [Ask questions and share ideas](https://github.com/manavgup/rag_modulo/discussions)
- **Documentation**: This comprehensive documentation
- **Code Examples**: Check the repository for usage examples

### Community

- **Contributors**: See [CONTRIBUTORS.md](CONTRIBUTORS.md) for all contributors
- **License**: MIT License - see [LICENSE](LICENSE) for details
- **Code of Conduct**: See [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

## 🚀 Quick Commands

### Development

```bash
# Complete development setup
make dev-setup

# Start development environment
make dev-up

# Run tests
make test

# Check code quality
make lint

# View logs
make dev-logs
```

### Deployment

```bash
# Build production images
make build-all

# Deploy to production
make run-services

# Health check
make health-check

# View status
make status
```

---

**Ready to get started?** Check out the [Quick Start Guide](getting-started.md) or dive into the [Development Guide](development/README.md)!
