# Configuration

The RAG CLI provides extensive configuration options to customize behavior, authentication, and integration with your RAG system. Configuration is managed through profiles, allowing different settings for development, staging, and production environments.

## Configuration Overview

### Configuration Hierarchy

The CLI uses the following configuration priority order:

1. **Command-line flags** (highest priority)
2. **Environment variables**
3. **Profile-specific configuration**
4. **Global configuration**
5. **Default values** (lowest priority)

### Configuration Locations

- **Global Config**: `~/.rag/config.json`
- **Profile Configs**: `~/.rag/profiles/`
- **Authentication Tokens**: `~/.rag/tokens/`
- **Cache Directory**: `~/.rag/cache/`
- **Logs Directory**: `~/.rag/logs/`

## Configuration File Structure

### Main Configuration File (`~/.rag/config.json`)

```json
{
  "active_profile": "default",
  "profiles": {
    "default": {
      "api_url": "http://localhost:8000",
      "timeout": 30,
      "verify_ssl": true,
      "output": {
        "format": "table",
        "verbose": false,
        "colors": true
      },
      "auth": {
        "provider": "ibm",
        "client_id": "your-client-id",
        "issuer": "https://your-oidc-provider.com",
        "scope": "openid profile email",
        "auto_refresh": true,
        "refresh_buffer": 300
      },
      "search": {
        "max_chunks": 5,
        "similarity_threshold": 0.7,
        "default_model": "gpt-3.5-turbo",
        "temperature": 0.1
      },
      "collections": {
        "default_vector_db": "milvus",
        "default_chunk_size": 512,
        "default_chunk_overlap": 50,
        "default_private": false
      },
      "documents": {
        "auto_title": false,
        "batch_size": 5,
        "max_file_size": "50MB",
        "supported_formats": ["pdf", "docx", "txt", "md"]
      },
      "cache": {
        "enabled": true,
        "ttl": 3600,
        "max_size": "1GB"
      },
      "logging": {
        "level": "INFO",
        "file": "~/.rag/logs/cli.log",
        "max_size": "10MB",
        "backup_count": 5
      }
    }
  }
}
```

### Profile-Specific Configuration

Profiles allow you to maintain different configurations for different environments:

```bash
# Development profile
~/.rag/profiles/dev.json
{
  "api_url": "http://localhost:8000",
  "timeout": 60,
  "verify_ssl": false,
  "auth": {
    "client_id": "dev-client-id",
    "issuer": "https://dev-auth.company.com"
  },
  "logging": {
    "level": "DEBUG"
  }
}

# Production profile
~/.rag/profiles/prod.json
{
  "api_url": "https://rag-api.company.com",
  "timeout": 30,
  "verify_ssl": true,
  "auth": {
    "client_id": "prod-client-id",
    "issuer": "https://auth.company.com"
  },
  "logging": {
    "level": "WARN"
  }
}
```

## Configuration Management Commands

### View Configuration

```bash
# Show current configuration
./rag-cli config show

# Show specific section
./rag-cli config show auth

# Show configuration for specific profile
./rag-cli config show --profile prod

# Show configuration as JSON
./rag-cli config show --format json
```

### Set Configuration Values

```bash
# Set global configuration
./rag-cli config set api_url "http://localhost:8000"

# Set profile-specific value
./rag-cli config set auth.client_id "new-client-id" --profile dev

# Set nested configuration
./rag-cli config set search.max_chunks 10
./rag-cli config set output.format "json"

# Set multiple values
./rag-cli config set api_url "http://localhost:8000" timeout 45
```

### Unset Configuration Values

```bash
# Remove configuration value (revert to default)
./rag-cli config unset auth.client_secret

# Remove entire section
./rag-cli config unset search

# Remove profile-specific value
./rag-cli config unset api_url --profile staging
```

### Profile Management

```bash
# List all profiles
./rag-cli config profiles

# Create new profile
./rag-cli config create-profile staging

# Switch active profile
./rag-cli config use-profile prod

# Copy profile
./rag-cli config copy-profile dev staging

# Delete profile
./rag-cli config delete-profile old-profile
```

### Configuration Validation

```bash
# Test configuration
./rag-cli config test

# Test specific profile
./rag-cli config test --profile prod

# Test connectivity
./rag-cli config test-connection

# Validate configuration syntax
./rag-cli config validate
```

## Configuration Sections

