# Troubleshooting

This guide provides solutions to common issues encountered when using the RAG CLI. Issues are organized by category with step-by-step resolution instructions.

## Quick Diagnostics

### Health Check Command

Run a comprehensive health check to identify common issues:

```bash
./rag-cli --debug config test --comprehensive
```

This command will check:
- Configuration validity
- Backend connectivity
- Authentication status
- Network connectivity
- Cache health
- Log accessibility

### Debug Mode

Enable debug mode for detailed troubleshooting information:

```bash
# Enable debug for single command
./rag-cli --debug auth login

# Enable debug globally
./rag-cli config set debug true

# View debug logs
tail -f ~/.rag/logs/cli.log
```

## Installation Issues

### CLI Not Found or Not Executable

**Symptoms:**
- `command not found: rag-cli`
- `Permission denied`

**Solutions:**

1. **Check installation path:**
```bash
# Verify CLI exists
ls -la ./rag-cli

# Make executable if needed
chmod +x ./rag-cli
```

2. **Poetry environment issues:**
```bash
# Activate Poetry environment
poetry shell

# Or run with Poetry
poetry run python -m rag_solution.cli.main --help
```

3. **Path issues:**
```bash
# Add to PATH (adjust for your shell)
echo 'export PATH="$PWD:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Or create symlink
sudo ln -s $PWD/rag-cli /usr/local/bin/rag-cli
```

### Python Dependencies Missing

**Symptoms:**
- `ModuleNotFoundError`
- Import errors

**Solutions:**

1. **Reinstall dependencies:**
```bash
cd backend
poetry install --with dev,test

# Or force reinstall
poetry install --with dev,test --no-cache
```

2. **Check Python version:**
```bash
python --version  # Should be 3.8+
poetry env info    # Check Poetry environment
```

3. **Clear Python cache:**
```bash
find . -type d -name __pycache__ -exec rm -r {} +
find . -name "*.pyc" -delete
```

## Authentication Issues

### Unable to Authenticate

**Symptoms:**
- `Authentication failed`
- `Invalid client credentials`
- Browser doesn't open

**Diagnostic Steps:**

1. **Check authentication status:**
```bash
./rag-cli auth status --verbose
```

2. **Verify configuration:**
```bash
./rag-cli config show auth
```

**Solutions:**

1. **Fix client credentials:**
```bash
# Set correct client ID
./rag-cli config set auth.client_id "correct-client-id"

# Set OIDC issuer
./rag-cli config set auth.issuer "https://correct-issuer.com"

# Test configuration
./rag-cli config test-connection
```

2. **Manual browser authentication:**
```bash
# If browser doesn't open automatically
./rag-cli auth login --no-browser

# Then manually open the provided URL
```

3. **Clear authentication cache:**
```bash
# Clear stored tokens
rm -rf ~/.rag/tokens/

# Clear authentication configuration
./rag-cli config unset auth

# Reconfigure authentication
./rag-cli config set auth.client_id "your-client-id"
./rag-cli config set auth.issuer "https://your-issuer.com"
```

### Token Expired or Invalid

**Symptoms:**
- `Token expired`
- `Invalid token`
- `Authentication required` for authenticated users

**Solutions:**

1. **Refresh token:**
```bash
./rag-cli auth refresh

# Force refresh if needed
./rag-cli auth refresh --force
```

2. **Re-authenticate:**
```bash
./rag-cli auth logout
./rag-cli auth login
```

3. **Check token expiration settings:**
```bash
# Increase refresh buffer
./rag-cli config set auth.refresh_buffer 600

# Enable auto-refresh
./rag-cli config set auth.auto_refresh true
```

### OIDC Provider Issues

**Symptoms:**
- `Unable to connect to OIDC provider`
- `Invalid redirect URI`
- SSL/TLS errors

**Solutions:**

1. **Check OIDC configuration:**
```bash
# Test OIDC provider connectivity
curl -I https://your-issuer.com/.well-known/openid_configuration

# Verify redirect URI
./rag-cli config show auth.redirect_uri
```

2. **SSL issues (development only):**
```bash
# Temporarily disable SSL verification
./rag-cli config set verify_ssl false

# Update certificates (production)
# macOS: Update via System Preferences
# Linux: sudo apt update && sudo apt install ca-certificates
```

3. **Network/Proxy issues:**
```bash
# Configure proxy if needed
./rag-cli config set http.proxy "http://proxy:8080"

# Test direct connectivity
./rag-cli config test-connection --bypass-proxy
```

## Connection Issues

### Cannot Connect to Backend

**Symptoms:**
- `Connection refused`
- `Backend API not running`
- Timeout errors

