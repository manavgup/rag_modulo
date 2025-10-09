# Jules Secrets Configuration Guide

This guide explains how to securely configure Docker Hub credentials and other secrets in Jules.

## 🔐 Current Configuration

The `config-with-docker.yaml` now includes Docker Hub authentication to avoid rate limits.

### ⚠️ Security Warning

**Current State**: Credentials are hardcoded in `config-with-docker.yaml`
```yaml
environment:
  DOCKER_HUB_USERNAME: "your-docker-hub-username"
  DOCKER_HUB_TOKEN: "dckr_pat_YOUR_TOKEN_HERE"
```

**This is OK for:**
- ✅ Quick setup and testing
- ✅ Personal development environments
- ✅ Private Jules workspaces

**This is NOT OK for:**
- ❌ Public repositories
- ❌ Shared team environments
- ❌ Production deployments

## 🎯 Better Approach: Jules Secrets (Recommended)

### Option 1: Use Jules Secrets UI (If Available)

If Jules supports a secrets management UI:

1. Go to Jules workspace settings → Secrets
2. Add secrets:
   - Name: `DOCKER_HUB_USERNAME`, Value: `your-docker-hub-username`
   - Name: `DOCKER_HUB_TOKEN`, Value: `dckr_pat_YOUR_TOKEN_HERE`

3. Update `config-with-docker.yaml`:
   ```yaml
   environment:
     JULES_ENVIRONMENT: "true"
     DEVELOPMENT_MODE: "true"
     DOCKER_ENABLED: "true"

     # Docker Hub credentials - set via Jules Secrets UI
     # DOCKER_HUB_USERNAME: set in Jules Secrets
     # DOCKER_HUB_TOKEN: set in Jules Secrets
   ```

4. Jules will automatically inject these as environment variables

### Option 2: Environment Variables (Current Approach)

**For immediate use** (what we just did):

Keep credentials in `config-with-docker.yaml` but:

1. ✅ **Rotate the token after initial setup**
2. ✅ **Use short expiration** (30 days)
3. ✅ **Don't commit to public repos**
4. ✅ **Revoke if compromised**

### Option 3: Runtime Authentication

Authenticate manually after Jules setup completes:

1. Update `config-with-docker.yaml` to remove credentials:
   ```yaml
   environment:
     JULES_ENVIRONMENT: "true"
     DEVELOPMENT_MODE: "true"
     DOCKER_ENABLED: "true"
     # No Docker Hub credentials here
   ```

2. After Jules setup, manually authenticate:
   ```bash
   echo "dckr_pat_YOUR_TOKEN" | docker login -u your-docker-hub-username --password-stdin
   cd /app
   docker compose -f docker-compose-infra.yml pull
   docker compose -f docker-compose-infra.yml up -d
   ```

## 🔄 Token Rotation Best Practices

### When to Rotate

Rotate your Docker Hub token:
- ✅ Every 30-90 days (set expiration when creating)
- ✅ After sharing in chat/support (like we just did!)
- ✅ When team member leaves
- ✅ If token appears in logs
- ✅ On suspected compromise

### How to Rotate

1. **Create new token**:
   - Go to: https://app.docker.com/settings/personal-access-tokens
   - Generate new token with same permissions
   - Copy the new token

2. **Update configuration**:
   ```yaml
   # In .jules/config-with-docker.yaml
   DOCKER_HUB_TOKEN: "dckr_pat_NEW_TOKEN_HERE"
   ```

3. **Delete old token**:
   - Go back to Docker Hub settings
   - Find old token
   - Click Delete

4. **Test new token**:
   ```bash
   echo "dckr_pat_NEW_TOKEN" | docker login -u your-docker-hub-username --password-stdin
   docker pull hello-world
   ```

## 🔒 Security Best Practices

### For Docker Hub Tokens

