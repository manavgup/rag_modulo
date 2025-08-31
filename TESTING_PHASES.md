# Testing Guide for Build Process and Container Startup Fixes

This document outlines the testing procedures for each phase of the fixes implemented for issue #152: "Critical: Fix Build Process and Container Startup Failures".

## **Phase 1: Critical Environment Variable Fixes**

### **What Was Fixed**
- Added missing critical environment variables to `env.example`
- Fixed MinIO credentials with default values
- Fixed MLflow server configuration
- Added proper environment variable fallbacks

### **Testing Procedure**

#### **1.1 Test Environment Variable Setup**
```bash
# Copy the example environment file
cp env.example .env

# Run environment validation
make validate-env

# Expected Output: All critical variables should show "✓ OK"
```

#### **1.2 Test Container Startup**
```bash
# Start the application
make run-app

# Check if all containers start successfully
docker ps

# Expected: All services should be running and healthy
```

#### **1.3 Verify Critical Services**
```bash
# Check MinIO (should not have SIGABRT errors)
docker logs minio | grep -i "error\|panic\|fatal"

# Check Milvus (should start without access denied errors)
docker logs milvus-standalone | grep -i "error\|panic\|fatal"

# Check MLflow (should start without timeout)
docker logs mlflow-server | grep -i "error\|timeout\|failed"
```

### **Success Criteria**
- ✅ `make validate-env` passes with no errors
- ✅ `make run-app` starts all containers successfully
- ✅ No SIGABRT errors in Milvus logs
- ✅ MLflow server starts within 60 seconds
- ✅ All services show "healthy" status

---

## **Phase 2: Build Optimization**

### **What Was Fixed**
- Added comprehensive `.dockerignore` files
- Enabled Docker BuildKit
- Optimized Dockerfile layer ordering
- Implemented multi-stage builds

### **Testing Procedure**

#### **2.1 Test Build Context Reduction**
```bash
# Check build context sizes
make build-optimize

# Expected Output:
# ✓ Frontend .dockerignore exists
# ✓ Backend .dockerignore exists
# BuildKit available
```

#### **2.2 Test Build Performance**
```bash
# Run comprehensive build performance tests
make build-performance

# This will:
# - Measure build times
# - Test layer caching
# - Compare BuildKit vs standard builds
# - Generate performance report
```

#### **2.3 Manual Build Testing**
```bash
# Test frontend build
docker build -t test-frontend -f webui/Dockerfile.frontend webui

# Test backend build
docker build -t test-backend -f backend/Dockerfile.backend backend

# Check build times and image sizes
docker images test-frontend test-backend
```

### **Success Criteria**
- ✅ Build context reduced by at least 50%
- ✅ Build times reduced by at least 30%
- ✅ Layer caching working properly
- ✅ BuildKit enabled and functional
- ✅ No deprecated builder warnings

---

## **Phase 3: Frontend Security & Modernization**

### **What Was Fixed**
- Removed deprecated `carbon-components-react`
- Updated build tooling
- Added security audit scripts
- Migrated to modern Carbon components

### **Testing Procedure**

#### **3.1 Test Security Vulnerabilities**
```bash
cd webui

# Check for security vulnerabilities
npm audit

# Fix vulnerabilities automatically
npm run audit:fix

# Check outdated packages
npm run outdated
```

#### **3.2 Test Build Process**
```bash
# Clean install dependencies
npm run clean

# Build the application
npm run build

# Check build output size
ls -la build/
```

#### **3.3 Test Component Migration**
```bash
# Check if deprecated packages are removed
npm list carbon-components-react

# Expected: Package not found or not installed
```

### **Success Criteria**
- ✅ `npm audit` shows 0 critical/high vulnerabilities
- ✅ Build completes without errors
- ✅ No deprecated package warnings
- ✅ Modern Carbon components working
- ✅ Bundle size optimized

---

## **Phase 4: Backend Optimization**

### **What Was Fixed**
- Fixed Poetry lock file issues
- Implemented dependency caching
- Optimized Python dependency installation
- Added proper Poetry version pinning

### **Testing Procedure**

#### **4.1 Test Poetry Configuration**
```bash
cd backend

# Check Poetry version
poetry --version

# Verify dependency installation
poetry install --only main

# Check for lock file warnings
poetry lock --no-update
```

#### **4.2 Test Docker Build**
```bash
# Build backend image
docker build -t test-backend -f backend/Dockerfile.backend backend

# Check build logs for Poetry warnings
# Expected: No "lock file might not be compatible" warnings
```

