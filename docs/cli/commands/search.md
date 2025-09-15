# Search Commands

Search commands provide powerful querying capabilities across document collections, including semantic search, RAG (Retrieval-Augmented Generation) queries, and search analytics.

## Overview

The search system provides:
- **Semantic Search**: Vector-based similarity matching
- **RAG Queries**: AI-powered question answering with retrieved context
- **Hybrid Search**: Combining keyword and semantic search
- **Search Analytics**: Query performance and result analysis
- **Search History**: Track and replay previous searches

## Commands Reference

### `rag-cli search query`

Perform a RAG query to get AI-generated answers with supporting context.

#### Usage
```bash
./rag-cli search query COLLECTION_ID QUERY [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `QUERY` | Search query or question | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--max-chunks MAX` | Maximum chunks to retrieve | `5` |
| `--similarity-threshold THRESHOLD` | Minimum similarity score (0.0-1.0) | `0.7` |
| `--model MODEL` | LLM model for answer generation | System default |
| `--temperature TEMP` | Response creativity (0.0-1.0) | `0.1` |
| `--max-tokens TOKENS` | Maximum response length | `512` |
| `--format FORMAT` | Output format (`text`, `json`, `markdown`) | `text` |
| `--include-sources` | Include source document references | `true` |
| `--include-chunks` | Include retrieved text chunks | `false` |
| `--save-query` | Save query to search history | `true` |

#### Examples

**Basic RAG query:**
```bash
./rag-cli search query col_123abc "What are the main benefits of machine learning?"
```

**Detailed query with custom settings:**
```bash
./rag-cli search query col_123abc "Explain deep learning architectures" \
  --max-chunks 8 \
  --similarity-threshold 0.6 \
  --temperature 0.2 \
  --include-chunks
```

**JSON output for processing:**
```bash
./rag-cli search query col_123abc "summarize recent research findings" \
  --format json \
  --max-tokens 256
```

**High-precision query:**
```bash
./rag-cli search query col_research "What were the accuracy results in the CNN study?" \
  --similarity-threshold 0.8 \
  --model "gpt-4" \
  --include-sources
```

#### Expected Output

**Basic query response:**
```
🔍 RAG Query Results

Query: "What are the main benefits of machine learning?"
Collection: Knowledge Base (col_123abc)
Retrieved chunks: 5/5
Response time: 2.3s

📝 Answer:
Machine learning offers several key benefits:

1. **Automation of Decision Making**: ML algorithms can automatically analyze data and make predictions or decisions without explicit programming for each scenario.

2. **Pattern Recognition**: ML excels at identifying complex patterns in large datasets that might be impossible for humans to detect manually.

3. **Scalability**: Once trained, ML models can process vast amounts of data quickly and efficiently, making them highly scalable for enterprise applications.

4. **Continuous Improvement**: ML systems can learn and adapt over time, improving their accuracy and performance as they process more data.

5. **Cost Efficiency**: By automating complex tasks, ML can significantly reduce operational costs and human error rates.

📚 Sources:
• ML Research Paper (doc_abc123) - Page 3
• Introduction to AI (doc_def456) - Section 2.1
• Business Applications of ML (doc_ghi789) - Chapter 1

Confidence: High (similarity scores: 0.89, 0.85, 0.83)
```

**JSON format output:**
```json
{
  "query": "What are the main benefits of machine learning?",
  "collection_id": "col_123abc",
  "collection_name": "Knowledge Base",
  "response": {
    "answer": "Machine learning offers several key benefits:\n\n1. **Automation of Decision Making**: ML algorithms can automatically analyze data and make predictions...",
    "confidence": "high",
    "response_time_ms": 2300
  },
  "retrieved_chunks": [
    {
      "document_id": "doc_abc123",
      "document_title": "ML Research Paper",
      "chunk_id": "chunk_12",
      "content": "Machine learning algorithms excel at pattern recognition and can identify complex relationships in data...",
      "similarity_score": 0.89,
      "page_number": 3
    }
  ],
  "sources": [
    {
      "document_id": "doc_abc123",
      "document_title": "ML Research Paper",
      "relevance": "high",
      "pages_referenced": [3, 7, 12]
    }
  ],
  "metadata": {
    "model_used": "gpt-3.5-turbo",
    "temperature": 0.1,
    "max_tokens": 512,
    "timestamp": "2024-01-15T14:30:00Z"
  }
}
```