1. **Principle of Least Privilege**:
   - Only grant "Read" permission if you're just pulling images
   - Use "Read, Write" only if you need to push images

2. **Short Expiration**:
   - Development: 30 days
   - Production: Automated rotation every 90 days

3. **Separate Tokens**:
   - Different token for each environment
   - Different token for each developer
   - Different token for CI/CD

4. **Monitor Usage**:
   - Check Docker Hub settings → Access Tokens
   - Review "Last used" dates
   - Revoke unused tokens

### For Other Secrets in Jules

The same principles apply to other credentials:

```yaml
environment:
  # WatsonX credentials
  WATSONX_APIKEY: "your-watsonx-key"
  WATSONX_INSTANCE_ID: "your-instance-id"

  # OpenAI credentials (for podcasts)
  OPENAI_API_KEY: "sk-proj-..."

  # Database credentials
  COLLECTIONDB_PASS: "secure-password"
```

**Best practices**:
- ✅ Use Jules Secrets UI if available
- ✅ Rotate credentials regularly
- ✅ Use different credentials for dev/prod
- ✅ Never commit to public repos
- ✅ Use `.gitignore` for sensitive config files

## 📋 Immediate Action Items

### After Initial Setup (Do This Now!)

Since you shared your token in this conversation:

1. **Verify setup works**:
   ```bash
   cd /app
   docker compose -f docker-compose-infra.yml ps
   # All services should be "Up"
   ```

2. **Rotate the token** (recommended):
   - Create new token: https://app.docker.com/settings/personal-access-tokens
   - Update `.jules/config-with-docker.yaml` with new token
   - Delete old token: `dckr_pat_YOUR_TOKEN_HERE`

3. **Test application**:
   ```bash
   make local-dev-backend
   # Visit: http://localhost:8000/docs
   ```

## 🔍 Troubleshooting

### "Login Succeeded" but still hitting rate limits

**Cause**: Docker not using stored credentials
**Solution**:
```bash
# Verify authentication
docker info | grep Username
# Should show: Username: your-docker-hub-username

# Check stored credentials
cat ~/.docker/config.json
# Should contain auth token
```

### "unauthorized: incorrect username or password"

**Cause**: Token expired or revoked
**Solution**:
```bash
# Create new token at Docker Hub
# Update config-with-docker.yaml
# Re-authenticate
echo "NEW_TOKEN" | docker login -u your-docker-hub-username --password-stdin
```

### Environment variables not set

**Cause**: Jules didn't load config properly
**Solution**:
```bash
# Check if variables are set
echo $DOCKER_HUB_USERNAME
echo $DOCKER_HUB_TOKEN

# If empty, manually set them
export DOCKER_HUB_USERNAME="your-docker-hub-username"
export DOCKER_HUB_TOKEN="dckr_pat_YOUR_TOKEN"

# Re-run setup script
./.jules/setup-with-docker.sh
```

## 📚 Additional Resources

- **Docker Hub Tokens**: https://docs.docker.com/security/for-developers/access-tokens/
- **Jules Documentation**: https://jules.google/docs/environment/
- **GitHub Secrets**: https://docs.github.com/en/actions/security-guides/encrypted-secrets
- **Security Best Practices**: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html

## ✅ Quick Reference

### Current Token Info
- **Username**: `your-docker-hub-username`
- **Token**: `dckr_pat_YOUR_TOKEN_HERE`
- **Status**: ⚠️ Shared in conversation, should be rotated
- **Action**: Rotate after initial setup completes

### Token Management URLs
- **Create/View Tokens**: https://app.docker.com/settings/personal-access-tokens
- **Account Settings**: https://app.docker.com/settings/general
- **Usage Stats**: https://app.docker.com/settings/billing

### Quick Commands
```bash
# Login
echo "TOKEN" | docker login -u your-docker-hub-username --password-stdin

# Verify
docker info | grep Username

# Test
docker pull hello-world

# Logout
docker logout
```