#### **4.3 Test Dependency Management**
```bash
cd backend

# Check installed packages
poetry show --tree

# Verify no unused dependencies
poetry show --outdated
```

### **Success Criteria**
- ✅ No Poetry lock file compatibility warnings
- ✅ Dependencies install without errors
- ✅ Build cache working properly
- ✅ No unnecessary package installations

---

## **Phase 5: Container Health & Monitoring**

### **What Was Fixed**
- Improved health checks for all services
- Added comprehensive health monitoring scripts
- Enhanced service startup dependencies
- Better error logging and debugging

### **Testing Procedure**

#### **5.1 Test Health Check Script**
```bash
# Run comprehensive health check
make health-check

# Expected Output:
# ✓ All services are healthy
# ✓ Network connectivity verified
# ✓ Environment variables validated
```

#### **5.2 Test Service Dependencies**
```bash
# Start services and monitor startup order
make run-app

# Watch service startup sequence
docker-compose logs -f

# Expected: Services start in proper dependency order
```

#### **5.3 Test Error Handling**
```bash
# Simulate service failure
docker stop postgres

# Check if dependent services handle failure gracefully
docker logs backend | grep -i "error\|retry"

# Restart service
docker start postgres
```

### **Success Criteria**
- ✅ Health check script runs without errors
- ✅ All services show healthy status
- ✅ Proper startup dependencies working
- ✅ Graceful error handling implemented

---

## **Phase 6: Testing & Validation**

### **What Was Added**
- New Makefile targets for validation
- Comprehensive testing scripts
- Performance measurement tools
- Automated validation workflows

### **Testing Procedure**

#### **6.1 Test New Makefile Targets**
```bash
# Test environment validation
make validate-env

# Test health checking
make health-check

# Test build optimization
make build-optimize

# Test build performance
make build-performance
```

#### **6.2 Test Validation Scripts**
```bash
# Test environment validation script
./scripts/validate-env.sh

# Test health check script
./scripts/health-check.sh

# Test build performance script
./scripts/build-performance.sh
```

### **Success Criteria**
- ✅ All new Makefile targets work
- ✅ Validation scripts execute properly
- ✅ Performance measurements accurate
- ✅ Comprehensive reporting working

---

## **End-to-End Testing**

### **Complete System Test**
```bash
# 1. Validate environment
make validate-env

# 2. Start all services
make run-app

# 3. Wait for all services to be healthy
make health-check

# 4. Test build optimization
make build-optimize

# 5. Test build performance
make build-performance

# 6. Run application tests
make tests
```

### **Expected Results**
- ✅ All services start successfully
- ✅ No container startup failures
- ✅ Build process optimized
- ✅ Security vulnerabilities resolved
- ✅ Performance improved significantly

---

## **Troubleshooting**

### **Common Issues**

#### **Environment Variables Missing**
```bash
# Check what's missing
make validate-env

# Copy and configure .env file
cp env.example .env
# Edit .env with proper values
```

#### **Container Startup Failures**
```bash
# Check service logs
docker-compose logs [service-name]

# Run health check
make health-check

# Check environment
make validate-env
```

#### **Build Performance Issues**
```bash
# Check build context size
make build-optimize

# Test build performance
make build-performance

# Verify .dockerignore files exist
ls -la webui/.dockerignore backend/.dockerignore
```

### **Performance Benchmarks**

#### **Before Fixes (Expected)**
- Frontend build context: ~1.3GB
- Backend build context: ~1.2GB
- Total build time: 10-15 minutes
- Multiple security vulnerabilities

#### **After Fixes (Target)**
- Frontend build context: <500MB
- Backend build context: <400MB
- Total build time: <5 minutes
- Zero critical/high vulnerabilities

---

## **Validation Checklist**

Before submitting the PR, ensure all items are checked:

- [ ] Phase 1: Environment variables fixed and tested
- [ ] Phase 2: Build optimization implemented and tested
- [ ] Phase 3: Frontend security resolved and tested
- [ ] Phase 4: Backend optimization completed and tested
- [ ] Phase 5: Container health monitoring working
- [ ] Phase 6: Testing tools functional
- [ ] All tests passing
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] No breaking changes introduced

---

## **Support**

If you encounter issues during testing:

1. Check the logs: `docker-compose logs [service-name]`
2. Run health check: `make health-check`
3. Validate environment: `make validate-env`
4. Check build optimization: `make build-optimize`
5. Review this testing guide for specific phase issues

For additional help, refer to the main README.md or create an issue with detailed error information.
