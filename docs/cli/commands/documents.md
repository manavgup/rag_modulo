# Document Commands

Document commands manage files within collections, including upload, processing, and retrieval operations. These commands handle the core content management features of the RAG system.

## Overview

Document management provides:
- **Multi-Format Support**: PDF, DOCX, TXT, MD, and other text-based formats
- **Intelligent Processing**: Automatic text extraction and chunking
- **Metadata Management**: Rich document tagging and categorization
- **Version Control**: Track document updates and changes
- **Batch Operations**: Efficient bulk document handling

## Commands Reference

### `rag-cli documents list`

List documents within a collection.

#### Usage
```bash
./rag-cli documents list COLLECTION_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (`table`, `json`, `csv`, `yaml`) | `table` |
| `--limit LIMIT` | Maximum documents to return | `50` |
| `--offset OFFSET` | Number of documents to skip | `0` |
| `--filter FILTER` | Filter by title, type, or status | None |
| `--sort FIELD` | Sort by (`title`, `created_at`, `size`, `status`) | `title` |
| `--order ORDER` | Sort order (`asc`, `desc`) | `asc` |
| `--include-stats` | Include processing statistics | `false` |

#### Examples

**Basic listing:**
```bash
./rag-cli documents list col_123abc
```

**Filtered by file type:**
```bash
./rag-cli documents list col_123abc --filter "pdf"
```

**With processing statistics:**
```bash
./rag-cli documents list col_123abc --include-stats --format json
```

**Sorted by upload date:**
```bash
./rag-cli documents list col_123abc --sort created_at --order desc
```

#### Expected Output

**Table format:**
```
┌──────────────────────┬─────────────────────────────┬──────────┬──────────┬────────────┬─────────────────────┐
│ ID                   │ Title                       │ Type     │ Size     │ Status     │ Uploaded            │
├──────────────────────┼─────────────────────────────┼──────────┼──────────┼────────────┼─────────────────────┤
│ doc_abc123           │ ML Research Paper           │ PDF      │ 2.3 MB   │ Processed  │ 2024-01-15 09:30:00 │
│ doc_def456           │ Technical Requirements      │ DOCX     │ 456 KB   │ Processing │ 2024-01-15 10:15:00 │
│ doc_ghi789           │ Quick Notes                 │ TXT      │ 12 KB    │ Processed  │ 2024-01-14 16:45:00 │
└──────────────────────┴─────────────────────────────┴──────────┴──────────┴────────────┴─────────────────────┘

