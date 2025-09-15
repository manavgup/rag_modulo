# GitHub Codespaces Development

This guide explains how to use GitHub Codespaces for development with RAG Modulo.

## What is GitHub Codespaces?

GitHub Codespaces provides cloud-based development environments that run in your browser. It uses the same Dev Container configuration as your local development, ensuring consistency across all environments.

## Quick Start

### 1. Create a Codespace

1. **Go to your GitHub repository**
2. **Click "Code" button**
3. **Click "Codespaces" tab**
4. **Click "Create codespace on main"** (or your current branch)

### 2. Wait for Setup (2-3 minutes)

The Codespace will:
- ✅ Build the Dev Container
- ✅ Install all dependencies
- ✅ Configure VS Code extensions
- ✅ Set up the development environment

### 3. Start Development

```bash
# In Codespace terminal
root ➜ /workspace $ make dev-up
root ➜ /workspace $ make dev-validate
```

## Codespaces Benefits

### ✅ Consistent Environment
- **Same Dev Container** as local development
- **Same VS Code extensions** and settings
- **Same development tools** (make, git, curl, etc.)
- **Same Python environment** and dependencies

### ✅ Zero Local Setup
- **No Docker Desktop** required
- **No VS Code installation** required
- **No Python installation** required
- **Just a web browser!**

### ✅ Cross-Platform
- **Works on any device** (Windows, Mac, Linux, Chromebook, iPad)
- **Same experience** everywhere
- **No platform-specific issues**

### ✅ Team Collaboration
- **Share Codespaces** with team members
- **Consistent onboarding** for new developers
- **Easy debugging** and pair programming

## Development Workflow

### Typical Codespace Session

```bash
# 1. Create Codespace (once)
# 2. Start development environment
root ➜ /workspace $ make dev-up

# 3. Edit code in VS Code (browser)
# 4. Test changes immediately
# 5. Commit and push changes
```

### Hot Reloading in Codespaces

- ✅ **Backend changes**: Edit Python files → Save → Test immediately
- ✅ **Frontend changes**: Edit React files → Save → Browser updates
- ✅ **No restarts needed** for most changes

## Port Forwarding

Codespaces automatically forwards ports to your browser:

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000
- **MLflow**: http://localhost:5001

## VS Code Features

### ✅ Full VS Code Experience
- **IntelliSense** and code completion
- **Debugging** with breakpoints
- **Git integration** with GitHub
- **Terminal** with full shell access
- **File explorer** and search

### ✅ Pre-configured Extensions
- **Python** (Pylance, debugging)
- **Ruff** (linting and formatting)
- **Docker** (container management)
- **GitHub Copilot** (AI code completion)
- **Jupyter** (notebook support)

## Environment Variables

The Codespace automatically sets:
- `DEVELOPMENT_MODE=true`
- `TESTING=true`
- `SKIP_AUTH=true`
- `PYTHONPATH=/app:/app/rag_solution:/app/vectordbs`

## Docker Commands

All Docker commands work in Codespaces:

```bash
# Build development images
root ➜ /workspace $ make dev-build

# Start services
root ➜ /workspace $ make dev-up

# Check status
root ➜ /workspace $ make dev-status

# View logs
root ➜ /workspace $ make dev-logs

# Validate environment
root ➜ /workspace $ make dev-validate
```

## Troubleshooting

### Common Issues

#### 1. Codespace Creation Fails
- **Check repository permissions** (public or you have access)
- **Verify Dev Container configuration** (`.devcontainer/devcontainer.json`)
- **Try creating on a different branch**

#### 2. Services Not Starting
```bash
# Check if Docker is running
root ➜ /workspace $ docker ps

# Restart development environment
root ➜ /workspace $ make dev-down && make dev-up
```

#### 3. Port Forwarding Issues
- **Check port forwarding** in Codespace settings
- **Verify services are running** on correct ports
- **Try accessing via Codespace URL** instead of localhost

### Performance Tips

- **Use smaller Codespace** for simple tasks
- **Stop unused services** to save resources
- **Clean up Docker images** periodically
- **Use Codespace prebuilds** for faster startup

## Cost Considerations

- **Codespaces are billed** by usage (CPU, memory, storage)
- **Stop Codespaces** when not in use
- **Use appropriate machine size** for your needs
- **Consider prebuilds** for frequently used environments

## Integration with Local Development

### Seamless Workflow
- **Local development**: Use VS Code + Dev Container
- **Cloud development**: Use Codespaces
- **Same configuration**: Both use `.devcontainer/devcontainer.json`
- **Same commands**: All `make` targets work in both

### When to Use Each

#### Use Local Development When:
- **Fast iteration** needed
- **Offline development** required
- **Cost is a concern**
- **Full control** over environment

#### Use Codespaces When:
- **Team collaboration** needed
- **Consistent environment** required
- **Cross-platform** development
- **Easy onboarding** for new developers

## Advanced Features

### Codespace Prebuilds
- **Faster startup** times
- **Pre-installed dependencies**
- **Custom machine images**
- **Team-wide consistency**

### Codespace Secrets
- **Environment variables** from GitHub Secrets
- **API keys** and credentials
- **Database connections**
- **Secure configuration**

### Codespace Lifecycle
- **Automatic shutdown** after inactivity
- **Persistent storage** for data
- **Snapshot and restore** capabilities
- **Export and import** configurations

## Best Practices

### Creation Methods

#### Manual Creation (Recommended for Development)
- **Daily development work** - Create Codespaces manually for coding
- **Debugging sessions** - Use for troubleshooting issues
- **Code reviews** - Create for PR review and testing
- **Team collaboration** - Share Codespaces for pair programming

#### Automated Creation (CI/CD Integration)
- **PR validation** - Automatically create Codespaces for PRs
- **Automated testing** - Run tests in Codespace environment
- **Environment validation** - Ensure Dev Container works
- **Documentation generation** - Build docs in Codespace

### Development
- **Commit frequently** to save work
- **Use branches** for feature development
- **Test in Codespace** before merging
- **Clean up resources** when done

### Team Collaboration
- **Share Codespaces** for debugging
- **Use consistent naming** for Codespaces
- **Document environment** requirements
- **Train team members** on Codespace usage

### Security
- **Use GitHub Secrets** for sensitive data
- **Limit Codespace access** to team members
- **Regular security updates** in Dev Container
- **Monitor Codespace usage** and costs

## Automated Codespace Workflows

### PR Validation Workflow
The project includes automated Codespace creation for PRs:

```yaml
# .github/workflows/pr-codespace.yml
# Automatically creates Codespace for PR review
# Comments on PR with Codespace URL
# Validates Dev Container configuration
```

### Testing Workflow
Automated testing in Codespace environment:

```yaml
# .github/workflows/codespace-testing.yml
# Runs tests in Codespace environment
# Validates hot reloading functionality
# Tests CLI commands
```

### Validation Workflow
Ensures Dev Container configuration works:

```yaml
# .github/workflows/codespace-validation.yml
# Validates Dev Container setup
# Tests development workflow commands
# Ensures all tools are available
```

---

*GitHub Codespaces provides a powerful cloud-based development environment that maintains consistency with your local Dev Container setup while enabling seamless team collaboration.*
