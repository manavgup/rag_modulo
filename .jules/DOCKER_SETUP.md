# Installing Docker in Jules Environment

This guide explains how to install and configure Docker in Jules to run RAG Modulo with local infrastructure services.

## 🎯 Two Approaches Available

| Approach | Pros | Cons | Recommended For |
|----------|------|------|-----------------|
| **Remote Infrastructure** | No Docker needed, faster setup, lower resource usage | Requires external services, ongoing costs | Most users |
| **Docker in Jules** | Full local control, no external dependencies | Requires elevated permissions, more complex setup | Advanced users, air-gapped environments |

## 🐳 Docker Installation in Jules

### Prerequisites

Jules environment must support:
- ✅ Root/sudo access
- ✅ SystemD or init system for daemon management
- ✅ Ability to modify user groups
- ✅ Persistent storage for Docker volumes

### Option 1: Using the Automated Script

Update your Jules config to use the Docker setup script:

```yaml
# Jules Configuration with Docker
setup:
  script: .jules/setup-with-docker.sh

environment:
  JULES_ENVIRONMENT: "true"
  DEVELOPMENT_MODE: "true"
```

The script will:
1. ✅ Check if Docker is installed
2. ✅ Install Docker if missing (requires sudo)
3. ✅ Start Docker daemon
4. ✅ Configure permissions (add user to docker group)
5. ✅ Test Docker functionality
6. ✅ Install application dependencies
7. ✅ Start infrastructure services with Docker Compose

### Option 2: Manual Installation

If the automated script fails, follow these manual steps:

#### Step 1: Install Docker

**For Debian/Ubuntu:**
```bash
# Update package index
sudo apt-get update

# Install Docker
sudo apt-get install -y docker.io docker-compose-plugin

# Verify installation
docker --version
docker compose version
```

**For RHEL/CentOS/Fedora:**
```bash
# Install Docker
sudo yum install -y docker docker-compose

# Verify installation
docker --version
docker-compose --version
```

#### Step 2: Start Docker Daemon

```bash
# Start Docker service
sudo systemctl start docker

# Enable Docker to start on boot
sudo systemctl enable docker

# Verify Docker is running
sudo systemctl status docker
```

#### Step 3: Configure Permissions

```bash
# Create docker group (if it doesn't exist)
sudo groupadd docker

# Add your user to docker group
sudo usermod -aG docker $USER

# Apply new group membership (alternative to logging out)
newgrp docker

# Fix socket permissions (temporary - until logout)
sudo chmod 666 /var/run/docker.sock

# Test Docker without sudo
docker ps
```

**⚠️ Important**: You may need to log out and back in for group membership to fully take effect.

#### Step 4: Install Application

```bash
cd /app

# Copy environment template
cp env.example .env

# Install dependencies
make local-dev-setup

# Start infrastructure
docker compose -f docker-compose-infra.yml up -d

# Verify services are running
docker compose -f docker-compose-infra.yml ps
```

#### Step 5: Start Application

```bash
# Terminal 1: Start backend
make local-dev-backend

# Terminal 2: Start frontend
make local-dev-frontend
```

## 🔍 Troubleshooting Docker in Jules

### Issue 1: "permission denied while trying to connect to the Docker daemon socket"

**Symptoms:**
```
Got permission denied while trying to connect to the Docker daemon socket
at unix:///var/run/docker.sock
```

**Solutions:**

**A. Quick Fix (Temporary)**
```bash
# Fix socket permissions (resets on reboot)
sudo chmod 666 /var/run/docker.sock
```

**B. Proper Fix (Permanent)**
```bash
# Add user to docker group
sudo usermod -aG docker $USER

# Apply group membership
newgrp docker

# Or log out and back in
```

**C. Use sudo (Not Recommended)**
```bash
# Run Docker commands with sudo
sudo docker compose -f docker-compose-infra.yml up -d
```

### Issue 2: Docker daemon not running

**Symptoms:**
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock.
Is the docker daemon running?
```

**Solutions:**

```bash
# Check if Docker is installed
docker --version

# Check daemon status
sudo systemctl status docker

# Start daemon
sudo systemctl start docker

# Enable daemon to start on boot
sudo systemctl enable docker

# If systemctl not available, try:
sudo service docker start
```

### Issue 3: Docker Compose not found

**Symptoms:**
```
docker: 'compose' is not a docker command.
```

**Solutions:**

**Option A: Install Docker Compose V2 Plugin**
```bash
sudo apt-get install docker-compose-plugin
docker compose version
```

**Option B: Install Docker Compose V1 (Standalone)**
```bash
sudo apt-get install docker-compose
docker-compose --version

# Update Makefile to use V1 syntax
# Change: docker compose -> docker-compose
```

**Option C: Download Binary Directly**
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
docker-compose --version
```

### Issue 4: Out of disk space

