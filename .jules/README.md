# Jules Configuration Files

This directory contains configuration files for setting up RAG Modulo in Google Jules.

## 📁 Files

### Configuration Files
- **`config.yaml`** - Default: Remote infrastructure (no Docker)
- **`config-with-docker.yaml`** - Alternative: Docker installation + local infrastructure
- **`README.md`** - This file

### Setup Scripts
- **`setup.sh`** - Installs dependencies only (no Docker)
- **`setup-with-docker.sh`** - Installs Docker + dependencies + starts services

### Documentation
- **`DOCKER_SETUP.md`** - Complete guide for Docker installation in Jules

## 🎯 Which Configuration Should I Use?

| Factor | Remote Infrastructure<br/>(`config.yaml`) | Docker in Jules<br/>(`config-with-docker.yaml`) |
|--------|-------------------------------------------|------------------------------------------------|
| **Setup Complexity** | ⭐⭐⭐ Simple | ⭐⭐⭐⭐⭐ Complex |
| **Setup Time** | 15-30 minutes | 30-60 minutes |
| **Requires** | External services | sudo/root access |
| **Resource Usage** | Low (app only) | High (2-3 GB RAM) |
| **Ongoing Cost** | $0-10/month | $0 |
| **Best For** | Most users | Air-gapped environments |

**Recommended**: Start with **`config.yaml`** (remote infrastructure). Try Docker only if needed.

## 🚀 Setup Instructions

### Option A: Remote Infrastructure (Recommended)

**Best for**: Most users, quick setup, lower resource usage

1. Visit: `https://jules.google.com/repo/github/manavgup/rag_modulo/config`

2. Copy the contents of **`config.yaml`** into the Jules configuration editor

3. Jules will automatically:
   - ✅ Clone repository
   - ✅ Install Poetry dependencies (backend)
   - ✅ Install npm dependencies (frontend)
   - ✅ Create `.env` from `env.jules.example`
   - ❌ NOT install Docker
   - ❌ NOT start services

4. **You must set up remote infrastructure**:
   - Sign up for: Supabase (Postgres), Pinecone (Vector DB), Backblaze B2 (Storage)
   - See: `/app/JULES_SETUP.md` for detailed guide

5. **Configure and start**:
   ```bash
   # Edit .env with remote service URLs
   nano /app/.env

   # Verify connections
   make verify-remote-connections

   # Start services
   make local-dev-backend    # Terminal 1
   make local-dev-frontend   # Terminal 2
   ```

### Option B: Docker Installation (Advanced)

**Best for**: Advanced users, air-gapped environments, full local control

**Requirements**:
- ✅ Jules environment with sudo/root access
- ✅ Sufficient resources (4+ cores, 8+ GB RAM, 20+ GB disk)
- ✅ SystemD or similar init system

**Setup**:

1. Visit: `https://jules.google.com/repo/github/manavgup/rag_modulo/config`

2. Copy the contents of **`config-with-docker.yaml`** into the Jules configuration editor

3. Jules will automatically:
   - ✅ Install Docker (if not present)
   - ✅ Start Docker daemon
   - ✅ Configure permissions (add user to docker group)
   - ✅ Install application dependencies
   - ✅ Start infrastructure services (Postgres, Milvus, MinIO, MLFlow)

4. **Configure API keys and start**:
   ```bash
   # Edit .env (infrastructure already running)
   nano /app/.env
   # Only need to add: WATSONX_APIKEY, WATSONX_INSTANCE_ID

   # Check infrastructure
   docker compose -f docker-compose-infra.yml ps

   # Start services
   make local-dev-backend    # Terminal 1
   make local-dev-frontend   # Terminal 2
   ```

## 📊 Detailed Comparison

### Remote Infrastructure Approach

**Pros:**
- ✅ Simple setup (no Docker complexity)
- ✅ Lower resource usage in Jules
- ✅ Managed services (automatic backups, scaling)
- ✅ Works in restricted environments

**Cons:**
- ❌ Requires external services
- ❌ Potential network latency
- ❌ Ongoing costs (though free tiers available)

**Services You'll Need:**
1. **PostgreSQL**: Supabase (free tier: 500MB)
2. **Vector DB**: Pinecone (free tier: 1 index, 5M vectors)
3. **Object Storage**: Backblaze B2 (free tier: 10GB)
4. **WatsonX**: IBM Cloud (for AI features)

**Total Monthly Cost**: $0 (within free tiers)