---

### `rag-cli search similar`

Find documents or text chunks similar to given input text.

#### Usage
```bash
./rag-cli search similar COLLECTION_ID TEXT [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `COLLECTION_ID` | Collection identifier | Yes |
| `TEXT` | Text to find similarities for | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--max-results MAX` | Maximum results to return | `10` |
| `--similarity-threshold THRESHOLD` | Minimum similarity score (0.0-1.0) | `0.5` |
| `--search-type TYPE` | Search type (`chunks`, `documents`, `both`) | `chunks` |
| `--format FORMAT` | Output format (`table`, `json`, `markdown`) | `table` |
| `--include-content` | Include matched text content | `false` |
| `--group-by-document` | Group results by source document | `false` |

#### Examples

**Find similar text chunks:**
```bash
./rag-cli search similar col_123abc "neural network architectures"
```

**Document-level similarity:**
```bash
./rag-cli search similar col_123abc "deep learning applications" \
  --search-type documents \
  --max-results 5
```

**Detailed similarity with content:**
```bash
./rag-cli search similar col_123abc "convolutional neural networks" \
  --include-content \
  --similarity-threshold 0.7 \
  --format json
```

**Group results by document:**
```bash
./rag-cli search similar col_research "machine learning algorithms" \
  --group-by-document \
  --max-results 15
```

#### Expected Output

**Chunk similarity results:**
```
🔍 Similarity Search Results

Search text: "neural network architectures"
Collection: Knowledge Base (col_123abc)
Found: 8 matching chunks

┌─────────────────────────┬─────────────────────────────┬──────────┬─────────┬──────────┐
│ Document                │ Content Preview             │ Score    │ Page    │ Chunk ID │
├─────────────────────────┼─────────────────────────────┼──────────┼─────────┼──────────┤
│ Deep Learning Guide     │ Neural network architectures│ 0.94     │ 15      │ chunk_45 │
│                         │ form the backbone of modern │          │         │          │
│ ML Research Paper       │ Various neural architectures│ 0.87     │ 8       │ chunk_23 │
│                         │ have been developed for...  │          │         │          │
│ CNN Tutorial            │ Convolutional architectures │ 0.83     │ 3       │ chunk_78 │
│                         │ are specialized neural...   │          │         │          │
└─────────────────────────┴─────────────────────────────┴──────────┴─────────┴──────────┘

Average similarity: 0.85
Search time: 0.8s
```

**Document-level results:**
```
🔍 Document Similarity Results

Search text: "deep learning applications"
Collection: Research Papers (col_research)
Found: 3 matching documents

┌─────────────────────────┬──────────┬───────────┬─────────────────┬─────────────────────┐
│ Document Title          │ Score    │ Matches   │ File Type       │ Last Modified       │
├─────────────────────────┼──────────┼───────────┼─────────────────┼─────────────────────┤
│ DL Applications Review  │ 0.91     │ 12 chunks │ PDF             │ 2024-01-14 09:30:00 │
│ Computer Vision with DL │ 0.76     │ 8 chunks  │ PDF             │ 2024-01-12 15:45:00 │
│ NLP Deep Learning       │ 0.72     │ 6 chunks  │ DOCX            │ 2024-01-10 11:20:00 │
└─────────────────────────┴──────────┴───────────┴─────────────────┴─────────────────────┘
```

---

### `rag-cli search history`

View and manage search history.