**Symptoms:**
```
no space left on device
```

**Solutions:**

```bash
# Check Docker disk usage
docker system df

# Clean up unused containers
docker container prune -f

# Clean up unused images
docker image prune -a -f

# Clean up volumes (⚠️ destroys data)
docker volume prune -f

# Full cleanup (⚠️ destroys everything)
docker system prune -a --volumes -f
```

### Issue 5: Port conflicts

**Symptoms:**
```
bind: address already in use
```

**Solutions:**

```bash
# Check what's using the port
sudo lsof -i :19530  # Example: Milvus port
sudo netstat -tulpn | grep :5432  # Example: Postgres port

# Kill the process
sudo kill -9 <PID>

# Or change ports in docker-compose-infra.yml
```

### Issue 6: Memory issues / Services crashing

**Symptoms:**
```
Killed
Out of memory
```

**Solutions:**

```bash
# Check available memory
free -h

# Reduce resource usage - edit docker-compose-infra.yml:
services:
  milvus-standalone:
    mem_limit: 2g  # Reduce from default

  postgres:
    mem_limit: 512m
```

## 🔧 Resource Requirements

### Minimum Requirements (Limited Functionality)
- **CPU**: 2 cores
- **RAM**: 4 GB
- **Disk**: 10 GB free space

### Recommended (Full Functionality)
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Disk**: 20 GB free space

### Infrastructure Service Resources
- **PostgreSQL**: ~100 MB RAM
- **Milvus**: ~1-2 GB RAM
- **MinIO**: ~100 MB RAM
- **MLFlow**: ~200 MB RAM
- **Total**: ~2-3 GB RAM minimum

## 📊 Comparison: Docker vs Remote Infrastructure

| Factor | Docker in Jules | Remote Infrastructure |
|--------|-----------------|----------------------|
| **Setup Complexity** | Medium-High | Low |
| **Initial Setup Time** | 30-60 minutes | 15-30 minutes |
| **Resource Usage** | 2-3 GB RAM, 10+ GB disk | Minimal (app only) |
| **Ongoing Costs** | None | $0-10/month |
| **Network Latency** | Lowest (localhost) | Higher (internet) |
| **Maintenance** | Your responsibility | Managed service |
| **Scalability** | Limited to VM size | Automatic |
| **Best For** | Air-gapped, full control | Cloud-native, quick setup |

## 💡 Recommendations

### Use Docker in Jules If:
- ✅ You have sudo/root access
- ✅ Jules environment has sufficient resources (8GB+ RAM)
- ✅ You need air-gapped/offline development
- ✅ You want full control over infrastructure
- ✅ You're comfortable with Docker administration

### Use Remote Infrastructure If:
- ✅ You don't have sudo/root access
- ✅ Jules environment is resource-constrained
- ✅ You want faster setup with less complexity
- ✅ You're OK with managed services
- ✅ You want to minimize local resource usage

**Default Recommendation**: Start with **Remote Infrastructure** (see `JULES_SETUP.md`). If you encounter issues or need full local control, then try Docker installation.

## 🚀 Quick Start (Docker Approach)

```bash
# 1. Update Jules config to use Docker setup script
# Edit: https://jules.google.com/repo/github/manavgup/rag_modulo/config

setup:
  script: .jules/setup-with-docker.sh

# 2. Jules will automatically:
#    - Install Docker (if needed)
#    - Start Docker daemon
#    - Configure permissions
#    - Start infrastructure services
#    - Install application dependencies

# 3. After setup completes:
cd /app

# Configure .env with your API keys
nano .env

# Start backend
make local-dev-backend

# Start frontend (new terminal)
make local-dev-frontend
```

## 📚 Additional Resources

- [Docker Installation Guide](https://docs.docker.com/engine/install/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [Docker Post-Installation Steps](https://docs.docker.com/engine/install/linux-postinstall/)
- [Jules Documentation](https://jules.google/docs/environment/)
- [RAG Modulo Docker Compose Files](../docker-compose-infra.yml)

## 🆘 Still Having Issues?

If Docker installation continues to fail:

1. **Try Remote Infrastructure Instead**: See `JULES_SETUP.md` for a simpler approach
2. **Check Jules Permissions**: Ensure your Jules environment supports Docker
3. **Contact Jules Support**: Verify Docker is supported in your Jules instance
4. **Manual VM Setup**: Consider deploying infrastructure on a separate VM

## 🔐 Security Considerations

**⚠️ Warning**: Adding users to the `docker` group grants root-equivalent privileges.

```bash
# Users in docker group can:
docker run -v /:/host -it ubuntu chroot /host

# This gives full root access to the host system!
```

**Recommendations:**
- Only add trusted users to docker group
- In production, use rootless Docker mode
- Consider using Podman as Docker alternative (rootless by default)
- For Jules, this may be acceptable in isolated development environments
