# Docker BuildKit Deprecation Warning Fix

## Issue
When running `make run-app` or build commands, you see:
```
DEPRECATED: The legacy builder is deprecated and will be removed in a future release.
            Install the buildx component to build images with BuildKit:
            https://docs.docker.com/go/buildx/
```

## Root Cause
Docker 27+ deprecates the legacy builder in favor of BuildKit, but requires the `buildx` plugin to be installed separately. When buildx is not available, Docker falls back to the legacy builder and shows the deprecation warning.

## Solutions Applied

### 1. Makefile Updates
- Removed forced BuildKit environment variables that caused build failures when buildx wasn't installed
- Updated build commands to work with the legacy builder
- Added informative messages about the deprecation warning
- Created `install-buildx` target to help users install buildx

### 2. MinIO Configuration Fix
- Corrected MinIO password mismatch between `.env` and `docker-compose-infra.yml`
- Standardized on `minioadmin` as the default password
- Fixed health checks for MinIO service

## How to Eliminate the Warning

### Option 1: Install Docker Desktop (Recommended)
Docker Desktop includes buildx by default:
- macOS/Windows: Download from https://www.docker.com/products/docker-desktop
- Linux: Follow platform-specific instructions

### Option 2: Install buildx via Homebrew (macOS)
```bash
make install-buildx
# or directly:
brew install docker-buildx
```

### Option 3: Manual Installation
Follow the official guide: https://github.com/docker/buildx#installing

## Current Status
- ✅ Builds work successfully (with deprecation warning)
- ✅ All services start correctly
- ✅ Milvus and MinIO are healthy
- ✅ No blocking errors

## Files Modified
1. `Makefile` - Updated build targets and removed forced BuildKit
2. `.env` - Fixed MinIO password
3. `docker-compose-infra.yml` - Fixed MinIO default password

## Next Steps
The deprecation warning is non-blocking. Your options are:
1. **Ignore it** - Everything works, just with a warning
2. **Install buildx** - Eliminates the warning and enables advanced build features
3. **Wait** - Docker may eventually bundle buildx in future releases

## Testing
To verify everything works:
```bash
# Check services
docker ps

# Test a build (will show warning but work)
make build-frontend

# Check Milvus health
docker exec milvus-standalone curl -s http://localhost:9091/healthz
```
