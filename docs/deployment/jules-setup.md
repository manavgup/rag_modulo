# Jules/Remote Development Setup Guide

## 🎯 Overview

This guide helps you set up RAG Modulo in cloud-based development environments like **Jules** where Docker is not available. The strategy is to run infrastructure services (Postgres, Milvus, MinIO) remotely and connect your application code to them.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────┐
│            Jules Environment                │
│  ┌──────────────────────────────────────┐  │
│  │   Application Code (No Docker)       │  │
│  │  • Backend (FastAPI on port 8000)    │  │
│  │  • Frontend (React on port 3000)     │  │
│  └─────────────┬────────────────────────┘  │
└────────────────┼────────────────────────────┘
                 │ HTTPS Connections
                 ▼
┌─────────────────────────────────────────────┐
│      Remote Infrastructure Services         │
│  ┌──────────────────────────────────────┐  │
│  │ PostgreSQL (managed or self-hosted)  │  │
│  │ Milvus (Zilliz Cloud or self-hosted)│  │
│  │ MinIO/S3 (cloud object storage)      │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 📋 Prerequisites

1. **Jules Account** with repository access
2. **Remote Infrastructure** (see options below)
3. **API Keys**:
   - IBM WatsonX API key
   - OpenAI API key (optional, for podcasts)

## 🚀 Quick Start (3 Steps)

### Step 1: Set Up Remote Infrastructure

Choose one of these options:

#### Option A: Fully Managed (Easiest - Recommended) ⭐

Use fully managed services that require no infrastructure setup:

```bash
# 1. PostgreSQL: Sign up for Supabase (free tier)
#    https://supabase.com/dashboard/projects
#    → Create project → Get connection string

# 2. Vector DB: Sign up for Pinecone (free tier)
#    https://app.pinecone.io
#    → Create index → Get API key

# 3. Object Storage: Sign up for Cloudflare R2 (pay as you go)
#    https://dash.cloudflare.com/
#    → R2 → Create bucket → Get access keys
```

**Estimated Setup Time**: 15 minutes
**Monthly Cost**: Free (within free tiers)

#### Option B: Zilliz Cloud + Managed Services (Recommended for Milvus)

```bash
# 1. PostgreSQL: Supabase or Neon (free tier)
# 2. Milvus: Zilliz Cloud (managed Milvus, free tier)
#    https://cloud.zilliz.com
#    → Create cluster → Get connection details
# 3. Storage: Backblaze B2 or Cloudflare R2
```

**Estimated Setup Time**: 20 minutes
**Monthly Cost**: Free or ~$5-10

#### Option C: Self-Hosted on Cloud VM (Advanced)

```bash
# Deploy Docker Compose on a cloud VM (DigitalOcean, AWS, GCP)
# This gives you full control but requires VM management

# 1. Create cloud VM (Ubuntu 22.04, 4GB RAM minimum)
# 2. Install Docker and Docker Compose
# 3. Deploy infrastructure:

ssh your-vm-user@your-vm-ip
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo
docker compose -f docker-compose-infra.yml up -d

# 4. Configure firewall to allow ports:
#    - 5432 (PostgreSQL)
#    - 19530 (Milvus)
#    - 9000 (MinIO)
```

**Estimated Setup Time**: 45 minutes
**Monthly Cost**: ~$10-20 (VM hosting)

### Step 2: Configure Jules Environment

Update your Jules configuration at:
`https://jules.google.com/repo/github/manavgup/rag_modulo/config`

```yaml
# Jules Configuration
setup:
  commands:
    # Only install dependencies - DO NOT start Docker services
    - cp env.jules.example .env
    - echo "⚠️  IMPORTANT: Edit .env with your remote service URLs before starting!"
    - make local-dev-setup  # Installs Poetry + npm dependencies only

  environment:
    # Jules-specific settings
    JULES_ENVIRONMENT: "true"

  notes: |
    RAG Modulo setup complete!

    Next steps:
    1. Edit /app/.env with your remote service connection details
    2. Verify connections: make verify-remote-connections
    3. Start backend: make local-dev-backend
    4. Start frontend (new terminal): make local-dev-frontend

    Documentation: /app/docs/deployment/jules-setup.md
```