#### Usage
```bash
./rag-cli search history [OPTIONS]
```

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--limit LIMIT` | Maximum entries to return | `20` |
| `--filter FILTER` | Filter by collection or query text | None |
| `--format FORMAT` | Output format (`table`, `json`, `list`) | `table` |
| `--since SINCE` | Show queries since date (YYYY-MM-DD) | Last 7 days |
| `--collection COLLECTION_ID` | Filter by specific collection | All collections |

#### Examples

**Recent search history:**
```bash
./rag-cli search history
```

**Filter by collection:**
```bash
./rag-cli search history --collection col_123abc --limit 10
```

**Search history for specific date range:**
```bash
./rag-cli search history --since 2024-01-10 --format json
```

**Filter by query text:**
```bash
./rag-cli search history --filter "machine learning"
```

#### Expected Output

**History table:**
```
🔍 Search History

┌─────────────────────┬─────────────────────────────────┬─────────────────┬──────────┬─────────────────────┐
│ Timestamp           │ Query                           │ Collection      │ Results  │ Response Time       │
├─────────────────────┼─────────────────────────────────┼─────────────────┼──────────┼─────────────────────┤
│ 2024-01-15 14:30:00 │ What are neural networks?       │ Knowledge Base  │ 5 chunks │ 2.3s               │
│ 2024-01-15 14:25:00 │ deep learning applications      │ Research Papers │ 8 chunks │ 1.8s               │
│ 2024-01-15 14:20:00 │ CNN architecture benefits       │ Knowledge Base  │ 6 chunks │ 2.1s               │
│ 2024-01-15 14:15:00 │ machine learning algorithms     │ Technical Docs  │ 12 chunks│ 3.2s               │
└─────────────────────┴─────────────────────────────────┴─────────────────┴──────────┴─────────────────────┘

Total queries: 47
Average response time: 2.1s
Most searched collection: Knowledge Base (23 queries)
```

---

### `rag-cli search replay`

Replay a previous search query from history.

#### Usage
```bash
./rag-cli search replay QUERY_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `QUERY_ID` | Search history entry ID | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--update-settings` | Apply current search settings | `false` |
| `--compare` | Compare with original results | `false` |
| `--format FORMAT` | Output format | `text` |

#### Examples

**Replay previous query:**
```bash
./rag-cli search replay query_abc123
```

**Replay with comparison:**
```bash
./rag-cli search replay query_abc123 --compare
```

**Replay with updated settings:**
```bash
./rag-cli search replay query_abc123 --update-settings
```

---

### `rag-cli search explain`

Get detailed explanation of search results and ranking.

#### Usage
```bash
./rag-cli search explain QUERY_ID [OPTIONS]
```

#### Arguments
| Argument | Description | Required |
|----------|-------------|----------|
| `QUERY_ID` | Search query ID to explain | Yes |

#### Options
| Option | Description | Default |
|--------|-------------|---------|
| `--include-embeddings` | Show embedding analysis | `false` |
| `--include-ranking` | Show ranking algorithm details | `true` |
| `--format FORMAT` | Output format (`text`, `json`) | `text` |

#### Examples

**Basic explanation:**
```bash
./rag-cli search explain query_abc123
```

**Detailed technical analysis:**
```bash
./rag-cli search explain query_abc123 \
  --include-embeddings \
  --include-ranking \
  --format json
```

#### Expected Output

**Search explanation:**
```
🔍 Search Explanation

Query ID: query_abc123
Original Query: "What are the benefits of deep learning?"
Collection: Knowledge Base (col_123abc)
Timestamp: 2024-01-15 14:30:00

📊 Search Process:
1. Query Processing:
   - Tokenized into 7 tokens
   - Generated 384-dimensional embedding
   - Processing time: 0.1s

2. Vector Search:
   - Searched 1,247 chunks across 15 documents
   - Used cosine similarity metric
   - Applied similarity threshold: 0.7
   - Search time: 0.4s

3. Result Ranking:
   - Retrieved 23 candidate chunks
   - Applied re-ranking algorithm
   - Selected top 5 results
   - Ranking time: 0.2s

