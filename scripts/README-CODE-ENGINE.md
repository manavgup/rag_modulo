# IBM Cloud Code Engine Deployment Guide

Complete guide for deploying RAG Modulo to IBM Cloud Code Engine.

## Prerequisites

### On Your Mac (Local Workstation)

1. **IBM Cloud CLI** installed
   ```bash
   curl -fsSL https://clis.cloud.ibm.com/install/osx | sh
   ```

2. **IBM Cloud plugins**
   ```bash
   ibmcloud plugin install container-registry
   ibmcloud plugin install code-engine
   ```

3. **Docker Desktop** installed and running

4. **Configuration files**
   - Create `.secrets` file with your IBM Cloud API key:
     ```bash
     IBM_CLOUD_API_KEY=your-api-key-here
     IBM_CLOUD_REGION=ca-tor  # or us-south, eu-gb, etc.
     IBM_CR_NAMESPACE=rag_modulo
     CODE_ENGINE_PROJECT=rag-modulo
     IBM_CLOUD_RESOURCE_GROUP=Default
     ```

## Quick Start (5 Minutes)

### Option 1: Full Pipeline (Recommended for First Deployment)

```bash
# From your Mac, run:
make ce-deploy-full
```

This will:
1. ✅ Build Docker images locally
2. ✅ Test images with `make prod-start`
3. ✅ Push to IBM Container Registry
4. ✅ Deploy to Code Engine
5. ✅ Run smoke tests

### Option 2: Quick Deploy (Skip Local Testing)

```bash
make ce-deploy-quick
```

Skips step 2 (local testing) for faster deployment.

## Step-by-Step Deployment

### Step 1: Clean Up Old Resources (First Time Only)

```bash
# Run cleanup script
make ce-cleanup
```

This interactive script lets you:
- Delete old Code Engine projects
- Remove specific apps
- List existing resources

### Step 2: Build and Test Locally

```bash
# Build images
make build-all

# Test locally
make prod-start
make prod-status

# Verify
curl http://localhost:8000/health
curl http://localhost:3000

# Stop when done
make prod-stop
```

### Step 3: Push to IBM Container Registry

```bash
make ce-push
```

Or use the full script:
```bash
./scripts/build-and-push-for-local-testing.sh
```

### Step 4: Deploy to Code Engine

```bash
make ce-deploy
```

Or use the full script:
```bash
./scripts/deploy-to-code-engine.sh
```

### Step 5: Monitor and Verify

```bash
# Check status
make ce-status

# View logs
make ce-logs

# Get app URLs
ibmcloud ce app list
```

## Available Make Targets

### Code Engine Deployment
```bash
make ce-cleanup       # Clean up old Code Engine resources
make ce-push          # Push images to IBM Container Registry
make ce-deploy        # Deploy to Code Engine (images must exist)
make ce-deploy-full   # Full pipeline: Build → Test → Push → Deploy
make ce-deploy-quick  # Quick: Build → Push → Deploy (skip local test)
make ce-logs          # View Code Engine logs
make ce-status        # Show Code Engine app status
```

### Local Development
```bash
make build-all        # Build backend and frontend images
make prod-start       # Start production stack locally
make prod-stop        # Stop production stack
make prod-status      # Show production status
make prod-logs        # View production logs
```

## Available Scripts

All scripts are in the `scripts/` directory:

### Deployment Scripts

1. **`cleanup-code-engine.sh`**
   - Interactive cleanup of Code Engine resources
   - Options to delete projects, apps, or list resources
   - Safe with confirmation prompts

2. **`build-and-push-for-local-testing.sh`**
   - Builds images locally using fixed Dockerfiles
   - Pushes to IBM Container Registry
   - Uses git SHA as image tag

3. **`deploy-to-code-engine.sh`**
   - Deploys pre-built images to Code Engine
   - Creates or updates apps
   - Handles soft-deleted projects
   - Runs smoke tests

4. **`deploy-end-to-end.sh`**
   - Complete pipeline from build to deployment
   - Optional local testing (`--skip-test` to skip)
   - Comprehensive smoke tests

