# IBM Code Engine Quick Start Guide

Get RAG Modulo deployed to IBM Code Engine in under 2 hours.

## Prerequisites

- IBM Cloud account ([Sign up](https://cloud.ibm.com/registration) - free tier available)
- GitHub repository with admin access
- Docker images building successfully

## Cost: $0-20/month (free tier covers most staging usage)

---

## Step 1: Set Up IBM Cloud (30 minutes)

### Install IBM Cloud CLI

```bash
# macOS
curl -fsSL https://clis.cloud.ibm.com/install/osx | sh

# Linux
curl -fsSL https://clis.cloud.ibm.com/install/linux | sh

# Install Code Engine plugin
ibmcloud plugin install code-engine -f
```

### Install code-engine plugin

```bash
ibmcloud plugin install code-engine
```

### Login and Create Project

```bash
# Login
ibmcloud login --sso

# Set resource group
ibmcloud target -g rg-rag-turbo-01

# Create Code Engine project
ibmcloud code-engine project create --name rag-modulo-staging

# Select project
```

### Create Secrets

**Registry Secret (for pulling from GitHub Container Registry):**

```bash
# Create GitHub PAT with read:packages permission
# https://github.com/settings/tokens

ibmcloud code-engine secret create \
  --name ghcr-secret \
  --format registry \
  --server ghcr.io \
  --username YOUR_GITHUB_USERNAME \
  --password YOUR_GITHUB_PAT
```

**Application Secrets (environment variables):**

**Option 1: Automatic from .env (Recommended)**

```bash
# Automatically creates secrets from your .env file
./scripts/ibm-create-secrets.sh
```

**Option 2: Manual (if you don't have .env)**

```bash
ibmcloud code-engine secret create \
  --name rag-modulo-secrets \
  --from-literal COLLECTIONDB_HOST=your-db-host \
  --from-literal COLLECTIONDB_PORT=5432 \
  --from-literal COLLECTIONDB_NAME=rag_modulo \
  --from-literal COLLECTIONDB_USER=your-user \
  --from-literal COLLECTIONDB_PASSWORD=your-password \
  --from-literal VECTOR_DB=milvus \
  --from-literal MILVUS_HOST=your-milvus-host \
  --from-literal MILVUS_PORT=19530 \
  --from-literal JWT_SECRET_KEY=your-jwt-secret \
  --from-literal WATSONX_APIKEY=your-watsonx-key \
  --from-literal WATSONX_URL=https://us-south.ml.cloud.ibm.com \
  --from-literal WATSONX_INSTANCE_ID=your-instance-id \
  --from-literal OPENAI_API_KEY=your-openai-key \
  --from-literal ANTHROPIC_API_KEY=your-anthropic-key
```

### Get API Key

```bash
ibmcloud iam api-key-create rag-modulo-github-actions \
  -d "API key for GitHub Actions" \
  --file api-key.json

# View the key
cat api-key.json | jq -r '.apikey'
```

**⚠️ Save this API key - you'll need it for GitHub!**

---

## Step 2: Configure GitHub (15 minutes)

### Add GitHub Secret

Go to: **Your Repo → Settings → Secrets and variables → Actions**

**Secret:**
- Name: `IBM_CLOUD_API_KEY`
- Value: [The API key from Step 1]

### Add GitHub Variables

In the **Variables** tab:

| Variable | Value |
|----------|-------|
| `IBM_CLOUD_REGION` | `us-south` |
| `CODE_ENGINE_PROJECT` | `rag-modulo-staging` |
| `CODE_ENGINE_REGISTRY_SECRET` | `ghcr-secret` |

---

## Step 3: Deploy! (5 minutes)

### Option A: Push to Branch

```bash
git checkout -b staging
git push origin staging
```

The workflow triggers automatically.

### Option B: Manual Trigger

1. Go to: **Actions → Deploy to IBM Code Engine Staging**
2. Click **Run workflow**
3. Select branch → **Run workflow**

---

## Step 4: Access Your App

After deployment completes, get your URLs:

```bash
# Backend URL
ibmcloud code-engine app get --name rag-modulo-backend -o json | jq -r '.status.url'

# Frontend URL
ibmcloud code-engine app get --name rag-modulo-frontend -o json | jq -r '.status.url'
```

Your apps are live! 🎉

---

## What Was Deployed

✅ **Backend** - FastAPI app running on Code Engine
✅ **Frontend** - React app running on Code Engine
✅ **Auto-scaling** - Scales to 0 when idle (saves $$)
✅ **HTTPS URLs** - Automatically provisioned

---

## Key Differences from K8s Deployment

| Feature | Kubernetes | IBM Code Engine |
|---------|-----------|-----------------|
| **Setup Time** | 2-3 hours | 1 hour |
| **Monthly Cost** | $300-500 | $0-20 |
| **Management** | Manual cluster | Fully managed |
| **Scaling** | Always running | Scales to zero |
| **Deployment** | kubectl + Helm | IBM CLI |

---

## Troubleshooting

### "Project not found"

```bash
ibmcloud code-engine project list
ibmcloud code-engine project select --name rag-modulo-staging
```

### "Registry authentication failed"

Recreate the registry secret with a fresh GitHub PAT.

### "App failed to deploy"

```bash
# Check logs
ibmcloud code-engine app logs --name rag-modulo-backend

# Check events
ibmcloud code-engine app events --name rag-modulo-backend
```

### Health check fails

Code Engine apps scale to zero when idle. First request takes ~10-30 seconds (cold start). This is normal.

---

## Useful Commands

```bash
# List apps
ibmcloud code-engine app list

# View logs
ibmcloud code-engine app logs --name rag-modulo-backend --follow

# Update secret
ibmcloud code-engine secret update --name rag-modulo-secrets \
  --from-literal NEW_VAR=value

# Delete app
ibmcloud code-engine app delete --name rag-modulo-backend -f
```

---

## Next Steps

1. ✅ Set up external databases (PostgreSQL, Milvus, MinIO)
2. ✅ Update secrets with real connection strings
3. ✅ Test full application
4. ✅ Set up custom domain (optional)
5. ✅ Configure monitoring (IBM Cloud Logs)

---

## Resources

- [IBM Code Engine Docs](https://cloud.ibm.com/docs/codeengine)
- [Pricing Calculator](https://www.ibm.com/cloud/code-engine/pricing)
- [GitHub Actions Workflow](/.github/workflows/ibm-code-engine-staging.yml)
