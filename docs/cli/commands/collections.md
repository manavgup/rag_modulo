# Collection Commands

Collection commands manage document repositories within the RAG system. Collections group related documents and provide the foundation for semantic search and retrieval operations.

## Overview

Collections in RAG Modulo provide:
- **Document Organization**: Group related documents together
- **Vector Database Integration**: Choose storage backend (Milvus, ChromaDB, etc.)
- **Access Control**: Public and private collections
- **Metadata Management**: Rich collection descriptions and settings
- **Search Configuration**: Customize retrieval parameters

## Commands Reference

### `rag-cli collections list`

List all accessible collections.

#### Usage
```bash
./rag-cli collections list [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (`table`, `json`, `csv`, `yaml`) | `table` |
| `--limit LIMIT` | Maximum number of collections to return | `50` |
| `--offset OFFSET` | Number of collections to skip | `0` |
| `--filter FILTER` | Filter collections by name or status | None |
| `--sort FIELD` | Sort by field (`name`, `created_at`, `document_count`) | `name` |
| `--order ORDER` | Sort order (`asc`, `desc`) | `asc` |

#### Examples

**Basic listing:**
```bash
./rag-cli collections list
```

**JSON output with filtering:**
```bash
./rag-cli collections list --format json --filter "research"
```

**Paginated results:**
```bash
./rag-cli collections list --limit 10 --offset 20
```

**Sort by creation date:**
```bash
./rag-cli collections list --sort created_at --order desc
```

#### Expected Output

**Table format:**
```
┌──────────────────────┬─────────────────┬────────────┬───────────┬─────────────────────┐
│ ID                   │ Name            │ Documents  │ Status    │ Created             │
├──────────────────────┼─────────────────┼────────────┼───────────┼─────────────────────┤
│ col_123abc           │ Knowledge Base  │ 15         │ Active    │ 2024-01-10 10:00:00 │
│ col_456def           │ Research Papers │ 8          │ Processing│ 2024-01-10 11:00:00 │
│ col_789ghi           │ Technical Docs  │ 23         │ Active    │ 2024-01-09 15:30:00 │
└──────────────────────┴─────────────────┴────────────┴───────────┴─────────────────────┘

