#!/usr/bin/env python3
"""Create default reranking template."""

import requests

API_BASE = "http://localhost:8000"
USER_UUID = "ee76317f-3b6f-4fea-8b74-56483731f58c"

template_data = {
    "name": "Default Reranking Template",
    "template_type": "RERANKING",
    "template_format": "Rate the relevance of this document to the query on a scale of 0-{scale}:\n\nQuery: {query}\n\nDocument: {context}\n\nRelevance score:",
    "input_variables": {"query": "The search query", "context": "The document text", "scale": "Score scale (e.g., 10)"},
    "is_default": True,
    "max_context_length": 4000,
}

print("Creating reranking template...")
response = requests.post(
    f"{API_BASE}/api/users/{USER_UUID}/prompt-templates",
    headers={
        "Content-Type": "application/json",
        "X-User-UUID": USER_UUID,
    },
    json=template_data,
)

if response.status_code == 200:
    print("✅ Template created successfully!")
    print(response.json())
else:
    print(f"❌ Failed: {response.status_code}")
    print(response.text)