**Diagnostic Steps:**

1. **Check backend URL:**
```bash
./rag-cli config show api_url
```

2. **Test connectivity:**
```bash
# Test backend health endpoint
curl -I http://localhost:8000/health

# Test with CLI
./rag-cli config test-connection
```

**Solutions:**

1. **Verify backend is running:**
```bash
# Check if backend is running locally
docker compose ps
# or
make status
```

2. **Fix backend URL:**
```bash
# Update API URL
./rag-cli config set api_url "http://localhost:8000"

# Or for remote backend
./rag-cli config set api_url "https://your-backend.com"
```

3. **Network troubleshooting:**
```bash
# Check network connectivity
ping localhost
# or
ping your-backend.com

# Check port accessibility
telnet localhost 8000
# or
nc -zv localhost 8000
```

4. **Firewall issues:**
```bash
# Linux: Check iptables
sudo iptables -L

# macOS: Check pfctl
sudo pfctl -s rules

# Windows: Check Windows Firewall
netsh advfirewall show allprofiles
```

### Slow Response Times

**Symptoms:**
- Commands take too long
- Timeout errors
- Poor performance

**Solutions:**

1. **Adjust timeout settings:**
```bash
# Increase timeout
./rag-cli config set timeout 60

# Increase retry settings
./rag-cli config set retry_attempts 5
./rag-cli config set retry_delay 2.0
```

2. **Enable caching:**
```bash
./rag-cli config set cache.enabled true
./rag-cli config set cache.ttl 3600
```

3. **Optimize batch operations:**
```bash
# Reduce batch size for slow networks
./rag-cli config set documents.batch_size 3

# Enable parallel uploads
./rag-cli config set documents.parallel_uploads false
```

## Command-Specific Issues

### Collection Operations

**Issue: Cannot create collection**

**Symptoms:**
- `Collection creation failed`
- `Vector database connection error`

**Solutions:**

1. **Check vector database status:**
```bash
# Test Milvus connection (example)
curl -I http://localhost:19530/health

# Check backend vector database config
./rag-cli collections list --debug
```

2. **Try different vector database:**
```bash
./rag-cli collections create "Test Collection" --vector-db chromadb
```

**Issue: Collection not found**

**Solutions:**

1. **List available collections:**
```bash
./rag-cli collections list
```

2. **Check collection ID format:**
```bash
# Use proper collection ID format (usually starts with 'col_')
./rag-cli collections get col_123abc
```

### Document Operations

**Issue: Document upload fails**

**Symptoms:**
- `Upload failed`
- `Unsupported file format`
- `File too large`

**Solutions:**

1. **Check file format:**
```bash
# Verify supported formats
./rag-cli config show documents.supported_formats

# Convert unsupported formats
# PDF, DOCX, TXT, MD are commonly supported
```

2. **Check file size limits:**
```bash
# Check max file size
./rag-cli config show documents.max_file_size

# Increase limit if needed
./rag-cli config set documents.max_file_size "100MB"
```

3. **File permissions:**
```bash
# Check file is readable
ls -la your-document.pdf

# Fix permissions if needed
chmod 644 your-document.pdf
```

**Issue: Document processing stuck**

**Solutions:**

1. **Check processing status:**
```bash
./rag-cli documents get col_123abc doc_456def --include-stats
```

2. **Restart processing:**
```bash
./rag-cli documents reprocess col_123abc doc_456def --force
```

3. **Check backend processing queue:**
```bash
# This would require backend API support
./rag-cli admin processing-queue status
```

### Search Operations

**Issue: No search results**

**Symptoms:**
- Empty search results
- Low relevance scores
- "No matches found"

**Solutions:**

1. **Lower similarity threshold:**
```bash
./rag-cli search query col_123abc "your query" --similarity-threshold 0.5
```

2. **Increase max chunks:**
```bash
./rag-cli search query col_123abc "your query" --max-chunks 10
```

3. **Check document processing:**
```bash
# Verify documents are processed
./rag-cli documents list col_123abc --filter "processed"
```

4. **Try different query formulation:**
```bash
# Use more specific terms
./rag-cli search query col_123abc "specific technical term"

# Or broader terms
./rag-cli search query col_123abc "general concept"
```

**Issue: Search performance problems**

**Solutions:**

1. **Check index health:**
```bash
./rag-cli collections get col_123abc --include-stats
```

2. **Optimize search parameters:**
```bash
# Reduce max chunks for faster results
./rag-cli search query col_123abc "query" --max-chunks 3

# Increase similarity threshold for more relevant results
./rag-cli search query col_123abc "query" --similarity-threshold 0.8
```

