# API Examples

This page provides practical examples for using the RAG Modulo API.

## Authentication Examples

### Register and Login

```python
import requests

BASE_URL = "http://localhost:8000/api"

# Register new user
register_response = requests.post(
    f"{BASE_URL}/auth/register",
    json={
        "username": "user@example.com",
        "password": "secure_password123",
        "email": "user@example.com"
    }
)
user_id = register_response.json()["user_id"]

# Login to get token
login_response = requests.post(
    f"{BASE_URL}/auth/login",
    json={
        "username": "user@example.com",
        "password": "secure_password123"
    }
)
token = login_response.json()["access_token"]

# Use token for authenticated requests
headers = {"Authorization": f"Bearer {token}"}
```

## Collection Examples

### Create and Manage Collections

```python
# Create collection
collection_response = requests.post(
    f"{BASE_URL}/collections",
    headers=headers,
    json={
        "name": "Research Papers",
        "description": "AI and ML research papers",
        "user_id": user_id
    }
)
collection_id = collection_response.json()["id"]

# List all collections
collections = requests.get(
    f"{BASE_URL}/collections",
    headers=headers
)
print(f"Total collections: {len(collections.json())}")

# Get specific collection
collection = requests.get(
    f"{BASE_URL}/collections/{collection_id}",
    headers=headers
)
print(f"Collection: {collection.json()['name']}")
```

## Document Examples

### Upload Documents

```python
# Upload PDF document
with open("research_paper.pdf", "rb") as f:
    files = {"file": ("research_paper.pdf", f, "application/pdf")}
    data = {"collection_id": collection_id}

    upload_response = requests.post(
        f"{BASE_URL}/documents/upload",
        headers=headers,
        files=files,
        data=data
    )
    document_id = upload_response.json()["id"]
    print(f"Document uploaded: {document_id}")

# List documents in collection
documents = requests.get(
    f"{BASE_URL}/documents",
    headers=headers,
    params={"collection_id": collection_id}
)
print(f"Total documents: {len(documents.json())}")
```

### Batch Upload

```python
import os

# Upload multiple documents
document_ids = []
for filename in os.listdir("./documents"):
    if filename.endswith(".pdf"):
        with open(f"./documents/{filename}", "rb") as f:
            files = {"file": (filename, f, "application/pdf")}
            data = {"collection_id": collection_id}

            response = requests.post(
                f"{BASE_URL}/documents/upload",
                headers=headers,
                files=files,
                data=data
            )
            document_ids.append(response.json()["id"])

print(f"Uploaded {len(document_ids)} documents")
```

## Search Examples

### Basic Search

```python
# Simple search query
search_response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json={
        "question": "What is machine learning?",
        "collection_id": collection_id,
        "user_id": user_id
    }
)

result = search_response.json()
print(f"Answer: {result['answer']}")
print(f"Sources: {len(result['sources'])} documents")
```

### Chain of Thought Search

```python
# Complex query with CoT reasoning
cot_response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json={
        "question": "How does machine learning work and what are its key components?",
        "collection_id": collection_id,
        "user_id": user_id,
        "config_metadata": {
            "cot_enabled": True,
            "show_cot_steps": True,
            "max_reasoning_depth": 3
        }
    }
)

result = cot_response.json()
print(f"Answer: {result['answer']}")

if result.get("reasoning_steps"):
    print("\nReasoning Steps:")
    for i, step in enumerate(result["reasoning_steps"], 1):
        print(f"{i}. {step['sub_question']}")
        print(f"   Answer: {step['answer'][:100]}...")
```

### Advanced Search Configuration

```python
# Search with advanced configuration
advanced_response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json={
        "question": "Explain deep learning architectures",
        "collection_id": collection_id,
        "user_id": user_id,
        "config_metadata": {
            "max_results": 10,
            "min_score": 0.75,
            "use_reranking": True,
            "include_metadata": True
        }
    }
)

result = advanced_response.json()
for i, source in enumerate(result["sources"], 1):
    print(f"{i}. Score: {source['score']:.2f}")
    print(f"   Content: {source['content'][:100]}...")
```

## Conversation Examples

### Create Conversation Session

