# CLI Examples

Practical examples for using the RAG Modulo command-line interface.

## Installation

```bash
# CLI is installed with the backend
poetry install

# Verify installation
./rag-cli --help
```

## Authentication

### Setup Authentication

```bash
# Configure API endpoint
./rag-cli config set api_url http://localhost:8000

# Login to get token
./rag-cli auth login user@example.com

# Verify authentication
./rag-cli auth whoami
```

See [CLI Authentication](authentication.md) for details.

## Collection Management

### List Collections

```bash
# List all collections
./rag-cli collections list

# List with details
./rag-cli collections list --verbose
```

### Create Collection

```bash
# Create new collection
./rag-cli collections create "Research Papers" \
  --description "AI and ML research papers"

# Create with metadata
./rag-cli collections create "Technical Docs" \
  --description "Technical documentation" \
  --metadata '{"category": "docs", "tags": ["tech"]}'
```

### View Collection Details

```bash
# Get collection info
./rag-cli collections get col_123abc

# Show document count
./rag-cli collections stats col_123abc
```

### Delete Collection

```bash
# Delete collection (requires confirmation)
./rag-cli collections delete col_123abc

# Force delete without confirmation
./rag-cli collections delete col_123abc --force
```

## Document Management

### Upload Documents

```bash
# Upload single document
./rag-cli documents upload col_123abc document.pdf

# Upload with metadata
./rag-cli documents upload col_123abc research.pdf \
  --metadata '{"author": "John Doe", "year": 2025}'

# Upload from directory
./rag-cli documents upload-dir col_123abc ./documents/

# Upload with progress bar
./rag-cli documents upload col_123abc large_file.pdf --progress
```

### List Documents

```bash
# List all documents in collection
./rag-cli documents list col_123abc

# List with status
./rag-cli documents list col_123abc --status indexed

# List with pagination
./rag-cli documents list col_123abc --page 2 --page-size 20
```

### Delete Documents

```bash
# Delete single document
./rag-cli documents delete doc_456def

# Delete all documents in collection
./rag-cli documents delete-all col_123abc --force
```

## Search Operations

### Basic Search

```bash
# Simple search
./rag-cli search query col_123abc "What is machine learning?"

# Save results to file
./rag-cli search query col_123abc "What is ML?" \
  --output results.json

# Show sources
./rag-cli search query col_123abc "What is ML?" \
  --show-sources
```

### Chain of Thought Search

```bash
# Enable CoT reasoning
./rag-cli search query col_123abc \
  "How does machine learning work and what are its components?" \
  --cot

# Show reasoning steps
./rag-cli search query col_123abc \
  "Explain deep learning architectures" \
  --cot --show-steps

# Configure CoT depth
./rag-cli search query col_123abc \
  "Complex question" \
  --cot --max-depth 3
```

### Advanced Search

```bash
# Specify max results
./rag-cli search query col_123abc "What is ML?" \
  --max-results 10

# Set minimum score threshold
./rag-cli search query col_123abc "What is ML?" \
  --min-score 0.75

# Use specific pipeline
./rag-cli search query col_123abc "What is ML?" \
  --pipeline pipe_789ghi
```

### Batch Search

```bash
# Search from file (one query per line)
./rag-cli search batch col_123abc queries.txt

# Save batch results
./rag-cli search batch col_123abc queries.txt \
  --output batch_results.json

# Parallel batch processing
./rag-cli search batch col_123abc queries.txt \
  --parallel 4
```

## Conversation Management

### Create Session

```bash
# Create conversation session
./rag-cli conversations create "ML Q&A Session"

# Create with metadata
./rag-cli conversations create "Research Chat" \
  --metadata '{"topic": "machine_learning"}'
```

### Add Messages

```bash
# Add user message
./rag-cli conversations message sess_abc123 \
  "What is supervised learning?" \
  --role user

# Add assistant message
./rag-cli conversations message sess_abc123 \
  "Supervised learning is..." \
  --role assistant
```

### View Conversation

```bash
# Get session history
./rag-cli conversations get sess_abc123

# Export conversation
./rag-cli conversations export sess_abc123 \
  --format json \
  --output conversation.json

# Export as markdown
./rag-cli conversations export sess_abc123 \
  --format markdown \
  --output conversation.md
```

### List Sessions