## Configuration Issues

### Invalid Configuration

**Symptoms:**
- `Configuration error`
- `Invalid JSON syntax`
- Commands fail unexpectedly

**Solutions:**

1. **Validate configuration:**
```bash
./rag-cli config validate

# Fix syntax errors automatically
./rag-cli config validate --fix-syntax
```

2. **Reset configuration:**
```bash
# Backup first
./rag-cli config backup ~/.rag/config-backup.json

# Reset to defaults
./rag-cli config reset

# Or recreate configuration
rm ~/.rag/config.json
./rag-cli config init
```

3. **Check configuration permissions:**
```bash
# Ensure config directory is writable
ls -la ~/.rag/
chmod 755 ~/.rag/
chmod 644 ~/.rag/config.json
```

### Profile Issues

**Issue: Profile not found**

**Solutions:**

1. **List available profiles:**
```bash
./rag-cli config profiles
```

2. **Create missing profile:**
```bash
./rag-cli config create-profile missing-profile
```

3. **Switch to existing profile:**
```bash
./rag-cli config use-profile default
```

## Performance Issues

### Slow Command Execution

**Diagnostic Steps:**

1. **Enable timing information:**
```bash
./rag-cli --debug --verbose command args
```

2. **Check system resources:**
```bash
# Check memory usage
free -h

# Check disk space
df -h

# Check network latency
ping your-backend.com
```

**Solutions:**

1. **Clear cache:**
```bash
# Clear CLI cache
./rag-cli config clean-cache

# Or disable cache temporarily
./rag-cli config set cache.enabled false
```

2. **Optimize configuration:**
```bash
# Reduce timeout for faster failure
./rag-cli config set timeout 15

# Enable compression
./rag-cli config set cache.compression true
```

### Memory Issues

**Symptoms:**
- Out of memory errors
- System becomes unresponsive
- Large file processing fails

**Solutions:**

1. **Reduce batch sizes:**
```bash
./rag-cli config set documents.batch_size 2
./rag-cli config set search.max_chunks 3
```

2. **Process files individually:**
```bash
# Instead of bulk upload
for file in *.pdf; do
    ./rag-cli documents upload col_123abc "$file"
done
```

3. **Monitor memory usage:**
```bash
# Monitor during operation
top -p $(pgrep -f rag-cli)
```

## Log Analysis

### Enable Comprehensive Logging

```bash
# Set debug level logging
./rag-cli config set logging.level DEBUG

# Enable verbose output
./rag-cli config set output.verbose true

# Run command with maximum logging
./rag-cli --debug --verbose command args
```

### Common Log Patterns

**Authentication Issues:**
```bash
grep -i "auth" ~/.rag/logs/cli.log | tail -10
```

**Network Issues:**
```bash
grep -i "connection\|timeout\|network" ~/.rag/logs/cli.log | tail -10
```

**Configuration Issues:**
```bash
grep -i "config\|setting" ~/.rag/logs/cli.log | tail -10
```

**API Errors:**
```bash
grep -i "error\|exception" ~/.rag/logs/cli.log | tail -20
```

### Log Rotation Issues

**Issue: Log files too large**

**Solutions:**
```bash
# Configure log rotation
./rag-cli config set logging.max_size "10MB"
./rag-cli config set logging.backup_count 5

# Manually rotate logs
./rag-cli config rotate-logs
```

## Environment-Specific Issues

### Docker/Container Issues

**Issue: CLI not working in container**

**Solutions:**

1. **Check container setup:**
```bash
# Run CLI in container
docker run --rm -it -v ~/.rag:/root/.rag rag-cli --version

# Check volume mounts
docker run --rm -it -v ~/.rag:/root/.rag rag-cli config show
```

2. **Network connectivity in container:**
```bash
# Test connectivity from container
docker run --rm -it --net host rag-cli config test-connection
```

### CI/CD Pipeline Issues

**Issue: Authentication in automated environments**

**Solutions:**

1. **Use service account credentials:**
```bash
# Set environment variables in CI
export RAG_AUTH_CLIENT_ID="$SERVICE_ACCOUNT_ID"
export RAG_AUTH_CLIENT_SECRET="$SERVICE_ACCOUNT_SECRET"

# Use non-interactive authentication
./rag-cli auth login --non-interactive
```

2. **Disable interactive prompts:**
```bash
# Set non-interactive mode
export RAG_NON_INTERACTIVE=true

# Or use force flags
./rag-cli collections delete col_123abc --force
```

## System Integration Issues

### Shell Integration

**Issue: Tab completion not working**