🎯 Top Results Analysis:
┌──────────┬─────────────────────────────┬──────────┬─────────────────────────────┐
│ Rank     │ Document                    │ Score    │ Why This Result             │
├──────────┼─────────────────────────────┼──────────┼─────────────────────────────┤
│ 1        │ Deep Learning Fundamentals  │ 0.94     │ Direct topic match, high    │
│          │                             │          │ semantic similarity         │
│ 2        │ ML Applications Guide       │ 0.87     │ Benefits discussion,        │
│          │                             │          │ contextual relevance        │
│ 3        │ Neural Networks Overview    │ 0.83     │ Technical depth, related    │
│          │                             │          │ concepts                    │
└──────────┴─────────────────────────────┴──────────┴─────────────────────────────┘

📈 Performance Metrics:
- Total search time: 2.3s
- Chunks evaluated: 1,247
- Documents touched: 15
- Memory usage: 145 MB
- Cache hit ratio: 67%

💡 Query Optimization Suggestions:
- Query is well-formed and specific
- Consider adding more specific terms for narrower results
- Current similarity threshold (0.7) is appropriate for this query
```

## Advanced Search Features

### Multi-Collection Search

Search across multiple collections simultaneously:

```bash
#!/bin/bash
query="artificial intelligence applications"
collections=("col_research" "col_technical" "col_business")

echo "🔍 Multi-Collection Search: '$query'"
echo "========================================="

for collection in "${collections[@]}"; do
    collection_name=$(./rag-cli collections get "$collection" --format json | jq -r '.name')
    echo ""
    echo "📚 Searching: $collection_name"
    echo "--------------------------------"

    ./rag-cli search query "$collection" "$query" \
      --max-chunks 3 \
      --format text \
      --include-sources
done
```

### Batch Query Processing

Process multiple queries from a file:

```bash
#!/bin/bash
collection_id="col_123abc"
queries_file="queries.txt"
results_dir="./search_results"

mkdir -p "$results_dir"

echo "📝 Processing batch queries..."

