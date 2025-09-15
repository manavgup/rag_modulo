# Installation Guide

This guide covers the complete installation process for the RAG CLI, from system requirements to verification steps.

## System Requirements

### Operating Systems
- **Linux**: Ubuntu 20.04+, CentOS 8+, or equivalent
- **macOS**: 10.15+ (Catalina or newer)
- **Windows**: Windows 10+ with WSL2 (recommended) or PowerShell

### Dependencies
- **Python**: 3.8 or higher
- **Poetry**: 1.4.0 or higher (for dependency management)
- **Git**: For source installation

### Hardware Requirements
- **Memory**: Minimum 4GB RAM (8GB+ recommended for large document processing)
- **Storage**: 2GB free space for installation and document cache
- **Network**: Stable internet connection for authentication and API calls

## Installation Methods

### Method 1: Source Installation (Recommended)

This method installs from the source repository and is recommended for development and customization.

```bash
# 1. Clone the repository
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo/backend

# 2. Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# 3. Install dependencies
poetry install

# 4. Activate the virtual environment
poetry shell

# 5. Verify installation
./rag-cli --version
```

### Method 2: Development Installation

For contributors and developers who need the full development environment:

```bash
# 1. Clone and navigate
git clone https://github.com/manavgup/rag_modulo.git
cd rag_modulo/backend

# 2. Install with development dependencies
poetry install --with dev,test

# 3. Install pre-commit hooks (optional)
poetry run pre-commit install

# 4. Activate environment
poetry shell

# 5. Run tests to verify installation
poetry run pytest tests/unit/test_cli_unit.py -v
```

### Method 3: Container Installation

Run the CLI in a containerized environment:

```bash
# 1. Build the container
docker build -f Dockerfile.cli -t rag-cli .

# 2. Create an alias for easy usage
echo 'alias rag-cli="docker run --rm -it -v ~/.rag:/root/.rag rag-cli"' >> ~/.bashrc
source ~/.bashrc

# 3. Verify installation
rag-cli --version
```

## Post-Installation Setup

### 1. Create Configuration Directory

```bash
# The CLI will create this automatically, but you can pre-create it
mkdir -p ~/.rag
```

### 2. Set Up Backend Connection

Configure the CLI to connect to your RAG backend:

```bash
# For local development
./rag-cli config set-url http://localhost:8000

# For remote deployment
./rag-cli config set-url https://your-rag-instance.com

# Verify connection
./rag-cli config show
```

### 3. Test Basic Functionality

```bash
# Check backend connectivity
./rag-cli auth status

# Should return: "Not authenticated" (expected for fresh installation)
```

## Environment-Specific Setup

### Development Environment

```bash
# 1. Set development profile
./rag-cli config set-profile dev

# 2. Configure development backend
./rag-cli config set-url http://localhost:8000 --profile dev

# 3. Set development timeouts
./rag-cli config set-timeout 60 --profile dev
```

### Production Environment

```bash
# 1. Set production profile
./rag-cli config set-profile prod

# 2. Configure production backend
./rag-cli config set-url https://rag-api.yourcompany.com --profile prod

# 3. Set production timeouts
./rag-cli config set-timeout 30 --profile prod

# 4. Enable TLS verification
./rag-cli config set verify-tls true --profile prod
```

## Verification Steps

### 1. Version Check
```bash
./rag-cli --version
# Expected output: RAG CLI v1.0.0
```

### 2. Help System
```bash
./rag-cli --help
# Should display comprehensive help information
```

### 3. Configuration Verification
```bash
./rag-cli config show
# Should display current configuration
```

### 4. Backend Connectivity
```bash
# This will test if the backend is reachable
./rag-cli auth status
```

## Troubleshooting Installation

### Common Issues

#### Poetry Not Found
```bash
# Add Poetry to PATH (adjust for your shell)
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

#### Permission Errors
```bash
# Ensure proper permissions for the CLI script
chmod +x ./rag-cli

# Or run with Poetry
poetry run python -m rag_solution.cli.main --help
```

#### Python Version Issues
```bash
# Check Python version
python --version

# Use specific Python version with Poetry
poetry env use python3.9
poetry install
```

#### Dependencies Conflicts
```bash
# Clear Poetry cache and reinstall
poetry cache clear --all PyPI
poetry install --no-cache
```

### Network Issues

#### Backend Connection Failures
```bash
# Test backend manually
curl -I http://localhost:8000/health

# Check firewall settings
# Linux/macOS: Check iptables/pfctl rules
# Windows: Check Windows Firewall settings
```

#### SSL/TLS Issues
```bash
# Disable TLS verification temporarily (development only)
./rag-cli config set verify-tls false

# Update certificates
# macOS: Update via System Preferences
# Linux: sudo apt update && sudo apt install ca-certificates
```

## Updating the CLI

### Update from Source
```bash
cd rag_modulo
git pull origin main
cd backend
poetry install
```

### Check for Updates
```bash
./rag-cli version check-updates
```

## Uninstallation

### Remove CLI Installation
```bash
# Remove virtual environment
poetry env remove python

# Remove configuration (optional)
rm -rf ~/.rag

# Remove source code (if desired)
rm -rf /path/to/rag_modulo
```

## Next Steps

After successful installation:

1. **[Authentication Setup](authentication.md)** - Configure IBM OIDC authentication
2. **[Configuration Guide](configuration.md)** - Customize CLI behavior
3. **[Commands Overview](commands/index.md)** - Learn available commands
4. **[Quick Start Tutorial](index.md#quick-start)** - Try your first operations

## Support

If you encounter installation issues:

1. Check our [Troubleshooting Guide](troubleshooting.md)
2. Search existing [GitHub Issues](https://github.com/manavgup/rag_modulo/issues)
3. Create a new issue with installation logs and system information