Total: 3 documents (2.8 MB)
```

**JSON with statistics:**
```json
{
  "documents": [
    {
      "id": "doc_abc123",
      "title": "ML Research Paper",
      "filename": "ml-research-2024.pdf",
      "file_type": "pdf",
      "size_bytes": 2415616,
      "status": "processed",
      "uploaded_at": "2024-01-15T09:30:00Z",
      "processed_at": "2024-01-15T09:32:15Z",
      "chunk_count": 47,
      "page_count": 12,
      "processing_time_seconds": 135,
      "metadata": {
        "author": "Dr. Jane Smith",
        "subject": "Machine Learning",
        "creation_date": "2024-01-10"
      }
    }
  ],
  "total": 3,
  "total_size_bytes": 2927616
}
```

---

### `rag-cli documents upload`

Upload one or more documents to a collection.

#### Usage
```bash
./rag-cli documents upload COLLECTION_ID FILE_PATH [FILE_PATH...] [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `FILE_PATH` | Path to file(s) to upload | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--title TITLE` | Custom document title | Filename |
| `--description DESC` | Document description | Empty |
| `--tags TAGS` | Comma-separated tags | None |
| `--metadata KEY=VALUE` | Custom metadata pairs | None |
| `--auto-title` | Extract title from document content | `false` |
| `--wait` | Wait for processing to complete | `false` |
| `--batch-size SIZE` | Number of files to upload concurrently | `5` |
| `--recursive` | Upload files recursively from directories | `false` |
| `--pattern PATTERN` | File pattern filter (e.g., `*.pdf`) | `*` |

#### Examples

**Single document upload:**
```bash
./rag-cli documents upload col_123abc report.pdf
```

**Multiple documents with custom metadata:**
```bash
./rag-cli documents upload col_123abc report.pdf presentation.pptx \
  --tags "research,quarterly" \
  --metadata "department=engineering" \
  --metadata "quarter=Q1-2024"
```

**Bulk upload from directory:**
```bash
./rag-cli documents upload col_123abc ./documents/ \
  --recursive \
  --pattern "*.pdf" \
  --auto-title \
  --wait
```

**Upload with custom processing:**
```bash
./rag-cli documents upload col_123abc manual.pdf \
  --title "User Manual v2.1" \
  --description "Updated user manual with new features" \
  --tags "manual,user-guide,v2.1" \
  --wait
```

#### Expected Output

**Single file upload:**
```
📤 Uploading document...

File: report.pdf
Size: 2.3 MB
Collection: Knowledge Base (col_123abc)

✅ Upload successful!

Document ID: doc_abc123def
Title: report.pdf
Status: Processing
Estimated processing time: 2-3 minutes

Monitor progress: ./rag-cli documents get col_123abc doc_abc123def
```

**Batch upload with progress:**
```
📤 Uploading 5 documents to Knowledge Base...

[████████████████████████████████████████] 100% (5/5)

✅ Batch upload completed!

Successfully uploaded:
  - report.pdf → doc_abc123 (Processing)
  - slides.pptx → doc_def456 (Processing)
  - notes.txt → doc_ghi789 (Processing)
  - manual.pdf → doc_jkl012 (Processing)
  - readme.md → doc_mno345 (Processing)

Total: 5 documents (12.7 MB)
Processing: All documents are being processed in the background.
```

**Upload with wait flag:**
```
📤 Uploading and processing document...

File: research-paper.pdf
Size: 3.1 MB
Collection: Research Papers (col_research)

[████████████████████████████████████████] Upload: 100%
[████████████████████████████████████████] Processing: 100%

✅ Document processed successfully!

Document ID: doc_research123
Title: AI in Healthcare: A Comprehensive Review
Pages: 24
Chunks: 89
Processing time: 3m 42s

Ready for search: ./rag-cli search query col_research "AI healthcare applications"
```

---

### `rag-cli documents get`

Get detailed information about a specific document.

#### Usage
```bash
./rag-cli documents get COLLECTION_ID DOCUMENT_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `DOCUMENT_ID` | Document identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--format FORMAT` | Output format (`table`, `json`, `yaml`) | `table` |
| `--include-content` | Include extracted text content | `false` |
| `--include-chunks` | Include chunk information | `false` |
| `--include-metadata` | Include all metadata fields | `false` |

#### Examples

**Basic document info:**
```bash
./rag-cli documents get col_123abc doc_abc123
```

**Detailed information:**
```bash
./rag-cli documents get col_123abc doc_abc123 \
  --include-chunks \
  --include-metadata \
  --format json
```

**Content preview:**
```bash
./rag-cli documents get col_123abc doc_abc123 --include-content
```

#### Expected Output

**Basic information:**
```
📄 Document Details

ID: doc_abc123
Title: ML Research Paper
Filename: ml-research-2024.pdf
Collection: Knowledge Base (col_123abc)

📊 File Information
Type: PDF
Size: 2.3 MB (2,415,616 bytes)
Pages: 12
Status: ✅ Processed

📅 Timeline
Uploaded: 2024-01-15 09:30:00
Processed: 2024-01-15 09:32:15
Processing time: 2m 15s

🔍 Search Data
Chunks: 47
Average chunk size: 418 tokens
Ready for search: ✅
```

**Detailed with chunks:**
```
📄 Document Details
[... basic info ...]

📝 Content Structure
Total chunks: 47
Chunk distribution:
  - Introduction: 3 chunks
  - Methodology: 12 chunks
  - Results: 18 chunks
  - Discussion: 9 chunks
  - Conclusion: 3 chunks
  - References: 2 chunks

🏷️ Metadata
Author: Dr. Jane Smith
Subject: Machine Learning
Keywords: artificial intelligence, neural networks, deep learning
Creation date: 2024-01-10
Document version: 1.2
Tags: research, quarterly, ml

📊 Processing Statistics
Text extraction time: 45s
Chunking time: 23s
Embedding generation: 87s
Index update time: 20s
```

---

### `rag-cli documents download`

Download a document from a collection.

#### Usage
```bash
./rag-cli documents download COLLECTION_ID DOCUMENT_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `DOCUMENT_ID` | Document identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--output PATH` | Output file path | Original filename |
| `--format FORMAT` | Download format (`original`, `text`, `json`) | `original` |
| `--include-metadata` | Include metadata in output | `false` |

#### Examples

**Download original file:**
```bash
./rag-cli documents download col_123abc doc_abc123
```

**Download to specific location:**
```bash
./rag-cli documents download col_123abc doc_abc123 \
  --output ./downloads/research-paper.pdf
```

**Download extracted text:**
```bash
./rag-cli documents download col_123abc doc_abc123 \
  --format text \
  --output research-paper.txt
```

**Download with metadata:**
```bash
./rag-cli documents download col_123abc doc_abc123 \
  --format json \
  --include-metadata \
  --output document-export.json
```

#### Expected Output

**Successful download:**
```
📥 Downloading document...

Document: ML Research Paper (doc_abc123)
Source: col_123abc
Format: Original PDF

✅ Download completed!

File: ml-research-2024.pdf
Size: 2.3 MB
Location: ./ml-research-2024.pdf
```

**Text extraction download:**
```
📥 Extracting and downloading text...

Document: ML Research Paper (doc_abc123)
Format: Plain text
Pages: 12 → Text file

✅ Download completed!

File: ml-research-2024.txt
Size: 156 KB
Location: ./ml-research-2024.txt
Chunks: 47 text segments included
```

---

### `rag-cli documents delete`

Delete a document from a collection.

#### Usage
```bash
./rag-cli documents delete COLLECTION_ID DOCUMENT_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `DOCUMENT_ID` | Document identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--force` | Skip confirmation prompt | `false` |
| `--backup` | Create backup before deletion | `false` |
| `--backup-path PATH` | Custom backup location | `./document-backup/` |

#### Examples

**Interactive deletion:**
```bash
./rag-cli documents delete col_123abc doc_abc123
```

**Force delete without confirmation:**
```bash
./rag-cli documents delete col_123abc doc_abc123 --force
```

**Delete with backup:**
```bash
./rag-cli documents delete col_123abc doc_abc123 \
  --backup \
  --backup-path ./backups/
```

#### Expected Output

**Interactive deletion:**
```
⚠️ Delete Document Confirmation

Document: ML Research Paper (doc_abc123)
Collection: Knowledge Base (col_123abc)
File: ml-research-2024.pdf (2.3 MB)
Chunks: 47 text segments
Uploaded: 2024-01-15 09:30:00

This action cannot be undone!
Document will be removed from search index.

Are you sure you want to delete this document? (y/N): y

✅ Document deleted successfully!

Removed:
- Original file (2.3 MB)
- 47 text chunks
- Search index entries
- Metadata records

Collection updated: 14 documents remaining
```

---

### `rag-cli documents reprocess`

Reprocess a document with updated settings.

#### Usage
```bash
./rag-cli documents reprocess COLLECTION_ID DOCUMENT_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `DOCUMENT_ID` | Document identifier | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--wait` | Wait for reprocessing to complete | `false` |
| `--force` | Force reprocessing even if not needed | `false` |
| `--chunk-size SIZE` | Override default chunk size | Collection default |
| `--chunk-overlap OVERLAP` | Override chunk overlap | Collection default |

#### Examples

**Basic reprocessing:**
```bash
./rag-cli documents reprocess col_123abc doc_abc123
```

**Reprocess with custom settings:**
```bash
./rag-cli documents reprocess col_123abc doc_abc123 \
  --chunk-size 1024 \
  --chunk-overlap 100 \
  --wait
```

**Force reprocessing:**
```bash
./rag-cli documents reprocess col_123abc doc_abc123 --force --wait
```

#### Expected Output

**Reprocessing initiated:**
```
🔄 Initiating document reprocessing...

Document: ML Research Paper (doc_abc123)
Collection: Knowledge Base (col_123abc)
Reason: Collection chunk size updated

Current chunks: 47 (512 tokens each)
New chunk size: 1024 tokens
Estimated new chunks: ~24

✅ Reprocessing started!

Status: Processing
Estimated time: 2-3 minutes

Monitor progress: ./rag-cli documents get col_123abc doc_abc123
```

**Reprocessing completed (with --wait):**
```
🔄 Reprocessing document...

[████████████████████████████████████████] 100%

✅ Reprocessing completed!

Document: ML Research Paper (doc_abc123)
Processing time: 1m 34s

Changes:
- Chunks: 47 → 24 (-49%)
- Average chunk size: 418 → 892 tokens
- Index updated: ✅

Document is ready for search with updated chunking.
```

## Advanced Usage

### Batch Document Operations

**Upload entire directory structure:**
```bash
#!/bin/bash
find ./documents -type f \( -name "*.pdf" -o -name "*.docx" -o -name "*.txt" \) | \
while read file; do
    echo "Uploading: $file"
    ./rag-cli documents upload col_123abc "$file" \
      --auto-title \
      --tags "batch-upload,$(date +%Y-%m)" \
      --metadata "source=directory-import"
done
```

**Mass document reprocessing:**
```bash
#!/bin/bash
# Reprocess all documents after collection settings change
./rag-cli documents list col_123abc --format json | \
jq -r '.documents[] | select(.status == "processed") | .id' | \
while read doc_id; do
    echo "Reprocessing: $doc_id"
    ./rag-cli documents reprocess col_123abc "$doc_id"
done
```

**Document health check:**
```bash
#!/bin/bash
echo "📊 Document Health Check"
echo "======================="

# Check for failed documents
failed=$(./rag-cli documents list col_123abc --format json | \
         jq '[.documents[] | select(.status == "failed")] | length')
echo "Failed documents: $failed"

# Check for stuck processing
processing=$(./rag-cli documents list col_123abc --format json | \
            jq '[.documents[] | select(.status == "processing")] | length')
echo "Processing documents: $processing"

# List documents needing attention
if [ "$failed" -gt 0 ] || [ "$processing" -gt 0 ]; then
    echo ""
    echo "Documents needing attention:"
    ./rag-cli documents list col_123abc --format json | \
    jq -r '.documents[] | select(.status == "failed" or .status == "processing") | [.id, .title, .status] | @tsv' | \
    while IFS=$'\t' read -r id title status; do
        echo "  - $title ($id): $status"
    done
fi
```

### Document Metadata Management

**Bulk metadata updates:**
```bash
#!/bin/bash
# Add department metadata to all documents
./rag-cli documents list col_123abc --format json | \
jq -r '.documents[].id' | \
while read doc_id; do
    ./rag-cli documents update col_123abc "$doc_id" \
      --metadata "department=engineering" \
      --metadata "reviewed=2024-01"
done
```

**Extract and export metadata:**
```bash
#!/bin/bash
echo "Document Metadata Report"
echo "======================="

./rag-cli documents list col_123abc --format json --include-stats | \
jq -r '.documents[] | [.title, .file_type, .size_bytes, .chunk_count, .tags] | @csv' > document-report.csv

echo "Report exported to: document-report.csv"
```

### Content Analysis

**Document statistics dashboard:**
```bash
#!/bin/bash
collection_id="col_123abc"

echo "📊 Document Statistics for Collection: $collection_id"
echo "=================================================="

# Get collection info
info=$(./rag-cli documents list "$collection_id" --format json --include-stats)

# Total documents
total=$(echo "$info" | jq '.total')
echo "Total Documents: $total"

# File type distribution
echo ""
echo "File Types:"
echo "$info" | jq -r '.documents | group_by(.file_type) | .[] | [.[0].file_type, length] | @tsv' | \
while IFS=$'\t' read -r type count; do
    echo "  - ${type^^}: $count documents"
done

# Size statistics
echo ""
echo "Size Statistics:"
total_size=$(echo "$info" | jq '[.documents[].size_bytes] | add')
avg_size=$(echo "$info" | jq '[.documents[].size_bytes] | add / length')
echo "  - Total: $(numfmt --to=iec $total_size)"
echo "  - Average: $(numfmt --to=iec ${avg_size%.*})"

# Processing status
echo ""
echo "Processing Status:"
echo "$info" | jq -r '.documents | group_by(.status) | .[] | [.[0].status, length] | @tsv' | \
while IFS=$'\t' read -r status count; do
    echo "  - ${status^}: $count documents"
done
```

## Error Handling

### Common Error Scenarios

#### Document Not Found
```bash
$ ./rag-cli documents get col_123abc invalid-doc-id
❌ Document not found

Document 'invalid-doc-id' does not exist in collection 'col_123abc'.

List available documents:
./rag-cli documents list col_123abc
```

#### Upload Failed - Unsupported Format
```bash
$ ./rag-cli documents upload col_123abc image.jpg
❌ Upload failed

File 'image.jpg' has unsupported format: JPEG
Supported formats: PDF, DOCX, DOC, TXT, MD, RTF, ODT

Convert to supported format or use text extraction tool first.
```

#### Processing Failed
```bash
$ ./rag-cli documents get col_123abc doc_failed123
📄 Document Details

ID: doc_failed123
Status: ❌ Processing Failed
Error: Text extraction failed - corrupted PDF

Retry options:
1. Re-upload original file: ./rag-cli documents upload col_123abc original-file.pdf
2. Force reprocess: ./rag-cli documents reprocess col_123abc doc_failed123 --force
3. Delete and retry: ./rag-cli documents delete col_123abc doc_failed123
```

#### Storage Quota Exceeded
```bash
$ ./rag-cli documents upload col_123abc large-file.pdf
❌ Upload failed

Collection storage quota exceeded.
Current usage: 4.8 GB / 5.0 GB limit
File size: 245 MB

Options:
1. Delete unused documents to free space
2. Contact administrator to increase quota
3. Split large file into smaller documents
```

### Debugging Document Issues

**Enable debug mode:**
```bash
./rag-cli --debug documents upload col_123abc problem-file.pdf
```

**Check processing logs:**
```bash
./rag-cli documents get col_123abc doc_123 --include-logs
```

**Validate document integrity:**
```bash
./rag-cli documents validate col_123abc doc_123 --check-chunks --check-embeddings
```

## Integration Examples

### CI/CD Document Updates
```bash
#!/bin/bash
# Automated documentation update script

collection_id="col_docs"
docs_dir="./updated-docs"

echo "🔄 Updating documentation collection..."

# Upload new/updated documents
for file in "$docs_dir"/*.md; do
    if [ -f "$file" ]; then
        title=$(basename "$file" .md)

        # Check if document already exists
        if ./rag-cli documents list "$collection_id" --filter "$title" --format json | jq -e '.documents | length > 0' > /dev/null; then
            echo "Updating existing document: $title"
            doc_id=$(./rag-cli documents list "$collection_id" --filter "$title" --format json | jq -r '.documents[0].id')
            ./rag-cli documents delete "$collection_id" "$doc_id" --force
        fi

        echo "Uploading: $title"
        ./rag-cli documents upload "$collection_id" "$file" \
          --title "$title" \
          --tags "documentation,auto-updated" \
          --metadata "version=$(git rev-parse --short HEAD)" \
          --metadata "updated=$(date -Iseconds)"
    fi
done

echo "✅ Documentation update completed"
```

### Document Backup System
```bash
#!/bin/bash
# Complete document backup script

collection_id="$1"
backup_dir="./backups/$(date +%Y%m%d_%H%M%S)"

echo "📦 Creating document backup for collection: $collection_id"

mkdir -p "$backup_dir"

# Export document metadata
./rag-cli documents list "$collection_id" --format json --include-stats > "$backup_dir/documents.json"

# Download all documents
./rag-cli documents list "$collection_id" --format json | \
jq -r '.documents[] | [.id, .title, .filename] | @tsv' | \
while IFS=$'\t' read -r doc_id title filename; do
    echo "Backing up: $title"
    ./rag-cli documents download "$collection_id" "$doc_id" \
      --output "$backup_dir/$filename"
done

echo "✅ Backup completed: $backup_dir"
tar -czf "$backup_dir.tar.gz" -C "$(dirname "$backup_dir")" "$(basename "$backup_dir")"
echo "📦 Archive created: $backup_dir.tar.gz"
```

## Next Steps

After mastering document management:
1. **[Search Commands](search.md)** - Query your document collections effectively
2. **[Collection Management](collections.md)** - Advanced collection configuration
3. **[Configuration](../configuration.md)** - Optimize document processing settings
4. **[Troubleshooting](../troubleshooting.md)** - Resolve document processing issues