### API Configuration

```bash
# Backend API settings
./rag-cli config set api_url "https://your-api.com"
./rag-cli config set timeout 30
./rag-cli config set verify_ssl true
./rag-cli config set retry_attempts 3
./rag-cli config set retry_delay 1.0
```

### Authentication Configuration

```bash
# OIDC authentication settings
./rag-cli config set auth.provider "ibm"
./rag-cli config set auth.client_id "your-client-id"
./rag-cli config set auth.client_secret "your-client-secret"
./rag-cli config set auth.issuer "https://your-oidc-provider.com"
./rag-cli config set auth.scope "openid profile email"
./rag-cli config set auth.redirect_uri "http://localhost:8080/callback"

# Token management
./rag-cli config set auth.auto_refresh true
./rag-cli config set auth.refresh_buffer 300
./rag-cli config set auth.token_cache_ttl 3600
```

### Output Configuration

```bash
# Output formatting
./rag-cli config set output.format "table"  # table, json, yaml, csv
./rag-cli config set output.colors true
./rag-cli config set output.verbose false
./rag-cli config set output.pager "less"
./rag-cli config set output.max_width 120
```

### Search Configuration

```bash
# Default search parameters
./rag-cli config set search.max_chunks 5
./rag-cli config set search.similarity_threshold 0.7
./rag-cli config set search.default_model "gpt-3.5-turbo"
./rag-cli config set search.temperature 0.1
./rag-cli config set search.max_tokens 512
./rag-cli config set search.include_sources true
```

### Collection Configuration

```bash
# Default collection settings
./rag-cli config set collections.default_vector_db "milvus"
./rag-cli config set collections.default_chunk_size 512
./rag-cli config set collections.default_chunk_overlap 50
./rag-cli config set collections.default_private false
./rag-cli config set collections.auto_optimize_chunks true
```

### Document Configuration

```bash
# Document processing settings
./rag-cli config set documents.auto_title false
./rag-cli config set documents.batch_size 5
./rag-cli config set documents.max_file_size "50MB"
./rag-cli config set documents.parallel_uploads true
./rag-cli config set documents.retry_failed true
```

### Cache Configuration

```bash
# Caching settings
./rag-cli config set cache.enabled true
./rag-cli config set cache.ttl 3600
./rag-cli config set cache.max_size "1GB"
./rag-cli config set cache.compression true
```

### Logging Configuration

```bash
# Logging settings
./rag-cli config set logging.level "INFO"  # DEBUG, INFO, WARN, ERROR
./rag-cli config set logging.file "~/.rag/logs/cli.log"
./rag-cli config set logging.max_size "10MB"
./rag-cli config set logging.backup_count 5
./rag-cli config set logging.format "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## Environment Variables

Override configuration using environment variables:

### API Configuration
```bash
export RAG_API_URL="http://localhost:8000"
export RAG_API_TIMEOUT="30"
export RAG_API_VERIFY_SSL="true"
```

### Authentication
```bash
export RAG_AUTH_CLIENT_ID="your-client-id"
export RAG_AUTH_CLIENT_SECRET="your-client-secret"
export RAG_AUTH_ISSUER="https://your-oidc-provider.com"
export RAG_AUTH_SCOPE="openid profile email"
```

### Output and Behavior
```bash
export RAG_OUTPUT_FORMAT="json"
export RAG_OUTPUT_VERBOSE="true"
export RAG_DEBUG="true"
export RAG_PROFILE="production"
```

### Directory Locations
```bash
export RAG_CONFIG_DIR="$HOME/.rag"
export RAG_CACHE_DIR="$HOME/.rag/cache"
export RAG_LOG_DIR="$HOME/.rag/logs"
```

## Advanced Configuration

### Custom Configuration Templates

Create configuration templates for common setups:

```bash
# Save current configuration as template
./rag-cli config export-template "development" > dev-template.json

# Apply template to new profile
./rag-cli config import-template staging dev-template.json
```

**Template Example (`dev-template.json`):**
```json
{
  "template_name": "development",
  "description": "Development environment configuration",
  "config": {
    "api_url": "http://localhost:8000",
    "timeout": 60,
    "verify_ssl": false,
    "auth": {
      "client_id": "dev-client-id",
      "auto_refresh": true
    },
    "logging": {
      "level": "DEBUG"
    },
    "output": {
      "verbose": true,
      "colors": true
    }
  }
}
```

### Configuration Inheritance

Set up configuration inheritance for shared settings:

```bash
# Create base configuration
./rag-cli config create-profile base
./rag-cli config set auth.provider "ibm" --profile base
./rag-cli config set output.colors true --profile base

