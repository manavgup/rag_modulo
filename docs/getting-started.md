# 🚀 Quick Start Guide

Get RAG Modulo up and running in minutes with this comprehensive quick start guide.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose V2** - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Python 3.12+** (for local development)
- **Node.js 18+** (for frontend development)
- **Git** - [Install Git](https://git-scm.com/downloads)

## 🐳 Option 1: Docker (Recommended)

The fastest way to get started is using our pre-built Docker images.

### Step 1: Clone the Repository

```bash
git clone https://github.com/manavgup/rag-modulo.git
cd rag-modulo
```

### Step 2: Set Up Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys
nano .env  # or use your preferred editor
```

### Step 3: Start the Application

```bash
# Start with pre-built images (recommended)
make run-ghcr
```

**That's it!** 🎉 The application should now be running.

### Step 4: Verify Installation

Check that all services are running:

```bash
# Check container status
docker compose ps

# View logs
make logs
```

### Access Points

| Service | URL | Description |
|:---:|:---:|:---:|
| **Frontend** | http://localhost:3000 | React web interface |
| **Backend API** | http://localhost:8000 | FastAPI backend |
| **MLFlow** | http://localhost:5001 | Experiment tracking |
| **MinIO Console** | http://localhost:9001 | Object storage |

---

## 🛠️ Option 2: Local Development

For developers who want to build and run locally.

### Step 1: Initialize Development Environment

```bash
# Initialize development environment
make dev-init

# This creates:
# - .env.dev (development configuration)
# - .env (production configuration)
```

### Step 2: Build Local Images

```bash
# Build all development images
make dev-build

# This builds:
# - Backend development image
# - Frontend development image
# - Test image
```

### Step 3: Start Development Environment

```bash
# Start development environment
make dev-up

# Validate everything is working
make dev-validate
```

### Step 4: Development Commands

```bash
# Restart with latest changes
make dev-restart

# View logs
make dev-logs

# Check status
make dev-status

# Stop environment
make dev-down
```

---

## ☁️ Option 3: GitHub Codespaces

Perfect for cloud development without local setup.

### Step 1: Create Codespace

1. **Go to the repository**: https://github.com/manavgup/rag_modulo
2. **Click "Code"** → **"Codespaces"**
3. **Click "Create codespace"** on your branch
4. **Wait for environment** to load (2-3 minutes)

### Step 2: Start Coding

The environment is automatically configured with:
- All dependencies installed
- Development environment ready
- Ports forwarded for testing

### Step 3: Access Services

Services are automatically available at:
- **Frontend**: https://your-codespace-url-3000.preview.app.github.dev
- **Backend**: https://your-codespace-url-8000.preview.app.github.dev

---

## 🔧 Configuration

### Required Environment Variables

Edit your `.env` file with the following required variables:

```bash
# Database Configuration
VECTOR_DB=milvus
MILVUS_HOST=localhost
MILVUS_PORT=19530
DB_HOST=localhost
DB_PORT=5432

# LLM Provider Settings (choose one or more)
WATSONX_INSTANCE_ID=your-instance-id
WATSONX_APIKEY=your-api-key
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key

# Application Settings
EMBEDDING_MODEL=all-minilm-l6-v2
DATA_DIR=/app/data
```

### Optional Configuration

```bash
# Authentication (for production)
IBM_CLIENT_ID=your-client-id
IBM_CLIENT_SECRET=your-client-secret

# Development Mode
DEVELOPMENT_MODE=true
SKIP_AUTH=true
TESTING=true
```

---

## 🧪 Verify Installation

### Health Checks

```bash
# Check all services are healthy
make dev-validate

# Test backend API
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000
```

### Run Tests

```bash
# Run quick tests
make test-atomic

# Run comprehensive tests
make test-all
```

---

## 🎯 First Steps

### 1. Create Your First Collection

```bash
# Using CLI
rag-cli collections create --name "my-first-collection"

# Or using the web interface at http://localhost:3000
```

### 2. Upload Documents

```bash
# Upload a document
rag-cli documents upload --collection-id <collection-id> --file document.pdf

# Or use the web interface
```

### 3. Ask Your First Question

```bash
# Ask a question
rag-cli search query --collection-id <collection-id> --query "What is this document about?"

# Or use the web interface
```

---

## 🔍 Troubleshooting

### Common Issues

<details>
<summary><strong>🐳 Docker Issues</strong></summary>

**Problem**: Services fail to start
```bash
# Check Docker is running
docker --version

# Check service logs
make logs

# Restart services
make stop-containers
make run-services
```
</details>

<details>
<summary><strong>🔐 Authentication Issues</strong></summary>

**Problem**: Login attempts fail
- Ensure OIDC configuration is correct in `.env`
- Check IBM Cloud credentials
- Verify redirect URLs match your setup
</details>

<details>
<summary><strong>🧪 Test Failures</strong></summary>

**Problem**: Tests failing locally
```bash
# Run tests in Docker
make test testfile=tests/unit/test_example.py

# Or use development environment
make dev-test
```
</details>

### Getting Help

1. **📚 Documentation**: Check our [comprehensive docs](../index.md)
2. **🐛 Issues**: [Report bugs](https://github.com/manavgup/rag_modulo/issues)
3. **💬 Discussions**: [Ask questions](https://github.com/manavgup/rag_modulo/discussions)
4. **🔧 Troubleshooting**: [Common issues](troubleshooting/common-issues.md)

---

## 🎉 Next Steps

Now that you have RAG Modulo running, explore these resources:

- **[📚 Full Documentation](../index.md)** - Comprehensive guides
- **[🛠️ Development Guide](development/workflow.md)** - Development best practices
- **[🧪 Testing Guide](testing/index.md)** - Testing strategies
- **[🚀 Deployment Guide](deployment/production.md)** - Production deployment
- **[🖥️ CLI Guide](cli/index.md)** - Command-line interface

---

## 💡 Tips

- **Use Docker**: It's the easiest way to get started
- **Check Logs**: Use `make logs` to debug issues
- **Validate Setup**: Run `make dev-validate` to check everything
- **Start Small**: Begin with simple documents and queries
- **Read Documentation**: Our docs are comprehensive and helpful

---

<div align="center">

**Ready to build amazing RAG applications?** 🚀

[📚 Explore Documentation](../index.md) • [🛠️ Development Guide](development/workflow.md) • [🧪 Testing Guide](testing/index.md)

</div>
