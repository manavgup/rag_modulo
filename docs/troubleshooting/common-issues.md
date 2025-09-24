# 🔧 Common Issues & Solutions

This guide covers the most common issues you might encounter when using RAG Modulo and how to resolve them.

## 🐳 Docker Issues

### Services Won't Start

**Problem**: Docker containers fail to start or immediately exit.

**Symptoms:**
- Containers show as "Exited" status
- Error messages in `docker compose ps`
- Services not accessible on expected ports

**Solutions:**

```bash
# Check Docker is running
docker --version
docker info

# Check container logs
make logs

# Restart all services
make stop-containers
make run-services

# Check for port conflicts
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000
```

**Prevention:**
- Ensure Docker Desktop is running
- Check for port conflicts before starting
- Verify sufficient disk space and memory

---

### Container Health Check Failures

**Problem**: Containers start but fail health checks.

**Symptoms:**
- Containers show as "unhealthy"
- Services accessible but not functioning properly
- Intermittent connection issues

**Solutions:**

```bash
# Check health status
docker compose ps

# View detailed logs
docker compose logs backend
docker compose logs postgres

# Restart specific service
docker compose restart backend

# Check resource usage
docker stats
```

**Prevention:**
- Monitor system resources
- Ensure adequate memory allocation
- Check database connectivity

---

## 🔐 Authentication Issues

### OIDC Login Failures

**Problem**: Users cannot log in through the OIDC provider.

**Symptoms:**
- Login redirects fail
- "Invalid credentials" errors
- OIDC configuration errors

**Solutions:**

```bash
# Check OIDC configuration in .env
grep -E "OIDC|IBM_CLIENT" .env

# Verify IBM Cloud setup
# 1. Check client ID and secret
# 2. Verify redirect URLs
# 3. Ensure OIDC provider is active

# Test authentication endpoint
curl -X GET http://localhost:8000/api/auth/login
```

**Configuration Checklist:**
- ✅ IBM_CLIENT_ID is correct
- ✅ IBM_CLIENT_SECRET is valid
- ✅ Redirect URLs match your setup
- ✅ OIDC provider is active in IBM Cloud

---

### Session Management Issues

**Problem**: Users get logged out unexpectedly or sessions don't persist.

**Symptoms:**
- Frequent login prompts
- Session timeouts
- "Unauthorized" errors after login

**Solutions:**

```bash
# Check session configuration
grep -E "SESSION|JWT" .env

# Clear browser cookies and cache
# Restart backend service
docker compose restart backend

# Check JWT secret
echo $JWT_SECRET_KEY
```

---

## 🧪 Testing Issues

### Tests Failing Locally

**Problem**: Tests pass in CI but fail locally.

**Symptoms:**
- pytest failures
- Import errors
- Database connection issues

**Solutions:**

```bash
# Run tests in Docker (recommended)
make test testfile=tests/unit/test_example.py

# Use development environment
make dev-test

# Check Python environment
python --version
pip list

# Verify dependencies
cd backend && poetry check
```

**Best Practices:**
- Use Docker for consistent testing
- Keep local Python environment clean
- Run `make dev-test` for isolated testing

---

### Test Database Issues

**Problem**: Tests fail due to database connectivity or data issues.

**Symptoms:**
- Database connection errors
- Test data not found
- Transaction rollback failures

**Solutions:**

```bash
# Reset test database
make stop-containers
make run-services

# Check database connectivity
docker compose exec postgres psql -U postgres -c "\l"

# Run tests with fresh database
make test-clean testfile=tests/integration/test_database.py
```

---

## 🔍 Search & Retrieval Issues

### Poor Search Results

**Problem**: Search queries return irrelevant or no results.

**Symptoms:**
- Low relevance scores
- Missing documents in results
- Inconsistent search behavior

**Solutions:**

```bash
# Check vector database status
curl http://localhost:8000/health

# Verify document ingestion
rag-cli documents list --collection-id <collection-id>

# Test search directly
rag-cli search query --collection-id <collection-id> --query "test query"

# Check embedding model
grep EMBEDDING_MODEL .env
```

**Optimization Tips:**
- Adjust chunk size for better retrieval
- Use hybrid search strategies
- Verify embedding model compatibility
- Check document preprocessing

---

### Vector Database Connection Issues