### Step 3: Configure Environment & Start Services

Once Jules finishes setup:

```bash
# 1. Edit .env with your remote service URLs
cd /app
nano .env

# Update these critical values:
# - POSTGRES_HOST=your-postgres-host.supabase.co
# - POSTGRES_PORT=5432
# - COLLECTIONDB_USER=postgres
# - COLLECTIONDB_PASS=your-password
# - MILVUS_HOST=your-cluster.aws-us-west-2.zillizcloud.com (or Pinecone API key)
# - MINIO_ENDPOINT=your-account.r2.cloudflarestorage.com
# - WATSONX_APIKEY=your-watsonx-api-key

# 2. Verify connections (optional but recommended)
make verify-remote-connections

# 3. Start backend (terminal 1)
make local-dev-backend
# Backend will be available at http://localhost:8000

# 4. Start frontend (terminal 2 - if Jules supports multiple terminals)
make local-dev-frontend
# Frontend will be available at http://localhost:3000
```

## 🔧 Configuration Examples

### Example 1: Supabase + Pinecone + Cloudflare R2

```bash
# .env configuration
POSTGRES_HOST=db.xxxxxxxxxxxxx.supabase.co
POSTGRES_PORT=5432
COLLECTIONDB_NAME=postgres
COLLECTIONDB_USER=postgres
COLLECTIONDB_PASS=your-supabase-password

# Use Pinecone instead of Milvus (easier for cloud)
VECTOR_DB=pinecone
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_ENVIRONMENT=us-west1-gcp

# Cloudflare R2 (S3-compatible)
MINIO_ENDPOINT=https://your-account-id.r2.cloudflarestorage.com
MINIO_ROOT_USER=your-r2-access-key-id
MINIO_ROOT_PASSWORD=your-r2-secret-access-key

# WatsonX
WATSONX_APIKEY=your-watsonx-api-key
WATSONX_INSTANCE_ID=your-instance-id
```

### Example 2: Neon + Zilliz Cloud + Backblaze B2

```bash
# Neon (Serverless Postgres)
POSTGRES_HOST=ep-xxxxx.us-east-2.aws.neon.tech
POSTGRES_PORT=5432
COLLECTIONDB_NAME=rag_modulo
COLLECTIONDB_USER=neondb_owner
COLLECTIONDB_PASS=your-neon-password

# Zilliz Cloud (Managed Milvus)
MILVUS_HOST=in01-xxxxxx.aws-us-west-2.zillizcloud.com
MILVUS_PORT=19530
MILVUS_USER=db_admin
MILVUS_PASSWORD=your-zilliz-password

# Backblaze B2
MINIO_ENDPOINT=s3.us-west-002.backblazeb2.com
MINIO_ROOT_USER=your-b2-key-id
MINIO_ROOT_PASSWORD=your-b2-application-key
```

### Example 3: Self-Hosted on Cloud VM

```bash
# All services on your VM
POSTGRES_HOST=your-vm-ip-address
POSTGRES_PORT=5432
COLLECTIONDB_NAME=rag_modulo
COLLECTIONDB_USER=rag_user
COLLECTIONDB_PASS=your-password

MILVUS_HOST=your-vm-ip-address
MILVUS_PORT=19530

MINIO_ENDPOINT=your-vm-ip-address:9000
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin
```

## 🧪 Verification & Testing

Add this to your Makefile for easy connection testing:

```makefile
verify-remote-connections:
	@echo "🔍 Verifying remote infrastructure connections..."
	@echo ""
	@echo "Testing PostgreSQL..."
	@cd backend && poetry run python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://$(COLLECTIONDB_USER):$(COLLECTIONDB_PASS)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(COLLECTIONDB_NAME)'))" && echo "✅ PostgreSQL connected" || echo "❌ PostgreSQL connection failed"
	@echo ""
	@echo "Testing Milvus..."
	@cd backend && poetry run python -c "from pymilvus import connections; connections.connect(host='$(MILVUS_HOST)', port='$(MILVUS_PORT)')" && echo "✅ Milvus connected" || echo "❌ Milvus connection failed"
	@echo ""
	@echo "All checks complete!"
```

