#!/bin/bash
set -e

# =============================================================================
# RAG Modulo Setup Script for Jules (WITH Docker)
# =============================================================================
# This script attempts to set up Docker in Jules environment to run
# infrastructure services locally.
#
# Prerequisites:
# - Docker must be installed in Jules base image
# - User must have permissions to start Docker daemon or access socket
# =============================================================================

echo "🚀 Setting up RAG Modulo with Docker in Jules..."
echo ""

cd /app

# =============================================================================
# Step 1: Check Docker Installation
# =============================================================================

echo "🔍 Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    echo "✅ Docker is installed: $DOCKER_VERSION"
else
    echo "❌ Docker is not installed"
    echo "📦 Attempting to install Docker..."

    # Try to install Docker (may require sudo/elevated permissions)
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo "📦 Installing Docker on Debian/Ubuntu..."
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose
    elif [ -f /etc/redhat-release ]; then
        # RHEL/CentOS/Fedora
        echo "📦 Installing Docker on RHEL/CentOS..."
        sudo yum install -y docker docker-compose
    else
        echo "❌ Unknown Linux distribution. Manual Docker installation required."
        echo "See: https://docs.docker.com/engine/install/"
        exit 1
    fi

    echo "✅ Docker installed"
fi

# =============================================================================
# Step 2: Check Docker Daemon Status
# =============================================================================

echo ""
echo "🔍 Checking Docker daemon status..."

if sudo systemctl is-active --quiet docker 2>/dev/null; then
    echo "✅ Docker daemon is running"
elif sudo service docker status &> /dev/null; then
    echo "✅ Docker daemon is running (via service)"
else
    echo "⚠️  Docker daemon is not running"
    echo "🔄 Attempting to start Docker daemon..."

    # Try systemctl first, then service
    if command -v systemctl &> /dev/null; then
        sudo systemctl start docker
        sudo systemctl enable docker
    elif command -v service &> /dev/null; then
        sudo service docker start
    else
        echo "❌ Unable to start Docker daemon"
        echo "💡 Try manually: sudo dockerd &"
        exit 1
    fi

    echo "✅ Docker daemon started"
fi

# =============================================================================
# Step 3: Docker Hub Authentication (avoid rate limits)
# =============================================================================

echo ""
echo "🔐 Authenticating with Docker Hub..."

if [ -n "$DOCKER_HUB_USERNAME" ] && [ -n "$DOCKER_HUB_TOKEN" ]; then
    echo "Docker Hub credentials found in environment"
    echo "$DOCKER_HUB_TOKEN" | docker login -u "$DOCKER_HUB_USERNAME" --password-stdin

    if [ $? -eq 0 ]; then
        echo "✅ Docker Hub authentication successful"
    else
        echo "⚠️  Docker Hub authentication failed, continuing with anonymous pulls"
        echo "    Note: You may hit rate limits (100 pulls per 6 hours)"
    fi
else
    echo "⚠️  Docker Hub credentials not found in environment"
    echo "    Continuing with anonymous pulls (rate limited to 100/6hrs)"
    echo "    To avoid rate limits, set DOCKER_HUB_USERNAME and DOCKER_HUB_TOKEN"
fi

# =============================================================================
# Step 4: Fix Docker Socket Permissions
# =============================================================================

echo ""
echo "🔐 Configuring Docker permissions..."

# Check if docker group exists
if ! getent group docker > /dev/null 2>&1; then
    echo "Creating docker group..."
    sudo groupadd docker
fi

# Add current user to docker group
CURRENT_USER=$(whoami)
if ! groups $CURRENT_USER | grep -q docker; then
    echo "Adding $CURRENT_USER to docker group..."
    sudo usermod -aG docker $CURRENT_USER
    echo "✅ User added to docker group"
    echo "⚠️  You may need to log out and back in for group membership to take effect"
else
    echo "✅ User already in docker group"
fi

# Fix socket permissions
if [ -S /var/run/docker.sock ]; then
    echo "Setting Docker socket permissions..."
    sudo chmod 666 /var/run/docker.sock
    echo "✅ Docker socket permissions configured"
fi

# =============================================================================
# Step 5: Verify Docker Works
# =============================================================================

echo ""
echo "🧪 Testing Docker..."

if docker ps &> /dev/null; then
    echo "✅ Docker is working!"
else
    echo "⚠️  Docker test failed. Trying with sudo..."
    if sudo docker ps &> /dev/null; then
        echo "⚠️  Docker works with sudo, but not without"
        echo "💡 You may need to run 'newgrp docker' or restart your session"
        echo "💡 For now, Docker commands may require sudo"
    else
        echo "❌ Docker is not working even with sudo"
        echo "Please check Docker installation manually"
        exit 1
    fi
fi

# =============================================================================
# Step 6: Install Application Dependencies
# =============================================================================

echo ""
echo "📦 Installing application dependencies..."

# Check if .env exists
if [ ! -f .env ]; then
    echo "📝 Creating .env from template..."
    cp env.example .env
    echo "✅ .env created"
else
    echo "ℹ️  .env already exists, skipping..."
fi

# Install dependencies
make local-dev-setup

# =============================================================================
# Step 7: Create Volume Directories (for bind mounts)
# =============================================================================

echo ""
echo "📁 Creating volume directories for data persistence..."

# Create directories for Docker volume bind mounts
mkdir -p volumes/postgres
mkdir -p volumes/milvus
mkdir -p volumes/etcd
mkdir -p volumes/minio
mkdir -p volumes/mlflow

# Set permissions (ensure Docker can write to them)
chmod -R 777 volumes/

echo "✅ Volume directories created"

# =============================================================================
# Step 8: Start Infrastructure with Docker Compose
# =============================================================================

echo ""
echo "🐳 Starting infrastructure services with Docker Compose..."

# Try to start infrastructure
if docker compose version &> /dev/null; then
    # Docker Compose V2
    docker compose -f docker-compose-infra.yml up -d
elif docker-compose --version &> /dev/null; then
    # Docker Compose V1
    docker-compose -f docker-compose-infra.yml up -d
else
    echo "❌ Docker Compose not found"
    echo "💡 Try: sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo ""
echo "✅ Infrastructure services started!"
echo ""

# =============================================================================
# Success Message
# =============================================================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ RAG Modulo Setup Complete (with Docker)!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📋 Infrastructure Services Running:"
echo "   - PostgreSQL: localhost:5432"
echo "   - Milvus: localhost:19530"
echo "   - MinIO: localhost:9001"
echo "   - MLFlow: localhost:5001"
echo ""
echo "📋 Next Steps:"
echo "   1. Configure .env with your API keys (WatsonX, OpenAI)"
echo "   2. Start backend:  make local-dev-backend"
echo "   3. Start frontend: make local-dev-frontend"
echo ""
echo "📋 Check Status:"
echo "   docker compose -f docker-compose-infra.yml ps"
echo "   make local-dev-status"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