# Create derived profiles
./rag-cli config create-profile dev --inherit base
./rag-cli config set api_url "http://localhost:8000" --profile dev

./rag-cli config create-profile prod --inherit base
./rag-cli config set api_url "https://api.company.com" --profile prod
```

### Dynamic Configuration

Use configuration scripts for dynamic settings:

```bash
#!/bin/bash
# dynamic-config.sh - Set configuration based on environment

if [ "$ENVIRONMENT" = "development" ]; then
    ./rag-cli config set api_url "http://localhost:8000"
    ./rag-cli config set logging.level "DEBUG"
    ./rag-cli config set verify_ssl false
elif [ "$ENVIRONMENT" = "production" ]; then
    ./rag-cli config set api_url "https://api.company.com"
    ./rag-cli config set logging.level "WARN"
    ./rag-cli config set verify_ssl true
fi

# Set common settings
./rag-cli config set auth.client_id "$OIDC_CLIENT_ID"
./rag-cli config set timeout 30
```

### Configuration Encryption

Encrypt sensitive configuration values:

```bash
# Encrypt sensitive values
./rag-cli config encrypt auth.client_secret "your-secret-value"

# Decrypt for use (happens automatically)
./rag-cli config show auth.client_secret --decrypt
```

## Configuration Best Practices

### Security

1. **Protect Sensitive Data**:
```bash
# Use environment variables for secrets
export RAG_AUTH_CLIENT_SECRET="secret-value"

# Or encrypt in configuration
./rag-cli config encrypt auth.client_secret "secret-value"

# Set appropriate file permissions
chmod 600 ~/.rag/config.json
```

2. **Separate Environments**:
```bash
# Use different profiles for different environments
./rag-cli config create-profile dev
./rag-cli config create-profile staging
./rag-cli config create-profile prod
```

3. **Regular Backups**:
```bash
# Backup configuration
./rag-cli config backup ~/config-backup-$(date +%Y%m%d).json

# Version control (without secrets)
git add ~/.rag/config-template.json
```

### Performance

1. **Optimize Timeouts**:
```bash
# Adjust based on network conditions
./rag-cli config set timeout 30          # Fast networks
./rag-cli config set timeout 60          # Slow networks
./rag-cli config set retry_attempts 3    # Network reliability
```

2. **Configure Caching**:
```bash
# Enable caching for better performance
./rag-cli config set cache.enabled true
./rag-cli config set cache.ttl 3600
./rag-cli config set cache.max_size "1GB"
```

3. **Batch Operations**:
```bash
# Optimize batch sizes
./rag-cli config set documents.batch_size 10    # Fast systems
./rag-cli config set documents.batch_size 5     # Slower systems
```

### Maintenance

1. **Regular Validation**:
```bash
#!/bin/bash
# config-health-check.sh
echo "🔧 Configuration Health Check"
echo "============================"

./rag-cli config validate
./rag-cli config test-connection

# Check for deprecated settings
./rag-cli config check-deprecated

# Clean up old cache
./rag-cli config clean-cache --older-than 7d
```

2. **Configuration Monitoring**:
```bash
#!/bin/bash
# Monitor configuration changes
inotifywait -m ~/.rag/config.json -e modify |
while read path action file; do
    echo "Configuration changed: $file"
    ./rag-cli config validate
done
```

## Configuration Examples

### Complete Development Setup

```bash
#!/bin/bash
# setup-dev-config.sh

echo "Setting up development configuration..."

# Create development profile
./rag-cli config create-profile dev

# API settings
./rag-cli config set api_url "http://localhost:8000" --profile dev
./rag-cli config set timeout 60 --profile dev
./rag-cli config set verify_ssl false --profile dev

# Authentication
./rag-cli config set auth.client_id "dev-client-id" --profile dev
./rag-cli config set auth.issuer "https://dev-auth.company.com" --profile dev

# Development-friendly settings
./rag-cli config set output.verbose true --profile dev
./rag-cli config set logging.level "DEBUG" --profile dev
./rag-cli config set cache.enabled false --profile dev