```python
# Create new conversation session
session_response = requests.post(
    f"{BASE_URL}/conversations/sessions",
    headers=headers,
    json={
        "user_id": user_id,
        "title": "ML Research Q&A",
        "metadata": {"topic": "machine_learning"}
    }
)
session_id = session_response.json()["id"]

# Add messages to session
messages = [
    {"role": "user", "message_type": "question", "content": "What is supervised learning?"},
    {"role": "assistant", "message_type": "answer", "content": "Supervised learning is..."}
]

for msg in messages:
    requests.post(
        f"{BASE_URL}/conversations/messages",
        headers=headers,
        json={
            "session_id": session_id,
            **msg,
            "token_count": len(msg["content"].split())
        }
    )

# Get conversation history
history = requests.get(
    f"{BASE_URL}/conversations/sessions/{session_id}/messages",
    headers=headers
)
print(f"Message count: {len(history.json()['messages'])}")
```

### Multi-Turn Conversation

```python
# Interactive conversation loop
session_id = create_session(user_id)

while True:
    user_input = input("You: ")
    if user_input.lower() in ["exit", "quit"]:
        break

    # Add user message
    requests.post(
        f"{BASE_URL}/conversations/messages",
        headers=headers,
        json={
            "session_id": session_id,
            "role": "user",
            "message_type": "question",
            "content": user_input
        }
    )

    # Get AI response via search
    search_response = requests.post(
        f"{BASE_URL}/search",
        headers=headers,
        json={
            "question": user_input,
            "collection_id": collection_id,
            "user_id": user_id
        }
    )
    answer = search_response.json()["answer"]

    # Add assistant message
    requests.post(
        f"{BASE_URL}/conversations/messages",
        headers=headers,
        json={
            "session_id": session_id,
            "role": "assistant",
            "message_type": "answer",
            "content": answer
        }
    )

    print(f"AI: {answer}")
```

## Pipeline Examples

### Create Custom Pipeline

```python
# Create custom pipeline with specific stages
pipeline_response = requests.post(
    f"{BASE_URL}/pipelines",
    headers=headers,
    json={
        "name": "Fast Search Pipeline",
        "user_id": user_id,
        "stages": ["retrieval", "generation"],
        "is_default": False,
        "config": {
            "retrieval": {
                "max_results": 5,
                "min_score": 0.8
            },
            "generation": {
                "max_tokens": 300,
                "temperature": 0.7
            }
        }
    }
)
pipeline_id = pipeline_response.json()["id"]

# Use custom pipeline for search
search_response = requests.post(
    f"{BASE_URL}/search",
    headers=headers,
    json={
        "question": "What is neural network?",
        "collection_id": collection_id,
        "user_id": user_id,
        "config_metadata": {
            "pipeline_id": pipeline_id
        }
    }
)
```

## Error Handling Examples

### Robust Error Handling

```python
import requests
from requests.exceptions import RequestException

def safe_api_call(url, method="GET", **kwargs):
    """Make API call with comprehensive error handling."""
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 401:
            print("Authentication failed. Please check your token.")
        elif e.response.status_code == 404:
            print("Resource not found.")
        elif e.response.status_code == 422:
            print("Validation error:")
            print(e.response.json()["detail"])
        else:
            print(f"HTTP error: {e}")
        return None

    except requests.exceptions.ConnectionError:
        print("Connection error. Is the server running?")
        return None

    except requests.exceptions.Timeout:
        print("Request timed out.")
        return None

    except RequestException as e:
        print(f"Request failed: {e}")
        return None

# Usage
result = safe_api_call(
    f"{BASE_URL}/search",
    method="POST",
    headers=headers,
    json=search_query
)
```

## Batch Processing Examples

### Process Multiple Queries

```python
# Batch search queries
queries = [
    "What is machine learning?",
    "Explain neural networks",
    "What is deep learning?",
    "How does NLP work?"
]

results = []
for query in queries:
    response = requests.post(
        f"{BASE_URL}/search",
        headers=headers,
        json={
            "question": query,
            "collection_id": collection_id,
            "user_id": user_id
        }
    )
    results.append({
        "query": query,
        "answer": response.json()["answer"],
        "sources": len(response.json()["sources"])
    })

# Display results
for r in results:
    print(f"Q: {r['query']}")
    print(f"A: {r['answer'][:100]}...")
    print(f"Sources: {r['sources']}\n")
```

## See Also

- [API Endpoints](endpoints.md) - Available endpoints
- [API Schemas](schemas.md) - Request/response schemas
- [Authentication](authentication.md) - Authentication guide
- [Error Handling](error-handling.md) - Error response format
