# Quick Start Guide

Get up and running with RAG Modulo in under 5 minutes!

## Prerequisites

- **Docker & Docker Compose**: Required for containerized development
- **Make**: For running development commands
- **Git**: For version control

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo
```

### 2. One-Command Setup

```bash
# Complete development environment setup
make dev-setup
```

This command will:
- ✅ Initialize development environment variables
- ✅ Build all development images
- ✅ Start the development environment
- ✅ Validate everything is working
- ✅ Provide next steps

### 3. Verify Installation

```bash
# Check that everything is running
make dev-status

# Test the API
curl http://localhost:8000/health
```

## Quick Test

### Upload a Document

```bash
# Upload a PDF document
curl -X POST "http://localhost:8000/api/users/files" \
  -H "Authorization: Bearer your-jwt-token" \
  -F "file=@/path/to/your/document.pdf"
```

### Search Documents

```bash
# Search your documents
curl -X POST "http://localhost:8000/api/search" \
  -H "Authorization: Bearer your-jwt-token" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the main topic?",
    "pipeline_id": "your-pipeline-id"
  }'
```

## Next Steps

- **[Development Guide](development/index.md)** - Complete development setup
- **[CLI Documentation](cli/index.md)** - Command-line interface
- **[API Reference](api/README.md)** - REST API documentation
- **[Deployment Guide](deployment/index.md)** - Production deployment

## Troubleshooting

### Common Issues

**Port conflicts:**
```bash
# Check what's using ports
lsof -i :8000
lsof -i :3000

# Stop conflicting services
make dev-down
```

**Docker issues:**
```bash
# Reset development environment
make dev-reset

# Complete cleanup
make clean-all
```

**Environment issues:**
```bash
# Validate setup
make dev-validate

# Check logs
make dev-logs
```

## Getting Help

- **GitHub Issues**: [Report problems](https://github.com/manavgup/rag_modulo/issues)
- **GitHub Discussions**: [Ask questions](https://github.com/manavgup/rag_modulo/discussions)
- **Documentation**: Comprehensive guides in this documentation

---

**Ready to dive deeper?** Check out the [Development Guide](development/index.md) for detailed setup instructions!