### Docker Installation Approach

**Pros:**
- ✅ Full local control
- ✅ No external dependencies
- ✅ No ongoing costs
- ✅ Works offline/air-gapped

**Cons:**
- ❌ Complex setup (Docker installation)
- ❌ Requires sudo/root access
- ❌ High resource usage (2-3 GB RAM)
- ❌ May not work in all Jules environments

**Resource Requirements:**
- **CPU**: 4 cores minimum
- **RAM**: 8 GB minimum
- **Disk**: 20 GB free space
- **Network**: Docker Hub access (for images)

## 🆘 Troubleshooting

### Remote Infrastructure Issues

**"Connection refused" errors**
```bash
# Check .env configuration
cat /app/.env | grep -E "POSTGRES|MILVUS|MINIO"

# Test connections
make verify-remote-connections

# Check if services are accessible
curl -v your-postgres-host:5432
```

**"Module not found" errors**
```bash
# Re-install dependencies
make local-dev-setup
```

### Docker Installation Issues

**"Permission denied (Docker socket)"**
```bash
# Quick fix (temporary)
sudo chmod 666 /var/run/docker.sock

# Proper fix (permanent)
sudo usermod -aG docker $USER
newgrp docker
```

**Docker daemon not running**
```bash
# Start daemon
sudo systemctl start docker

# Check status
sudo systemctl status docker

# View logs
sudo journalctl -u docker
```

**Out of disk space**
```bash
# Clean up Docker
docker system prune -a --volumes -f

# Check disk usage
docker system df
df -h
```

**For more troubleshooting**, see:
- Docker issues: `/app/.jules/DOCKER_SETUP.md#-troubleshooting-docker-in-jules`
- Remote issues: `/app/docs/deployment/jules-setup.md#-common-issues--solutions`

## 📝 Configuration Checklist

### Remote Infrastructure Setup
- [ ] Sign up for Supabase (Postgres)
- [ ] Sign up for Pinecone (Vector DB)
- [ ] Sign up for Backblaze B2 (Storage)
- [ ] Get IBM WatsonX API key
- [ ] Edit `/app/.env` with connection details
- [ ] Run `make verify-remote-connections`
- [ ] Start backend: `make local-dev-backend`
- [ ] Start frontend: `make local-dev-frontend`

### Docker Installation Setup
- [ ] Verify Jules has sudo access
- [ ] Check available resources (8GB+ RAM)
- [ ] Copy `config-with-docker.yaml` to Jules config
- [ ] Wait for setup to complete
- [ ] Verify Docker is running: `docker ps`
- [ ] Check infrastructure: `docker compose -f docker-compose-infra.yml ps`
- [ ] Edit `/app/.env` with WatsonX API key
- [ ] Start backend: `make local-dev-backend`
- [ ] Start frontend: `make local-dev-frontend`

## 📚 Documentation

- **Quick Start (Remote)**: `/app/JULES_SETUP.md`
- **Docker Setup Guide**: `/app/.jules/DOCKER_SETUP.md`
- **Full Deployment Guide**: `/app/docs/deployment/jules-setup.md`
- **Main README**: `/app/README.md`
- **API Documentation**: http://localhost:8000/docs (after backend starts)

## 💡 Tips & Best Practices

1. **Start Simple**: Use remote infrastructure (`config.yaml`) first
2. **Use Pinecone**: Easier than Milvus for cloud setups
3. **Verify Connections**: Always run `make verify-remote-connections` before starting
4. **Check Logs**: Use `tail -f /tmp/rag-backend.log` to debug backend issues
5. **Resource Monitoring**: Use `htop` or `docker stats` to monitor resource usage
6. **Security**: Never commit `.env` files with real credentials

## 🔗 Useful Links

- **Jules Documentation**: https://jules.google/docs/environment/
- **Project Repository**: https://github.com/manavgup/rag_modulo
- **Issue Tracker**: https://github.com/manavgup/rag_modulo/issues
- **Supabase**: https://supabase.com
- **Pinecone**: https://pinecone.io
- **Backblaze B2**: https://www.backblaze.com/b2
- **Docker Docs**: https://docs.docker.com/engine/install/

## 🤝 Getting Help

If you encounter issues:

1. Check the appropriate troubleshooting guide (above)
2. Review [GitHub Issues](https://github.com/manavgup/rag_modulo/issues)
3. Check [Jules Documentation](https://jules.google/docs/environment/)
4. Ask in project discussions