while IFS= read -r query; do
    if [ -n "$query" ] && [[ ! "$query" =~ ^[[:space:]]*# ]]; then
        echo "Querying: $query"

        # Create safe filename
        filename=$(echo "$query" | tr ' ' '_' | tr -cd '[:alnum:]_' | cut -c1-50)

        ./rag-cli search query "$collection_id" "$query" \
          --format json \
          --include-chunks \
          > "$results_dir/${filename}.json"
    fi
done < "$queries_file"

echo "✅ Batch processing completed. Results in: $results_dir"
```

### Search Analytics Dashboard

```bash
#!/bin/bash
echo "📊 Search Analytics Dashboard"
echo "============================"

# Recent search activity
recent_searches=$(./rag-cli search history --limit 100 --format json)

# Total queries
total=$(echo "$recent_searches" | jq '.total')
echo "Recent Queries: $total"

# Average response time
avg_time=$(echo "$recent_searches" | jq '[.queries[].response_time_ms] | add / length')
printf "Average Response Time: %.1fs\n" $(echo "$avg_time / 1000" | bc -l)

# Top collections
echo ""
echo "Top Collections by Query Volume:"
echo "$recent_searches" | \
jq -r '.queries | group_by(.collection_id) | sort_by(length) | reverse | .[0:5] | .[] | [.[0].collection_name, length] | @tsv' | \
while IFS=$'\t' read -r collection count; do
    echo "  - $collection: $count queries"
done

# Query patterns
echo ""
echo "Common Query Terms:"
echo "$recent_searches" | \
jq -r '.queries[].query' | \
tr '[:upper:]' '[:lower:]' | \
tr -s '[:punct:][:space:]' '\n' | \
sort | uniq -c | sort -rn | head -10 | \
while read count term; do
    echo "  - $term: $count occurrences"
done

# Performance trends
echo ""
echo "Performance by Hour (last 24h):"
echo "$recent_searches" | \
jq -r '.queries[] | [(.timestamp | strftime("%H")), .response_time_ms] | @tsv' | \
awk '{sum[$1]+=$2; count[$1]++} END {for(h in sum) printf "  %02d:00 - Avg: %.1fs (%d queries)\n", h, sum[h]/(count[h]*1000), count[h]}' | \
sort
```

## Search Optimization

### Query Performance Tuning

**Optimize similarity threshold:**
```bash
#!/bin/bash
collection_id="col_123abc"
query="machine learning algorithms"

echo "🎯 Similarity Threshold Optimization"
echo "==================================="

for threshold in 0.5 0.6 0.7 0.8 0.9; do
    echo "Testing threshold: $threshold"

    result=$(./rag-cli search query "$collection_id" "$query" \
      --similarity-threshold "$threshold" \
      --format json \
      --max-chunks 5)

    chunks=$(echo "$result" | jq '.retrieved_chunks | length')
    avg_score=$(echo "$result" | jq '[.retrieved_chunks[].similarity_score] | add / length')
    time=$(echo "$result" | jq '.response.response_time_ms')

    printf "  Chunks: %d, Avg Score: %.3f, Time: %dms\n" "$chunks" "$avg_score" "$time"
done
```

**Index health check:**
```bash
#!/bin/bash
collection_id="col_123abc"

echo "🏥 Search Index Health Check"
echo "============================"

# Test query performance
test_queries=("machine learning" "neural networks" "deep learning" "AI applications")

for query in "${test_queries[@]}"; do
    echo "Testing: $query"

    result=$(./rag-cli search similar "$collection_id" "$query" \
      --max-results 10 \
      --format json)

    results_count=$(echo "$result" | jq '.results | length')
    avg_similarity=$(echo "$result" | jq '[.results[].similarity_score] | add / length')
    search_time=$(echo "$result" | jq '.search_time_ms')

    printf "  Results: %d, Avg Similarity: %.3f, Time: %dms\n" "$results_count" "$avg_similarity" "$search_time"
done

# Check for performance degradation
echo ""
echo "Performance Recommendations:"
echo "- Results < 5: Consider lowering similarity threshold"
echo "- Avg Similarity < 0.7: May need better query formulation"
echo "- Time > 3000ms: Consider index optimization"
```

## Integration Examples

### Slack Bot Integration
```bash
#!/bin/bash
# Simple Slack webhook integration for search

slack_webhook="$SLACK_WEBHOOK_URL"
collection_id="col_knowledge"

query="$1"
if [ -z "$query" ]; then
    echo "Usage: $0 'your search query'"
    exit 1
fi

echo "🔍 Searching knowledge base..."

# Perform search
result=$(./rag-cli search query "$collection_id" "$query" \
  --max-chunks 3 \
  --format json \
  --max-tokens 200)

# Extract answer and sources
answer=$(echo "$result" | jq -r '.response.answer')
sources=$(echo "$result" | jq -r '.sources[] | "• " + .document_title')

# Format for Slack
slack_message=$(cat <<EOF
{
  "text": "Knowledge Base Search Results",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Query:* $query\n\n*Answer:*\n$answer"
      }
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Sources:*\n$sources"
      }
    }
  ]
}
EOF
)

# Send to Slack
curl -X POST -H 'Content-type: application/json' \
  --data "$slack_message" \
  "$slack_webhook"

echo "✅ Results sent to Slack"
```

### Search API Wrapper
```python
#!/usr/bin/env python3
"""
Simple REST API wrapper for RAG CLI search
"""

from flask import Flask, request, jsonify
import subprocess
import json

app = Flask(__name__)

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    collection_id = data.get('collection_id')
    query = data.get('query')

    if not collection_id or not query:
        return jsonify({'error': 'collection_id and query required'}), 400

    try:
        # Execute CLI search
        cmd = [
            './rag-cli', 'search', 'query',
            collection_id, query,
            '--format', 'json',
            '--max-chunks', str(data.get('max_chunks', 5)),
            '--similarity-threshold', str(data.get('similarity_threshold', 0.7))
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            return json.loads(result.stdout)
        else:
            return jsonify({'error': result.stderr}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

## Next Steps

After mastering search operations:
1. **[User Commands](users.md)** - Manage user access and permissions
2. **[Configuration](../configuration.md)** - Optimize search performance
3. **[Collection Management](collections.md)** - Advanced collection setup for better search
4. **[Troubleshooting](../troubleshooting.md)** - Resolve search performance issues
