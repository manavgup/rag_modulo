# Quick Fix for Container Startup Issues

## Problem
Containers failing to start with:
- Milvus: "panic: Access Denied" (exit code 134)
- MLflow: Database authentication failure
- Missing environment variables warnings

## Root Cause
Critical environment variables are missing from your `.env` file, specifically:
- MinIO credentials (causing Milvus failure)
- Database passwords (causing MLflow failure)
- Other required configuration values

## Immediate Fix

### Option 1: Quick Start (Recommended for Testing)
```bash
# Use the quickstart environment file
cp .env.quickstart .env

# Generate a JWT secret
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)" >> .env

# Edit .env and replace these with your actual API keys:
# - WATSONX_APIKEY
# - WATSONX_INSTANCE_ID
# - OPENAI_API_KEY (if using OpenAI)
# - ANTHROPIC_API_KEY (if using Anthropic)

# Restart containers
make stop-containers
make run-app
```

### Option 2: Fix Existing .env
Add these critical missing variables to your `.env`:

```bash
# MinIO (CRITICAL - Milvus won't start without these)
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=minioadmin

# Database (CRITICAL - MLflow won't start without these)
COLLECTIONDB_USER=rag_modulo_user
COLLECTIONDB_PASS=rag_modulo_password

# MLflow
MLFLOW_TRACKING_USERNAME=admin
MLFLOW_TRACKING_PASSWORD=password

# Milvus
MILVUS_PORT=19530

# OIDC (use placeholders for local dev)
OIDC_DISCOVERY_ENDPOINT=https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/.well-known/openid-configuration
OIDC_AUTH_URL=https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/authorize
OIDC_TOKEN_URL=https://prepiam.ice.ibmcloud.com/v1.0/endpoint/default/token
FRONTEND_URL=http://localhost:3000
IBM_CLIENT_ID=placeholder_client_id
IBM_CLIENT_SECRET=placeholder_client_secret
```

## Verification

After fixing, verify with:

```bash
# Check environment
make validate-env

# Restart and check containers
make stop-containers
make run-app

# Check container health
docker ps --format "table {{.Names}}\t{{.Status}}"

# If any fail, check logs
docker logs milvus-standalone
docker logs rag-modulo-mlflow-server-1
```

## Expected Result

All containers should show as healthy:
- postgres: Up (healthy)
- minio: Up (healthy)
- milvus-etcd: Up (healthy)
- milvus-standalone: Up (healthy)
- mlflow-server: Up (healthy)
- backend: Up (healthy)
- frontend: Up (healthy)

## Still Having Issues?

1. **Milvus still failing?**
   - Check MinIO is accessible: `docker logs minio`
   - Verify MinIO credentials match in both services
   - Try removing volumes: `docker volume prune`

2. **MLflow still failing?**
   - Check PostgreSQL is running: `docker logs rag-modulo-postgres-1`
   - Verify database credentials match
   - Check database exists: `docker exec rag-modulo-postgres-1 psql -U rag_modulo_user -d rag_modulo -c '\l'`

3. **Other services failing?**
   - Run `make env-help` for troubleshooting guide
   - Check issue #152 for ongoing fixes
   - File a new issue with container logs

## Long-term Solution

This is a temporary fix. The proper solution involves:
1. Better environment validation in Makefile
2. Default values for non-critical variables
3. Improved error messages
4. Health check improvements

See issue #152 for the complete fix plan.