**Solutions:**

1. **Install completion:**
```bash
# Generate completion script
./rag-cli completion bash > ~/.rag-completion.bash

# Add to shell profile
echo 'source ~/.rag-completion.bash' >> ~/.bashrc
source ~/.bashrc
```

2. **Fix shell compatibility:**
```bash
# For zsh
./rag-cli completion zsh > ~/.rag-completion.zsh
echo 'source ~/.rag-completion.zsh' >> ~/.zshrc
```

### Editor Integration

**Issue: Configuration editing problems**

**Solutions:**

1. **Use built-in editor:**
```bash
./rag-cli config edit
```

2. **Specify editor:**
```bash
export EDITOR=vim
./rag-cli config edit

# Or use specific editor
./rag-cli config edit --editor code
```

## Recovery Procedures

### Complete Reset

If all else fails, perform a complete reset:

```bash
#!/bin/bash
echo "🔄 Performing complete RAG CLI reset..."

# 1. Backup existing configuration
if [ -f ~/.rag/config.json ]; then
    cp ~/.rag/config.json ~/.rag/config.json.backup.$(date +%Y%m%d_%H%M%S)
fi

# 2. Stop any running processes
pkill -f rag-cli

# 3. Clear all CLI data
rm -rf ~/.rag/

# 4. Reinstall CLI
cd backend
poetry install --with dev,test

# 5. Initialize fresh configuration
./rag-cli config init

# 6. Test installation
./rag-cli --version
./rag-cli config test

echo "✅ Reset completed. Please reconfigure authentication:"
echo "   ./rag-cli config set auth.client_id 'your-client-id'"
echo "   ./rag-cli config set auth.issuer 'https://your-issuer.com'"
```

### Selective Recovery

For targeted recovery of specific components:

```bash
# Reset only authentication
rm -rf ~/.rag/tokens/
./rag-cli config unset auth
./rag-cli auth login

# Reset only configuration
rm ~/.rag/config.json
./rag-cli config init

# Clear only cache
rm -rf ~/.rag/cache/
./rag-cli config set cache.enabled true
```

## Getting Additional Help

### Built-in Help

```bash
# Command help
./rag-cli --help
./rag-cli auth --help
./rag-cli collections create --help

# Show examples
./rag-cli collections create --examples
```

### Debug Information Collection

When reporting issues, collect this information:

```bash
#!/bin/bash
# collect-debug-info.sh

echo "RAG CLI Debug Information"
echo "========================"
echo "Date: $(date)"
echo "System: $(uname -a)"
echo ""

echo "CLI Version:"
./rag-cli --version
echo ""

echo "Python Environment:"
python --version
poetry --version
echo ""

echo "Configuration:"
./rag-cli config show --format json
echo ""

echo "Test Results:"
./rag-cli config test --verbose
echo ""

echo "Recent Logs (last 20 lines):"
tail -20 ~/.rag/logs/cli.log
echo ""

echo "System Resources:"
df -h ~/.rag/
du -sh ~/.rag/*
```

### Community Support

1. **GitHub Issues**: [rag_modulo/issues](https://github.com/manavgup/rag_modulo/issues)
2. **Documentation**: Check for updated troubleshooting guides
3. **Debug Mode**: Always include `--debug --verbose` output in bug reports

### Professional Support

For enterprise support and custom troubleshooting:

1. Contact your system administrator
2. Check internal documentation
3. Escalate to technical support team

## Prevention Tips

### Regular Maintenance

```bash
#!/bin/bash
# maintenance.sh - Run weekly

echo "🔧 RAG CLI Maintenance"

# Update dependencies
cd backend && poetry update

# Clean cache
./rag-cli config clean-cache --older-than 7d

# Rotate logs
./rag-cli config rotate-logs

# Test configuration
./rag-cli config test

# Test connectivity
./rag-cli config test-connection

echo "✅ Maintenance completed"
```

### Monitoring

```bash
#!/bin/bash
# monitoring.sh - Health check script

# Check CLI health
if ! ./rag-cli config test --quiet; then
    echo "❌ CLI health check failed"
    # Send alert or notification
fi

# Check authentication
if ! ./rag-cli auth status --quiet; then
    echo "⚠️ Authentication expired"
    # Send notification for renewal
fi

# Check disk space
usage=$(df ~/.rag | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$usage" -gt 80 ]; then
    echo "⚠️ High disk usage in ~/.rag: ${usage}%"
fi
```

By following this troubleshooting guide, you should be able to resolve most common issues with the RAG CLI. If problems persist, don't hesitate to seek additional help using the provided support channels.