5. **`code-engine-logs.sh`**
   - View logs from both apps
   - Default: last 50 lines
   - Pass number for different count: `./scripts/code-engine-logs.sh 100`

## Troubleshooting

### Issue: "IBM Cloud CLI not found"
```bash
# Install IBM Cloud CLI
curl -fsSL https://clis.cloud.ibm.com/install/osx | sh

# Install plugins
ibmcloud plugin install container-registry
ibmcloud plugin install code-engine
```

### Issue: "Project is soft-deleted"
The deployment script automatically handles this by creating a new project with a timestamp suffix.

Or manually:
```bash
# List projects
ibmcloud ce project list

# Delete soft-deleted project
ibmcloud ce project delete --name old-project --hard
```

### Issue: "Image not found in ICR"
```bash
# Verify images exist
docker manifest inspect ca.icr.io/rag_modulo/rag-modulo-backend:$(git rev-parse HEAD)

# Re-push if needed
make ce-push
```

### Issue: "Apps not starting"
```bash
# Check logs
make ce-logs

# Check app status
ibmcloud ce app get rag-modulo-backend
ibmcloud ce app get rag-modulo-frontend

# Check revisions
ibmcloud ce revision list
```

### Issue: "Health checks failing"
```bash
# Apps may need more time to start
sleep 60

# Test backend directly
BACKEND_URL=$(ibmcloud ce app get rag-modulo-backend -o json | jq -r '.status.url')
curl -v $BACKEND_URL/health

# Check container logs
ibmcloud ce app logs --app rag-modulo-backend --tail 100
```

## Configuration

### Environment Variables (in .secrets)

```bash
# Required
IBM_CLOUD_API_KEY=your-api-key

# Optional (with defaults)
IBM_CLOUD_REGION=ca-tor           # Default: ca-tor
IBM_CR_NAMESPACE=rag_modulo       # Default: rag_modulo
CODE_ENGINE_PROJECT=rag-modulo    # Default: rag-modulo
IBM_CLOUD_RESOURCE_GROUP=Default  # Default: Default
```

### Resource Allocation

Backend:
- CPU: 2 cores
- Memory: 4GB
- Scaling: 1-5 instances

Frontend:
- CPU: 1 core
- Memory: 2GB
- Scaling: 1-3 instances

Modify in `scripts/deploy-to-code-engine.sh` if needed.

## Comparison with PR #641

### Old Approach (50+ Failed Commits)
- ❌ Complex GitHub Actions workflow
- ❌ Built in CI/CD (disk space issues)
- ❌ No local testing
- ❌ 8+ failure points
- ❌ ~50 minutes per attempt

### New Approach (This Solution)
- ✅ Simple scripts leveraging working Makefile
- ✅ Build and test locally first
- ✅ Push pre-tested images
- ✅ 2 failure points (build, deploy)
- ✅ ~10 minutes total

## Next Steps After Deployment

1. **Visit your apps**
   - Get URLs: `ibmcloud ce app list`
   - Open in browser

2. **Set up secrets** (if not done)
   ```bash
   ibmcloud ce secret create rag-modulo-secrets \
     --from-literal COLLECTIONDB_HOST=... \
     --from-literal MILVUS_HOST=... \
     # ... etc
   ```

3. **Set up custom domain** (optional)
   ```bash
   ibmcloud ce domainmapping create --name my-domain \
     --domain-name rag.example.com \
     --target rag-modulo-frontend
   ```

4. **Set up monitoring**
   - Enable IBM Cloud Monitoring
   - Set up alerts for app failures
   - Monitor resource usage

## Getting Help

- **IBM Cloud Code Engine Docs**: https://cloud.ibm.com/docs/codeengine
- **IBM Cloud CLI Docs**: https://cloud.ibm.com/docs/cli
- **Project Issues**: https://github.com/manavgup/rag_modulo/issues

## Cost Considerations

Code Engine pricing (as of 2024):
- Free tier: 100,000 vCPU-seconds/month
- Typical cost: $5-20/month for dev/test workloads
- Production: $50-200/month depending on scale

Monitor costs in IBM Cloud dashboard.