**Problem**: Cannot connect to vector database (Milvus, Elasticsearch, etc.).

**Symptoms:**
- Connection timeout errors
- "Database not found" errors
- Slow search performance

**Solutions:**

```bash
# Check vector database status
docker compose ps | grep milvus
docker compose ps | grep elasticsearch

# Test connection
curl http://localhost:19530/health  # Milvus
curl http://localhost:9200/_cluster/health  # Elasticsearch

# Restart vector database
docker compose restart milvus-standalone
```

---

## 📊 Performance Issues

### Slow Response Times

**Problem**: API responses are slow or timeout.

**Symptoms:**
- High response times
- Request timeouts
- Memory usage spikes

**Solutions:**

```bash
# Check system resources
docker stats

# Monitor API performance
curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health

# Check database performance
docker compose exec postgres psql -U postgres -c "SELECT * FROM pg_stat_activity;"

# Optimize configuration
# - Increase memory limits
# - Tune database settings
# - Enable caching
```

**Performance Tips:**
- Use connection pooling
- Enable query caching
- Optimize database indexes
- Monitor resource usage

---

### Memory Issues

**Problem**: High memory usage or out-of-memory errors.

**Symptoms:**
- Container memory limits exceeded
- System slowdown
- OOM (Out of Memory) errors

**Solutions:**

```bash
# Check memory usage
docker stats
free -h

# Increase memory limits in docker-compose.yml
# - Increase container memory limits
# - Add swap space
# - Optimize application settings

# Restart with more memory
docker compose down
docker compose up -d
```

---

## 🔧 Configuration Issues

### Environment Variable Problems

**Problem**: Application behaves unexpectedly due to configuration issues.

**Symptoms:**
- Features not working as expected
- Connection failures
- Incorrect behavior

**Solutions:**

```bash
# Validate environment configuration
make validate-env

# Check specific variables
grep -E "VECTOR_DB|DB_HOST|MILVUS" .env

# Compare with example
diff .env env.example

# Reset to defaults
cp env.example .env
```

**Configuration Checklist:**
- ✅ All required variables are set
- ✅ Values are correct and valid
- ✅ No typos in variable names
- ✅ File permissions are correct

---

### Port Conflicts

**Problem**: Services cannot start due to port conflicts.

**Symptoms:**
- "Port already in use" errors
- Services not accessible
- Connection refused errors

**Solutions:**

```bash
# Check port usage
netstat -tulpn | grep :8000
netstat -tulpn | grep :3000
netstat -tulpn | grep :5432

# Kill conflicting processes
sudo kill -9 <PID>

# Change ports in docker-compose.yml
# - Update port mappings
# - Restart services
```

---

## 🆘 Getting Additional Help

### Diagnostic Commands

```bash
# System information
make info

# Health check
make dev-validate

# View all logs
make logs

# Check container status
docker compose ps

# Resource usage
docker stats
```

### Log Analysis

```bash
# Backend logs
docker compose logs backend

# Database logs
docker compose logs postgres

# Vector database logs
docker compose logs milvus-standalone

# Follow logs in real-time
docker compose logs -f
```

### Support Resources

1. **📚 Documentation**: [Full documentation](../index.md)
2. **🐛 Issues**: [GitHub Issues](https://github.com/manavgup/rag_modulo/issues)
3. **💬 Discussions**: [GitHub Discussions](https://github.com/manavgup/rag_modulo/discussions)
4. **🔧 Troubleshooting**: [Debugging guide](debugging.md)

---

## 💡 Prevention Tips

### Regular Maintenance

- **Monitor Resources**: Check CPU, memory, and disk usage
- **Update Dependencies**: Keep Docker and dependencies updated
- **Backup Data**: Regular backups of important data
- **Test Changes**: Test in development before production

### Best Practices

- **Use Docker**: Consistent environment across platforms
- **Monitor Logs**: Regular log review for issues
- **Validate Configuration**: Check environment variables
- **Test Thoroughly**: Run tests before deploying changes

---

<div align="center">

**Still having issues?** 🤔

[🐛 Report a Bug](https://github.com/manavgup/rag_modulo/issues) • [💬 Ask a Question](https://github.com/manavgup/rag_modulo/discussions) • [🔧 Debugging Guide](debugging.md)

</div>
