# Commands Overview

The RAG CLI provides a comprehensive set of commands for managing your RAG system. Commands are organized into logical groups for different aspects of the system.

## Command Structure

All CLI commands follow a consistent structure:

```bash
./rag-cli [global-options] <group> <command> [command-options] [arguments]
```

### Global Options

Available with all commands:

- `--profile PROFILE`: Use specific configuration profile
- `--verbose`: Enable verbose output
- `--quiet`: Suppress non-error output
- `--debug`: Enable debug logging
- `--help`: Show help information

## Command Groups

### 🔐 [Authentication Commands](auth.md)

Manage authentication and user sessions:

```bash
./rag-cli auth login          # Authenticate with IBM OIDC
./rag-cli auth status         # Check authentication status
./rag-cli auth logout         # Log out and clear tokens
./rag-cli auth whoami         # Show current user info
./rag-cli auth refresh        # Refresh authentication token
```

### 📚 [Collection Commands](collections.md)

Manage document collections:

```bash
./rag-cli collections list                    # List all collections
./rag-cli collections create "My Collection"  # Create new collection
./rag-cli collections get COLLECTION_ID       # Get collection details
./rag-cli collections update COLLECTION_ID    # Update collection settings
./rag-cli collections delete COLLECTION_ID    # Delete collection
```

### 📄 [Document Commands](documents.md)

Manage documents within collections:

```bash
./rag-cli documents list COLLECTION_ID                    # List documents
./rag-cli documents upload COLLECTION_ID file.pdf         # Upload document
./rag-cli documents download COLLECTION_ID DOCUMENT_ID    # Download document
./rag-cli documents delete COLLECTION_ID DOCUMENT_ID      # Delete document
./rag-cli documents reprocess COLLECTION_ID DOCUMENT_ID   # Reprocess document
```

### 🔍 [Search Commands](search.md)

Perform searches and RAG queries:

```bash
./rag-cli search query COLLECTION_ID "your question"      # RAG query
./rag-cli search similar COLLECTION_ID "text to match"    # Similarity search
./rag-cli search history                                   # Search history
./rag-cli search explain QUERY_ID                         # Explain search results
```

### 👥 [User Commands](users.md)

Manage users and permissions (admin only):

```bash
./rag-cli users list                    # List all users
./rag-cli users get USER_ID             # Get user details
./rag-cli users create                  # Create new user
./rag-cli users update USER_ID          # Update user settings
./rag-cli users delete USER_ID          # Delete user
```

## Quick Reference

### Most Common Commands

```bash
# 1. Initial setup
./rag-cli auth login
./rag-cli auth status

# 2. Create and populate collection
./rag-cli collections create "Knowledge Base"
./rag-cli documents upload COLLECTION_ID document.pdf

# 3. Search and query
./rag-cli search query COLLECTION_ID "What is machine learning?"
./rag-cli search similar COLLECTION_ID "artificial intelligence"

# 4. Manage collections
./rag-cli collections list
./rag-cli collections get COLLECTION_ID
./rag-cli documents list COLLECTION_ID
```

### Command Chaining Examples

```bash
# Create collection and upload multiple documents
COLLECTION_ID=$(./rag-cli collections create "Research Papers" --output-id)
./rag-cli documents upload $COLLECTION_ID paper1.pdf paper2.pdf paper3.pdf

# Search multiple collections
for collection in collection1 collection2 collection3; do
    ./rag-cli search query $collection "your query" --max-results 3
done

# Backup collection data
./rag-cli collections get COLLECTION_ID --export > collection-backup.json
./rag-cli documents list COLLECTION_ID --export > documents-backup.json
```

## Output Formats

Most commands support multiple output formats:

### Table Format (Default)
```bash
./rag-cli collections list
```
```
┌──────────────────────┬─────────────────┬────────────┬───────────┐
│ ID                   │ Name            │ Documents  │ Status    │
├──────────────────────┼─────────────────┼────────────┼───────────┤
│ col_123abc           │ Knowledge Base  │ 15         │ Active    │
│ col_456def           │ Research Papers │ 8          │ Processing│
└──────────────────────┴─────────────────┴────────────┴───────────┘
```

### JSON Format
```bash
./rag-cli collections list --format json
```
```json
{
  "collections": [
    {
      "id": "col_123abc",
      "name": "Knowledge Base",
      "document_count": 15,
      "status": "active",
      "created_at": "2024-01-10T10:00:00Z"
    }
  ],
  "total": 1
}
```

### CSV Format
```bash
./rag-cli collections list --format csv
```
```csv
id,name,document_count,status,created_at
col_123abc,Knowledge Base,15,active,2024-01-10T10:00:00Z
col_456def,Research Papers,8,processing,2024-01-10T11:00:00Z
```

## Error Handling

The CLI provides clear error messages and exit codes:

### Exit Codes
- `0`: Success
- `1`: General error
- `2`: Authentication error
- `3`: Network error
- `4`: Configuration error
- `5`: Permission error

### Error Examples

```bash
# Authentication required
$ ./rag-cli collections list
❌ Error: Authentication required. Run 'rag-cli auth login' first.
Exit code: 2

# Invalid collection ID
$ ./rag-cli collections get invalid-id
❌ Error: Collection 'invalid-id' not found.
Exit code: 1

# Network connectivity issue
$ ./rag-cli auth login
❌ Error: Unable to connect to backend at http://localhost:8000
Exit code: 3
```

## Configuration Integration

Commands respect configuration settings:

```bash
# Set default output format
./rag-cli config set output.format json

# Set default timeout
./rag-cli config set api.timeout 60

# Use specific profile
./rag-cli --profile production collections list
```

## Scripting and Automation

The CLI is designed for scripting:

### Silent Mode
```bash
# Check authentication without output
if ./rag-cli auth status --quiet; then
    echo "Authenticated"
else
    echo "Not authenticated"
fi
```

### JSON Output for Parsing
```bash
# Extract collection IDs
./rag-cli collections list --format json | jq -r '.collections[].id'

# Count documents in collection
./rag-cli documents list COLLECTION_ID --format json | jq '.total'
```

### Batch Operations
```bash
#!/bin/bash
# Upload all PDFs in directory
for file in *.pdf; do
    ./rag-cli documents upload $COLLECTION_ID "$file" --title "$(basename "$file" .pdf)"
done
```

## Help System

Get help for any command:

```bash
# General help
./rag-cli --help

# Group help
./rag-cli auth --help
./rag-cli collections --help

# Specific command help
./rag-cli collections create --help
./rag-cli search query --help

# Examples for command
./rag-cli collections create --examples
```

## Next Steps

Explore detailed documentation for each command group:

1. **[Authentication Commands](auth.md)** - Start with authentication setup
2. **[Collection Commands](collections.md)** - Learn collection management
3. **[Document Commands](documents.md)** - Upload and manage documents
4. **[Search Commands](search.md)** - Perform searches and queries
5. **[User Commands](users.md)** - User administration (if applicable)

Or continue with:
- **[Configuration Guide](../configuration.md)** - Advanced configuration options
- **[Troubleshooting](../troubleshooting.md)** - Common issues and solutions