# Search settings
./rag-cli config set search.max_chunks 3 --profile dev
./rag-cli config set search.include_sources true --profile dev

echo "✅ Development configuration ready"
echo "Switch to dev profile: ./rag-cli config use-profile dev"
```

### Production Setup

```bash
#!/bin/bash
# setup-prod-config.sh

echo "Setting up production configuration..."

# Create production profile
./rag-cli config create-profile prod

# API settings
./rag-cli config set api_url "https://rag-api.company.com" --profile prod
./rag-cli config set timeout 30 --profile prod
./rag-cli config set verify_ssl true --profile prod
./rag-cli config set retry_attempts 3 --profile prod

# Authentication
./rag-cli config set auth.client_id "$PROD_CLIENT_ID" --profile prod
./rag-cli config set auth.issuer "https://auth.company.com" --profile prod
./rag-cli config set auth.auto_refresh true --profile prod

# Production settings
./rag-cli config set output.verbose false --profile prod
./rag-cli config set logging.level "WARN" --profile prod
./rag-cli config set cache.enabled true --profile prod

# Optimize for production
./rag-cli config set documents.batch_size 10 --profile prod
./rag-cli config set search.max_chunks 5 --profile prod

echo "✅ Production configuration ready"
echo "Switch to prod profile: ./rag-cli config use-profile prod"
```

### Multi-Tenant Setup

```bash
#!/bin/bash
# setup-multi-tenant.sh

tenants=("tenant-a" "tenant-b" "tenant-c")

for tenant in "${tenants[@]}"; do
    echo "Setting up configuration for: $tenant"

    # Create tenant-specific profile
    ./rag-cli config create-profile "$tenant"

    # Tenant-specific API endpoint
    ./rag-cli config set api_url "https://${tenant}.rag-api.com" --profile "$tenant"

    # Tenant-specific authentication
    ./rag-cli config set auth.client_id "${tenant}-client-id" --profile "$tenant"
    ./rag-cli config set auth.issuer "https://${tenant}.auth.com" --profile "$tenant"

    # Tenant-specific cache directory
    ./rag-cli config set cache.directory "~/.rag/cache/${tenant}" --profile "$tenant"

    echo "✅ $tenant configuration ready"
done

echo ""
echo "Switch between tenants:"
for tenant in "${tenants[@]}"; do
    echo "  ./rag-cli config use-profile $tenant"
done
```

## Configuration Migration

### Upgrading Configuration

When upgrading the CLI, migrate configuration as needed:

```bash
#!/bin/bash
# migrate-config.sh

echo "🔄 Migrating configuration..."

# Backup existing configuration
./rag-cli config backup ~/.rag/config-backup-$(date +%Y%m%d).json

# Check for migration needs
./rag-cli config check-migration

# Apply migrations
./rag-cli config migrate

# Validate migrated configuration
./rag-cli config validate

echo "✅ Configuration migration completed"
```

### Exporting and Importing Configuration

```bash
# Export configuration (without secrets)
./rag-cli config export --safe config-export.json

# Import configuration
./rag-cli config import config-export.json

# Export specific profile
./rag-cli config export --profile prod prod-config.json

# Import into specific profile
./rag-cli config import prod-config.json --profile staging
```

## Troubleshooting Configuration

### Common Configuration Issues

1. **Invalid JSON Syntax**:
```bash
$ ./rag-cli config show
❌ Configuration error: Invalid JSON syntax in ~/.rag/config.json

Fix: ./rag-cli config validate --fix-syntax
```

2. **Missing Required Settings**:
```bash
$ ./rag-cli auth login
❌ Configuration error: Missing required setting 'auth.client_id'

Fix: ./rag-cli config set auth.client_id "your-client-id"
```

3. **Profile Not Found**:
```bash
$ ./rag-cli config use-profile nonexistent
❌ Profile 'nonexistent' not found

Available profiles: ./rag-cli config profiles
```

### Configuration Debugging

```bash
# Debug configuration loading
./rag-cli --debug config show

# Test configuration values
./rag-cli config test --verbose

# Check configuration precedence
./rag-cli config explain api_url
```

## Next Steps

After configuring the CLI:
1. **[Troubleshooting](troubleshooting.md)** - Resolve common issues
2. **[Authentication](authentication.md)** - Set up authentication
3. **[Commands Overview](commands/index.md)** - Learn available commands
4. **Advanced Usage** - Integration and automation examples
