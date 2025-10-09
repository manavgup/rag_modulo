# 🚀 Jules Setup Quick Start

> **Setting up RAG Modulo in Jules - Two Approaches Available**

## ⚡ TL;DR

**Option 1** (Recommended): Run infrastructure **remotely** (Supabase, Pinecone, etc.) - Simpler, faster
**Option 2** (Advanced): Install **Docker in Jules** and run everything locally - More complex

> 📖 **Detailed comparison**: See [JULES_DOCKER_COMPARISON.md](JULES_DOCKER_COMPARISON.md)

---

## 🎯 Quick Decision Guide

| Your Situation | Recommended Approach |
|----------------|---------------------|
| First time setup | Remote Infrastructure (this guide) |
| No sudo access in Jules | Remote Infrastructure (this guide) |
| Limited Jules resources | Remote Infrastructure (this guide) |
| Need air-gapped environment | Docker Installation (see `.jules/DOCKER_SETUP.md`) |
| Have Docker expertise | Docker Installation (see `.jules/DOCKER_SETUP.md`) |

**Default**: Follow this guide (Remote Infrastructure)

---

## 📖 This Guide: Remote Infrastructure Setup

## 📋 Setup Steps

### 1️⃣ Set Up Remote Infrastructure (Choose One)

#### Option A: Fully Managed (Easiest) ⭐
- **PostgreSQL**: [Supabase](https://supabase.com) (free tier)
- **Vector DB**: [Pinecone](https://pinecone.io) (free tier)
- **Storage**: [Backblaze B2](https://www.backblaze.com/b2) (free 10GB)

#### Option B: Managed Milvus
- **PostgreSQL**: [Supabase](https://supabase.com)
- **Vector DB**: [Zilliz Cloud](https://cloud.zilliz.com) (managed Milvus, free tier)
- **Storage**: [Cloudflare R2](https://cloudflare.com/r2)

#### Option C: Self-Hosted
- Deploy `docker-compose-infra.yml` on a cloud VM (DigitalOcean/AWS)

### 2️⃣ Configure Jules

Update your Jules config at: `https://jules.google.com/repo/github/manavgup/rag_modulo/config`

```yaml
setup:
  commands:
    - cp env.jules.example .env
    - make local-dev-setup  # Install dependencies ONLY (no Docker)
```

**❌ DO NOT include**: `make local-dev-all` (this tries to start Docker)

### 3️⃣ Configure Environment

After Jules setup completes:

```bash
# 1. Edit .env with your remote service URLs
cd /app
nano .env

# Update these critical values:
POSTGRES_HOST=your-postgres-host.supabase.co
POSTGRES_PORT=5432
COLLECTIONDB_USER=postgres
COLLECTIONDB_PASS=your-password

# For Pinecone (easier):
VECTOR_DB=pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp

# For Zilliz/Milvus:
MILVUS_HOST=your-cluster.aws-us-west-2.zillizcloud.com
MILVUS_PORT=19530
MILVUS_USER=db_admin
MILVUS_PASSWORD=your-password

# Object Storage (S3-compatible):
MINIO_ENDPOINT=your-storage-endpoint.com
MINIO_ROOT_USER=your-access-key
MINIO_ROOT_PASSWORD=your-secret-key

# WatsonX (required for AI features):
WATSONX_APIKEY=your-watsonx-api-key
WATSONX_INSTANCE_ID=your-instance-id

# 2. Verify connections
make verify-remote-connections

# 3. Start services
make local-dev-backend    # Terminal 1
make local-dev-frontend   # Terminal 2 (if available)
```

## 🔍 Verify Setup

```bash
# Check all remote connections
make verify-remote-connections

# Expected output:
# ✅ PostgreSQL connected successfully
# ✅ Milvus connected successfully
# ✅ MinIO/S3 connected successfully
```

## 🆘 Common Issues

### ❌ "Connection refused"
- **Fix**: Check firewall rules, ensure services allow remote connections
- **Test**: `curl -v telnet://your-host:port`

### ❌ "Permission denied (Docker socket)"
- **Fix**: Don't run `make local-dev-all` - use `make local-dev-setup` instead
- **Why**: Jules doesn't support Docker

### ❌ "Module not found"
- **Fix**: Run `make local-dev-setup` to install dependencies
- **Check**: Backend needs Poetry, Frontend needs npm

## 📚 Full Documentation

For detailed setup guides, see:
- **[Jules Setup Guide](docs/deployment/jules-setup.md)** - Complete walkthrough
- **[Service Providers Comparison](docs/deployment/jules-setup.md#-service-providers-comparison)** - Which services to use
- **[Configuration Examples](docs/deployment/jules-setup.md#-configuration-examples)** - Copy-paste configs

## 🎯 Recommended Setup (Free Tier)

```bash
# 1. Supabase (PostgreSQL)
POSTGRES_HOST=db.xxxxxxxxxxxxx.supabase.co
POSTGRES_PORT=5432
COLLECTIONDB_USER=postgres
COLLECTIONDB_PASS=your-supabase-password

# 2. Pinecone (Vector DB - easiest for Jules)
VECTOR_DB=pinecone
PINECONE_API_KEY=pc-xxxxxxxxxxxxxxx
PINECONE_ENVIRONMENT=us-west1-gcp

# 3. Backblaze B2 (Storage)
MINIO_ENDPOINT=s3.us-west-002.backblazeb2.com
MINIO_ROOT_USER=your-b2-key-id
MINIO_ROOT_PASSWORD=your-b2-application-key

# 4. WatsonX (AI)
WATSONX_APIKEY=your-watsonx-api-key
WATSONX_INSTANCE_ID=your-instance-id
```

## ✅ Success Checklist

- [ ] Remote infrastructure services deployed
- [ ] `.env` configured with connection details
- [ ] `make verify-remote-connections` passes
- [ ] Backend starts successfully on port 8000
- [ ] Frontend starts successfully on port 3000
- [ ] Can create a collection via API
- [ ] Can upload documents and search

## 🚀 Next Steps

After successful setup:
1. Test collection creation: `POST /api/collections`
2. Upload documents: `POST /api/collections/{id}/documents`
3. Try search: `POST /api/search`
4. Explore Chain of Thought: `POST /api/search?use_cot=true`

## 🤝 Need Help?

- **Documentation**: [docs/deployment/jules-setup.md](docs/deployment/jules-setup.md)
- **Troubleshooting**: [docs/troubleshooting/](docs/troubleshooting/)
- **GitHub Issues**: [github.com/manavgup/rag_modulo/issues](https://github.com/manavgup/rag_modulo/issues)
