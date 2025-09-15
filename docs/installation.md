# Installation Guide

This guide covers installing RAG Modulo on different platforms and environments.

## System Requirements

### Minimum Requirements

- **CPU**: 4+ cores
- **RAM**: 8GB minimum, 16GB recommended
- **Storage**: 50GB+ available space
- **OS**: macOS 10.15+, Ubuntu 20.04+, Windows 10+ with WSL2

### Required Software

- **Docker**: Version 20.10+ with Docker Compose 2.0+
- **Make**: For running development commands
- **Git**: Version 2.30+ for version control

## Installation Methods

### Method 1: Development Installation (Recommended)

```bash
# Clone repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo

# One-command setup
make dev-setup
```

### Method 2: Manual Installation

#### 1. Install Prerequisites

**macOS:**
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install Make
brew install make
```

**Ubuntu/Debian:**
```bash
# Update package list
sudo apt update

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Make
sudo apt install make
```

**Windows:**
```bash
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
# Install Git from https://git-scm.com/download/win
# Install Make via Chocolatey: choco install make
```

#### 2. Clone Repository

```bash
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo
```

#### 3. Initialize Environment

```bash
# Create environment files
make dev-init

# Edit .env.dev with your credentials
nano .env.dev
```

#### 4. Build and Start

```bash
# Build development images
make dev-build

# Start development environment
make dev-up

# Verify installation
make dev-validate
```

## Configuration

### Environment Variables

Edit `.env.dev` with your configuration:

```bash
# Development Environment Configuration
TESTING=true
SKIP_AUTH=true
DEVELOPMENT_MODE=true

# IBM WatsonX Credentials (required)
WATSONX_INSTANCE_ID=your-watsonx-instance-id
WATSONX_APIKEY=your-watsonx-api-key
WATSONX_URL=https://us-south.ml.cloud.ibm.com

# Development JWT Secret
JWT_SECRET_KEY=dev-jwt-secret-key-for-local-development-only

# Database Configuration
COLLECTIONDB_NAME=rag_modulo
COLLECTIONDB_USER=rag_user
COLLECTIONDB_PASS=rag_password
```

### IBM WatsonX Setup

1. **Create IBM Cloud Account**: Sign up at [IBM Cloud](https://cloud.ibm.com)
2. **Create WatsonX Instance**: Follow IBM's documentation
3. **Get Credentials**: Copy your instance ID, API key, and URL
4. **Update Configuration**: Add credentials to `.env.dev`

## Verification

### Health Checks

```bash
# Check all services
make dev-status

# Test backend health
curl http://localhost:8000/health

# Test frontend
curl http://localhost:3000

# Test MLflow
curl http://localhost:5001
```

### Service URLs

- **Backend API**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **MLflow**: http://localhost:5001
- **PostgreSQL**: localhost:5432
- **Milvus**: localhost:19530
- **MinIO**: http://localhost:9000

## Troubleshooting

### Common Issues

#### Docker Not Running

```bash
# Start Docker Desktop
# On macOS: Open Docker Desktop application
# On Linux: sudo systemctl start docker
# On Windows: Start Docker Desktop

# Verify Docker is running
docker --version
docker compose --version
```

#### Port Conflicts

```bash
# Check what's using ports
lsof -i :8000  # Backend
lsof -i :3000  # Frontend
lsof -i :5001  # MLflow

# Stop conflicting services
make dev-down
```

#### Permission Issues

```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
# Log out and log back in

# Fix volume permissions
sudo chown -R $USER:$USER volumes/
```

#### Build Failures

```bash
# Clean build cache
docker builder prune -f

# Rebuild from scratch
make clean-all
make dev-build
```

### Getting Help

- **Check logs**: `make dev-logs`
- **Validate setup**: `make dev-validate`
- **Reset environment**: `make dev-reset`
- **GitHub Issues**: Create an issue for persistent problems

## Next Steps

After successful installation:

1. **[Development Guide](development/index.md)** - Learn the development workflow
2. **[CLI Documentation](cli/index.md)** - Explore the command-line interface
3. **[API Reference](api/README.md)** - Understand the REST API
4. **[Deployment Guide](deployment/index.md)** - Deploy to production

## Uninstallation

### Complete Removal

```bash
# Stop all services
make dev-down

# Remove all containers, volumes, and images
make clean-all

# Remove repository
cd ..
rm -rf rag_modulo
```

### Partial Removal

```bash
# Stop services only
make dev-down

# Remove containers only
docker compose -f docker-compose.dev.yml down

# Remove images only
docker rmi $(docker images "rag-modulo*" -q)
```

---

**Installation complete!** Check out the [Quick Start Guide](getting-started.md) to begin using RAG Modulo.