Total: 3 collections
```

**JSON format:**
```json
{
  "collections": [
    {
      "id": "col_123abc",
      "name": "Knowledge Base",
      "description": "General company knowledge repository",
      "document_count": 15,
      "status": "active",
      "is_private": false,
      "vector_db": "milvus",
      "created_at": "2024-01-10T10:00:00Z",
      "updated_at": "2024-01-15T09:30:00Z",
      "owner": "john.doe@company.com"
    }
  ],
  "total": 3,
  "limit": 50,
  "offset": 0
}
```

---

### `rag-cli collections create`

Create a new document collection.

#### Usage
```bash
./rag-cli collections create NAME [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `NAME` | Collection name | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--description DESC` | Collection description | Empty |
| `--vector-db DB` | Vector database (`milvus`, `chromadb`, `pinecone`) | `milvus` |
| `--private` | Create as private collection | `false` |
| `--chunk-size SIZE` | Document chunk size for processing | `512` |
| `--chunk-overlap OVERLAP` | Overlap between chunks | `50` |
| `--embedding-model MODEL` | Embedding model to use | System default |
| `--output-id` | Output only the collection ID | `false` |

#### Examples

**Basic collection:**
```bash
./rag-cli collections create "My Knowledge Base"
```

**Private collection with custom settings:**
```bash
./rag-cli collections create "Confidential Docs" \
  --description "Internal confidential documents" \
  --private \
  --vector-db milvus \
  --chunk-size 1024
```

**For scripting (get collection ID):**
```bash
COLLECTION_ID=$(./rag-cli collections create "Research Papers" --output-id)
echo "Created collection: $COLLECTION_ID"
```

**Custom embedding configuration:**
```bash
./rag-cli collections create "Technical Documentation" \
  --description "Software documentation and guides" \
  --embedding-model "sentence-transformers/all-mpnet-base-v2" \
  --chunk-size 768 \
  --chunk-overlap 100
```

#### Expected Output

**Successful creation:**
```
✅ Collection created successfully!

ID: col_abc123def
Name: My Knowledge Base
Description: (none)
Status: Active
Vector DB: milvus
Privacy: Public
Documents: 0

You can now upload documents:
./rag-cli documents upload col_abc123def your-document.pdf
```

**With custom settings:**
```
✅ Collection created successfully!

ID: col_xyz789abc
Name: Technical Documentation
Description: Software documentation and guides
Status: Active
Vector DB: milvus
Privacy: Public
Chunk Size: 768 tokens
Chunk Overlap: 100 tokens
Embedding Model: sentence-transformers/all-mpnet-base-v2
Documents: 0
```

---

### `rag-cli collections get`

Get detailed information about a specific collection.

#### Usage
```bash
./rag-cli collections get COLLECTION_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (`table`, `json`, `yaml`) | `table` |
| `--include-stats` | Include detailed statistics | `false` |
| `--include-settings` | Include technical settings | `false` |

#### Examples

**Basic information:**
```bash
./rag-cli collections get col_123abc
```

**Detailed information:**
```bash
./rag-cli collections get col_123abc --include-stats --include-settings
```

**JSON output for processing:**
```bash
./rag-cli collections get col_123abc --format json --include-stats
```

#### Expected Output

**Basic output:**
```
📚 Collection Details

ID: col_123abc
Name: Knowledge Base
Description: General company knowledge repository
Status: Active
Privacy: Public
Owner: john.doe@company.com

📊 Statistics
Documents: 15
Total Size: 2.3 MB
Last Updated: 2024-01-15 09:30:00
Created: 2024-01-10 10:00:00

🔍 Search Info
Vector Database: milvus
Ready for Search: ✅
```

**Detailed output with settings:**
```
📚 Collection Details

ID: col_123abc
Name: Knowledge Base
Description: General company knowledge repository
Status: Active
Privacy: Public
Owner: john.doe@company.com

📊 Detailed Statistics
Documents: 15
  - PDF: 8 documents (1.8 MB)
  - DOCX: 4 documents (0.4 MB)
  - TXT: 3 documents (0.1 MB)
Total Chunks: 1,247
Average Chunks per Document: 83
Index Size: 145 MB
Last Document Added: 2024-01-14 16:45:00
Last Search: 2024-01-15 08:15:00

⚙️ Technical Settings
Vector Database: milvus
Collection Name: knowledge_base_col_123abc
Embedding Model: sentence-transformers/all-MiniLM-L6-v2
Embedding Dimensions: 384
Chunk Size: 512 tokens
Chunk Overlap: 50 tokens
Distance Metric: cosine

🔍 Search Configuration
Max Results per Query: 10
Similarity Threshold: 0.7
Re-ranking Enabled: ✅
Context Window: 2048 tokens
```

---

### `rag-cli collections update`

Update collection settings and metadata.

#### Usage
```bash
./rag-cli collections update COLLECTION_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--name NAME` | Update collection name | No change |
| `--description DESC` | Update description | No change |
| `--private BOOL` | Change privacy setting | No change |
| `--chunk-size SIZE` | Update chunk size (triggers reprocessing) | No change |
| `--chunk-overlap OVERLAP` | Update chunk overlap | No change |
| `--similarity-threshold THRESHOLD` | Search similarity threshold | No change |

#### Examples

**Update name and description:**
```bash
./rag-cli collections update col_123abc \
  --name "Corporate Knowledge Base" \
  --description "Updated comprehensive knowledge repository"
```

**Change privacy setting:**
```bash
./rag-cli collections update col_123abc --private true
```

**Update chunking settings (triggers reprocessing):**
```bash
./rag-cli collections update col_123abc \
  --chunk-size 1024 \
  --chunk-overlap 100
```

**Update search parameters:**
```bash
./rag-cli collections update col_123abc \
  --similarity-threshold 0.8
```

#### Expected Output

**Successful update:**
```
✅ Collection updated successfully!

Updated fields:
- Name: "Knowledge Base" → "Corporate Knowledge Base"
- Description: Updated
- Privacy: Public → Private

⚠️ Note: Collection is now private. Only you and authorized users can access it.
```

**Update requiring reprocessing:**
```
✅ Collection updated successfully!

Updated fields:
- Chunk Size: 512 → 1024 tokens
- Chunk Overlap: 50 → 100 tokens

⚠️ Important: Document reprocessing required for these changes to take effect.
Documents will be reprocessed automatically in the background.
Current documents: 15 (estimated processing time: 5-10 minutes)

You can monitor progress with:
./rag-cli collections get col_123abc --include-stats
```

---

### `rag-cli collections delete`

Delete a collection and all its documents.

#### Usage
```bash
./rag-cli collections delete COLLECTION_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--force` | Skip confirmation prompt | `false` |
| `--backup` | Create backup before deletion | `false` |
| `--backup-path PATH` | Custom backup location | `./collection-backup/` |

#### Examples

**Interactive deletion:**
```bash
./rag-cli collections delete col_123abc
```

**Force deletion without confirmation:**
```bash
./rag-cli collections delete col_123abc --force
```

**Delete with backup:**
```bash
./rag-cli collections delete col_123abc \
  --backup \
  --backup-path "./backups/collection-$(date +%Y%m%d)"
```

#### Expected Output

**Interactive deletion:**
```
⚠️ Delete Collection Confirmation

Collection: Knowledge Base (col_123abc)
Documents: 15 documents (2.3 MB)
Created: 2024-01-10 10:00:00
Owner: john.doe@company.com

This action cannot be undone!

Are you sure you want to delete this collection? (y/N): y

✅ Collection deleted successfully!

Removed:
- Collection metadata
- 15 documents
- Vector embeddings
- Search indexes

Total space freed: 147.3 MB
```

**With backup:**
```
📦 Creating backup...
✅ Backup created: ./backups/collection-20240115/knowledge-base-backup.zip

⚠️ Delete Collection Confirmation
[... confirmation dialog ...]

✅ Collection deleted successfully!
📦 Backup available at: ./backups/collection-20240115/knowledge-base-backup.zip
```

## Advanced Usage

### Batch Operations

**Create multiple collections:**
```bash
#!/bin/bash
collections=("Research Papers" "Technical Docs" "Meeting Notes")

for name in "${collections[@]}"; do
    id=$(./rag-cli collections create "$name" --output-id)
    echo "Created: $name ($id)"
done
```

**Update multiple collections:**
```bash
#!/bin/bash
# Update privacy for all collections
./rag-cli collections list --format json | \
jq -r '.collections[].id' | \
while read collection_id; do
    ./rag-cli collections update "$collection_id" --private true
    echo "Updated: $collection_id"
done
```

### Collection Migration

**Export collection configuration:**
```bash
./rag-cli collections get col_123abc --format json --include-settings > collection-config.json
```

**Import/recreate collection:**
```bash
#!/bin/bash
config=$(cat collection-config.json)
name=$(echo "$config" | jq -r '.name')
description=$(echo "$config" | jq -r '.description')
chunk_size=$(echo "$config" | jq -r '.chunk_size')

./rag-cli collections create "$name" \
  --description "$description" \
  --chunk-size "$chunk_size"
```

### Monitoring Collection Health

**Check collection status:**
```bash
#!/bin/bash
./rag-cli collections list --format json | \
jq -r '.collections[] | select(.status != "active") | [.id, .name, .status] | @tsv' | \
while IFS=$'\t' read -r id name status; do
    echo "⚠️ Collection issue: $name ($id) - Status: $status"
done
```

**Collection statistics dashboard:**
```bash
#!/bin/bash
echo "📊 Collection Statistics Dashboard"
echo "================================="

total=$(./rag-cli collections list --format json | jq '.total')
echo "Total Collections: $total"

active=$(./rag-cli collections list --format json | jq '[.collections[] | select(.status == "active")] | length')
echo "Active Collections: $active"

total_docs=$(./rag-cli collections list --format json | jq '[.collections[].document_count] | add')
echo "Total Documents: $total_docs"

echo ""
echo "Top 5 Collections by Document Count:"
./rag-cli collections list --format json | \
jq -r '.collections | sort_by(.document_count) | reverse | .[0:5] | .[] | [.name, .document_count] | @tsv' | \
while IFS=$'\t' read -r name count; do
    echo "  - $name: $count documents"
done
```

## Error Handling

### Common Error Scenarios

#### Collection Not Found
```bash
$ ./rag-cli collections get invalid-id
❌ Collection not found

Collection ID 'invalid-id' does not exist or you don't have access to it.

Available collections:
./rag-cli collections list
```

#### Permission Denied
```bash
$ ./rag-cli collections get col_private123
❌ Access denied

Collection 'col_private123' is private and you don't have access.
Contact the collection owner for access.
```

#### Duplicate Collection Name
```bash
$ ./rag-cli collections create "Knowledge Base"
❌ Collection creation failed

A collection with the name 'Knowledge Base' already exists.
Collection names must be unique within your account.

Suggestion: Try "Knowledge Base v2" or "Knowledge Base - Updated"
```

#### Vector Database Connection Issues
```bash
$ ./rag-cli collections create "New Collection"
❌ Collection creation failed

Unable to connect to vector database (milvus).
- Check backend configuration
- Verify vector database is running
- Contact administrator if issue persists

Backend status: ./rag-cli config test-connection
```

### Debugging Collection Issues

**Enable debug mode:**
```bash
./rag-cli --debug collections get col_123abc
```

**Check backend connectivity:**
```bash
./rag-cli config test-connection --verbose
```

**Validate collection data:**
```bash
# Check collection consistency
./rag-cli collections get col_123abc --include-stats --include-settings
```

## Integration with Other Commands

### Document Upload Workflow
```bash
# 1. Create collection
COLLECTION_ID=$(./rag-cli collections create "Research Papers" \
  --description "Academic research collection" \
  --chunk-size 1024 \
  --output-id)

# 2. Upload documents
./rag-cli documents upload "$COLLECTION_ID" *.pdf

# 3. Verify collection
./rag-cli collections get "$COLLECTION_ID" --include-stats
```

### Search Integration
```bash
# Find collections with specific documents
./rag-cli collections list --filter "research" | \
grep -E "col_[a-zA-Z0-9]+" | \
while read collection_id _; do
    echo "Searching in: $collection_id"
    ./rag-cli search query "$collection_id" "machine learning" --max-results 3
done
```

### User Management Integration
```bash
# Grant access to private collection
./rag-cli collections update col_123abc --add-user "jane.doe@company.com"

# List users with access
./rag-cli collections get col_123abc --include-permissions
```

## Configuration Integration

### Default Settings
```bash
# Set default vector database
./rag-cli config set collections.default_vector_db "milvus"

# Set default chunk size
./rag-cli config set collections.default_chunk_size 768

# Set default privacy
./rag-cli config set collections.default_private false
```

### Profile-Specific Settings
```bash
# Production settings
./rag-cli config set collections.default_vector_db "pinecone" --profile prod
./rag-cli config set collections.default_chunk_size 1024 --profile prod

# Development settings
./rag-cli config set collections.default_vector_db "chromadb" --profile dev
./rag-cli config set collections.default_chunk_size 512 --profile dev
```

## Next Steps

After mastering collection management:
1. **[Documents](documents.md)** - Upload and manage documents within collections
2. **[Search](search.md)** - Query your collections effectively
3. **[Users](users.md)** - Manage collection access and permissions
4. **[Configuration](../configuration.md)** - Advanced collection configuration