## 📊 Service Providers Comparison

| Service | Provider | Free Tier | Pros | Cons |
|---------|----------|-----------|------|------|
| **PostgreSQL** | Supabase | ✅ 500MB | Easy setup, good dashboard | Limited free storage |
| | Neon | ✅ 0.5GB | Serverless, auto-scaling | New service |
| | ElephantSQL | ✅ 20MB | Mature, reliable | Very limited free tier |
| **Vector DB** | Pinecone | ✅ 1 index | Fully managed, no setup | Limited customization |
| | Zilliz Cloud | ✅ 1 cluster | True Milvus, compatible | Slightly more complex |
| | Weaviate Cloud | ✅ 1 cluster | GraphQL API, flexible | Different API from Milvus |
| **Object Storage** | Cloudflare R2 | ❌ Pay-as-go | No egress fees, fast | Requires credit card |
| | Backblaze B2 | ✅ 10GB | Cheap, S3-compatible | Slower than R2 |
| | AWS S3 | ❌ Pay-as-go | Industry standard | More expensive |

## 🎯 Recommended Combinations

### For Quick Testing (Free)
- **PostgreSQL**: Supabase (free tier)
- **Vector DB**: Pinecone (free tier)
- **Storage**: Backblaze B2 (free 10GB)

### For Production-Like Development
- **PostgreSQL**: Neon (serverless, auto-scaling)
- **Vector DB**: Zilliz Cloud (managed Milvus)
- **Storage**: Cloudflare R2 (no egress fees)

### For Maximum Control
- **All Services**: Self-hosted on cloud VM (DigitalOcean/AWS)

## ⚠️ Common Issues & Solutions

### Issue 1: "Connection refused" errors

```bash
# Check if services are accessible
curl -v telnet://your-postgres-host:5432
curl -v telnet://your-milvus-host:19530

# Solution: Check firewall rules, security groups, IP allowlists
```

### Issue 2: Poetry/npm installation fails

```bash
# Clear caches and retry
cd backend && poetry cache clear . --all
cd frontend && rm -rf node_modules && npm cache clean --force
make local-dev-setup
```

### Issue 3: WatsonX API rate limits

```bash
# Adjust rate limiting in .env
EMBEDDING_CONCURRENCY_LIMIT=1
EMBEDDING_REQUEST_DELAY=1.0
LLM_DELAY_TIME=1.0
```

### Issue 4: MinIO/S3 connection errors

```bash
# Verify S3-compatible endpoint format
# Should be: https://endpoint-without-bucket-name
# NOT: https://bucket-name.endpoint

# Test with AWS CLI
aws s3 --endpoint-url https://your-endpoint ls
```

## 🚀 Performance Optimization

### 1. Use Connection Pooling

```python
# backend/rag_solution/database.py
# Adjust pool size for remote connections
engine = create_async_engine(
    DATABASE_URL,
    pool_size=10,  # Increase for remote
    max_overflow=20,
    pool_timeout=30,  # Increase timeout
)
```

### 2. Enable Caching

```bash
# .env
ENABLE_QUERY_CACHE=true
CACHE_TTL=3600
```

### 3. Use CDN for Static Assets

```bash
# Frontend production build
REACT_APP_CDN_URL=https://your-cdn.example.com
```

## 📚 Additional Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Pinecone Quickstart](https://docs.pinecone.io/docs/quickstart)
- [Zilliz Cloud Guide](https://docs.zilliz.com/docs)
- [Cloudflare R2 Documentation](https://developers.cloudflare.com/r2/)
- [Jules Environment Setup](https://jules.google/docs/environment/)

## 🤝 Getting Help

If you encounter issues:

1. Check the [troubleshooting guide](../troubleshooting/common-issues.md)
2. Review [GitHub Issues](https://github.com/manavgup/rag_modulo/issues)
3. Ask in the project discussions

## 📝 Next Steps

After successful setup:

1. ✅ Test basic functionality: Create a collection
2. ✅ Upload documents and test search
3. ✅ Try Chain of Thought reasoning
4. ✅ Generate a podcast
5. 📖 Read the [API documentation](../api/README.md)
6. 🔧 Explore [advanced configuration](../development/advanced-configuration.md)