```bash
# List all sessions
./rag-cli conversations list

# List active sessions
./rag-cli conversations list --status active

# List archived sessions
./rag-cli conversations list --status archived
```

## Pipeline Management

### List Pipelines

```bash
# List all pipelines
./rag-cli pipelines list

# List user-specific pipelines
./rag-cli pipelines list --user user_123

# Show pipeline details
./rag-cli pipelines get pipe_789ghi
```

### Create Pipeline

```bash
# Create custom pipeline
./rag-cli pipelines create "Fast Search" \
  --stages retrieval,generation \
  --config '{"retrieval": {"max_results": 5}}'

# Set as default
./rag-cli pipelines create "My Pipeline" \
  --stages retrieval,reranking,generation \
  --default
```

## Configuration

### View Configuration

```bash
# Show all config
./rag-cli config show

# Show specific key
./rag-cli config get api_url
```

### Set Configuration

```bash
# Set API URL
./rag-cli config set api_url http://localhost:8000

# Set timeout
./rag-cli config set timeout 30

# Set output format
./rag-cli config set output_format json
```

## Output Formats

### JSON Output

```bash
# Get JSON response
./rag-cli search query col_123abc "What is ML?" \
  --format json
```

**Output**:
```json
{
  "answer": "Machine learning is...",
  "sources": [...],
  "metadata": {
    "total_tokens": 1250,
    "response_time_ms": 850
  }
}
```

### Table Output

```bash
# Get table format
./rag-cli documents list col_123abc --format table
```

**Output**:
```
┌──────────────┬─────────────────┬──────────┬────────────────────┐
│ ID           │ Filename        │ Status   │ Created At         │
├──────────────┼─────────────────┼──────────┼────────────────────┤
│ doc_456def   │ research.pdf    │ indexed  │ 2025-01-09 10:00   │
│ doc_789ghi   │ paper.pdf       │ indexed  │ 2025-01-09 11:00   │
└──────────────┴─────────────────┴──────────┴────────────────────┘
```

### YAML Output

```bash
# Get YAML response
./rag-cli collections get col_123abc --format yaml
```

**Output**:
```yaml
id: col_123abc
name: Research Papers
description: AI and ML papers
document_count: 42
created_at: 2025-01-09T10:00:00Z
```

## Scripting Examples

### Bash Script

```bash
#!/bin/bash
# Upload and search documents

COLLECTION_ID="col_123abc"

# Upload all PDFs
for file in ./documents/*.pdf; do
  echo "Uploading: $file"
  ./rag-cli documents upload "$COLLECTION_ID" "$file"
done

# Wait for indexing
sleep 10

# Search queries
queries=(
  "What is machine learning?"
  "Explain neural networks"
  "What is deep learning?"
)

for query in "${queries[@]}"; do
  echo "Query: $query"
  ./rag-cli search query "$COLLECTION_ID" "$query" \
    --format json > "result_${query// /_}.json"
done
```

### Python Script

```python
#!/usr/bin/env python3
import subprocess
import json

def cli_call(command):
    """Execute CLI command and return JSON result."""
    result = subprocess.run(
        ["./rag-cli"] + command.split(),
        capture_output=True,
        text=True
    )
    return json.loads(result.stdout)

# Create collection
collection = cli_call("collections create 'Auto Collection' --format json")
collection_id = collection["id"]

# Upload documents
for doc in ["doc1.pdf", "doc2.pdf", "doc3.pdf"]:
    cli_call(f"documents upload {collection_id} {doc}")

# Search
result = cli_call(f"search query {collection_id} 'What is ML?' --format json")
print(f"Answer: {result['answer']}")
```

## Debugging

### Verbose Output

```bash
# Enable verbose logging
./rag-cli --verbose search query col_123abc "What is ML?"

# Debug level logging
./rag-cli --debug search query col_123abc "What is ML?"
```

### Dry Run

```bash
# Preview without executing
./rag-cli documents upload col_123abc file.pdf --dry-run

# Show what would be deleted
./rag-cli collections delete col_123abc --dry-run
```

## See Also

- [CLI Overview](index.md) - CLI introduction
- [Authentication](authentication.md) - Authentication setup
- [Configuration](configuration.md) - CLI configuration
- [API Documentation](../api/index.md) - API reference
