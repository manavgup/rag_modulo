#!/usr/bin/env python3
"""Compare API search vs Direct Milvus+WatsonX search.

This script:
1. Takes collection ID/name and search query as input
2. Calls the API search endpoint to get results
3. Calls Milvus directly to get top N chunks
4. Calls WatsonX directly with the same prompt format
5. Compares the results side-by-side

Usage:
    python test_search_comparison.py --collection-id <uuid> --query "search query"
    python test_search_comparison.py --collection-name <name> --query "search query"

Examples:
    python test_search_comparison.py --collection-id 0fa6e28b-3b76-494a-97cb-df3c9288747e --query "What percentage of IBM's workforce consists of women?"
    python test_search_comparison.py --collection-name IBM --query "What percentage of IBM's workforce consists of women?"
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(backend_dir))

from dotenv import load_dotenv
from pymilvus import Collection, connections
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.foundation_models import Embeddings, Model
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams
from ibm_watsonx_ai.metanames import EmbedTextParamsMetaNames as EmbedParams
import requests

# Load environment variables
load_dotenv()


def _log_direct_embedding(query: str, project_id: str, api_url: str, stage: str, embedding: list | None = None) -> None:
    """Log embedding generation details for direct Milvus path."""
    try:
        from datetime import datetime

        debug_dir = "/tmp/rag_debug"
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = f"{debug_dir}/embedding_generation_direct_{stage.lower()}_{timestamp}.txt"

        with open(debug_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write(f"EMBEDDING GENERATION - DIRECT MILVUS PATH - {stage}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")

            f.write("INPUT TEXT:\n")
            f.write("-" * 80 + "\n")
            f.write(f"{query[:200]}{'...' if len(query) > 200 else ''}\n\n")

            f.write("WATSONX CONFIGURATION:\n")
            f.write("-" * 80 + "\n")
            f.write(f"Embedding Model: ibm/slate-125m-english-rtrvr-v2\n")
            f.write(f"Embedding Dimension: 768\n")
            f.write(f"Project ID: {project_id[:20]}...\n")
            f.write(f"API URL: {api_url}\n\n")

            if embedding is not None and stage == "AFTER":
                f.write("GENERATED EMBEDDING:\n")
                f.write("-" * 80 + "\n")
                f.write(f"Dimension: {len(embedding)}\n")
                f.write(f"First 10 values: {embedding[:10]}\n")
                f.write(f"Last 10 values: {embedding[-10:]}\n")
                f.write(f"Mean: {sum(embedding) / len(embedding):.6f}\n")
                f.write(f"Min: {min(embedding):.6f}\n")
                f.write(f"Max: {max(embedding):.6f}\n\n")

            f.write("=" * 80 + "\n")
            f.write(f"END OF EMBEDDING GENERATION LOG - DIRECT - {stage}\n")
            f.write("=" * 80 + "\n")

        print(f"📝 Direct embedding generation ({stage}) logged to: {debug_file}")

    except Exception as e:
        print(f"⚠️  Failed to log direct embedding generation ({stage}): {e}")



def get_collection_id_from_name(collection_name: str, api_url: str = "http://localhost:8000") -> str | None:
    """Get collection ID from collection name via API."""
    try:
        # Call the API to list collections
        response = requests.get(f"{api_url}/api/collections")

        if response.status_code == 200:
            collections = response.json()
            for collection in collections:
                if collection.get("name") == collection_name:
                    collection_id = collection.get("id")
                    print(f"✅ Found collection '{collection_name}' with ID: {collection_id}")
                    return collection_id
            print(f"❌ Collection '{collection_name}' not found")
            return None
        else:
            print(f"⚠️  API returned status {response.status_code}: {response.text}")
            return None
    except Exception as e:
        print(f"⚠️  Could not query API: {e}")
        return None


def get_milvus_collection_name(collection_id: str, api_url: str = "http://localhost:8000") -> str | None:
    """Get Milvus collection name from API using collection ID."""
    try:
        # Call the API to get collection info
        response = requests.get(f"{api_url}/api/collections/{collection_id}")

        if response.status_code == 200:
            collection_data = response.json()
            vector_db_name = collection_data.get("vector_db_name")
            if vector_db_name:
                print(f"✅ Found via API: {vector_db_name}")
                return vector_db_name
        else:
            print(f"⚠️  API returned status {response.status_code}: {response.text}")
    except Exception as e:
        print(f"⚠️  Could not query API: {e}")

    # Fallback: try UUID format
    collection_uuid = collection_id.replace("-", "")
    fallback_name = f"collection_{collection_uuid}"
    print(f"⚠️  Using fallback collection name: {fallback_name}")
    return fallback_name


def call_api_search(collection_id: str, query: str, user_id: str) -> dict:
    """Call the RAG API search endpoint."""
    api_url = "http://localhost:8000/api/search"

    payload = {
        "question": query,
        "collection_id": collection_id,
        "user_id": user_id,
        "config_metadata": {}
    }

    print("\n" + "=" * 80)
    print("1️⃣  CALLING API SEARCH")
    print("=" * 80)
    print(f"URL: {api_url}")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    try:
        response = requests.post(api_url, json=payload, timeout=60)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            result = response.json()
            print(f"✅ API Search successful")
            print(f"   Answer length: {len(result.get('answer', ''))} chars")
            print(f"   Documents: {len(result.get('documents', []))}")
            print(f"   Execution time: {result.get('execution_time', 0):.2f}s")
            return result
        else:
            print(f"❌ API Search failed: {response.text}")
            return {}
    except Exception as e:
        print(f"❌ API Search error: {e}")
        return {}


def call_direct_milvus_watsonx(collection_name: str, query: str, top_k: int = 10) -> dict:
    """Call Milvus directly, then WatsonX with the same prompt format."""
    print("\n" + "=" * 80)
    print("2️⃣  CALLING MILVUS + WATSONX DIRECTLY")
    print("=" * 80)

    # Get credentials
    api_key = os.getenv("WATSONX_APIKEY") or os.getenv("WATSONX_API_KEY")
    project_id = os.getenv("WATSONX_INSTANCE_ID") or os.getenv("WATSONX_PROJECT_ID") or "3f77f23d-71b7-426b-ae13-bc4710769880"
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key:
        print("❌ Missing WATSONX_APIKEY")
        return {}

    # Initialize WatsonX clients
    try:
        credentials = Credentials(api_key=api_key, url=url)

        # TESTING: Removed TRUNCATE_INPUT_TOKENS to match API path changes
        # Use SAME parameters as API path (backend/vectordbs/utils/watsonx.py:122-124)
        embed_params = {
            EmbedParams.RETURN_OPTIONS: {"input_text": True},
        }

        embeddings_client = Embeddings(
            model_id="ibm/slate-125m-english-rtrvr-v2",
            credentials=credentials,
            project_id=project_id,
            params=embed_params
        )

        llm_model = Model(
            model_id="ibm/granite-3-3-8b-instruct",
            credentials=credentials,
            project_id=project_id,
            params={
                GenParams.MAX_NEW_TOKENS: 800,
                GenParams.TEMPERATURE: 0.7,
                GenParams.TOP_K: 50,
                GenParams.TOP_P: 1.0,
                GenParams.STOP_SEQUENCES: ['##', '\n\nQuestion:', '\n\n##']
            }
        )
        print("✅ WatsonX clients initialized")
    except Exception as e:
        print(f"❌ WatsonX initialization failed: {e}")
        return {}

    # Connect to Milvus
    try:
        connections.connect(alias="default", host="localhost", port=19530)
        collection = Collection(collection_name)
        collection.load()
        print(f"✅ Connected to Milvus: {collection_name}")
        print(f"   Entities: {collection.num_entities:,}")
    except Exception as e:
        print(f"❌ Milvus connection failed: {e}")
        return {}

    # Get embeddings for query
    try:
        # LOG BEFORE EMBEDDING GENERATION
        _log_direct_embedding(query, project_id, url, "BEFORE", None)

        result = embeddings_client.embed_documents(texts=[query])
        query_embedding = result[0]
        print(f"✅ Query embedding generated (dim: {len(query_embedding)})")

        # LOG AFTER EMBEDDING GENERATION
        _log_direct_embedding(query, project_id, url, "AFTER", query_embedding)
    except Exception as e:
        print(f"❌ Embedding failed: {e}")
        connections.disconnect("default")
        return {}

    # Search Milvus
    try:
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}
        results = collection.search(
            data=[query_embedding],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=["text", "document_name", "page_number", "chunk_number"],
        )
        print(f"✅ Milvus search completed: {len(results[0])} results")
    except Exception as e:
        print(f"❌ Milvus search failed: {e}")
        connections.disconnect("default")
        return {}

    # Extract retrieved chunks
    retrieved_chunks = []
    print(f"\n📄 TOP {min(top_k, len(results[0]))} CHUNKS:")
    print("-" * 80)

    for i, hit in enumerate(results[0], 1):
        text = hit.entity.get("text") or ""
        doc_name = hit.entity.get("document_name") or "unknown"
        page = hit.entity.get("page_number") or "?"
        chunk = hit.entity.get("chunk_number") or "?"
        score = hit.score

        print(f"{i}. Score: {score:.4f} | Page: {page} | Chunk: {chunk}")
        print(f"   Doc: {doc_name}")
        print(f"   Text: {text[:150]}...")
        print()

        retrieved_chunks.append({
            "text": text,
            "score": score,
            "page": page,
            "doc": doc_name
        })

    # LOG DIRECT SEARCH CHUNKS TO FILE
    try:
        from datetime import datetime

        debug_dir = "/tmp/rag_debug"
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = f"{debug_dir}/chunks_direct_milvus_{timestamp}.txt"

        with open(debug_file, "w", encoding="utf-8") as f:
            f.write("=" * 80 + "\n")
            f.write("DIRECT MILVUS SEARCH CHUNKS\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write("=" * 80 + "\n\n")
            f.write(f"Query: {query}\n")
            f.write(f"Collection: {collection_name}\n")
            f.write(f"Top K: {top_k}\n")
            f.write(f"Total chunks: {len(retrieved_chunks)}\n\n")
            f.write("=" * 80 + "\n")
            f.write("CHUNKS:\n")
            f.write("=" * 80 + "\n\n")

            for i, chunk in enumerate(retrieved_chunks, 1):
                f.write(f"CHUNK #{i}\n")
                f.write("-" * 80 + "\n")
                f.write(f"Score: {chunk['score']:.6f}\n")
                f.write(f"Document: {chunk['doc']}\n")
                f.write(f"Page: {chunk['page']}\n")
                f.write(f"Text Length: {len(chunk['text'])} chars\n\n")
                f.write("Full Text:\n")
                f.write(chunk['text'])
                f.write("\n\n" + "-" * 80 + "\n\n")

            f.write("=" * 80 + "\n")
            f.write("END OF DIRECT MILVUS LOG\n")
            f.write("=" * 80 + "\n")

        print(f"\n✅ Direct Milvus chunks logged to: {debug_file}")
    except Exception as e:
        print(f"\n⚠️  Failed to log direct chunks: {e}")

    # Build context exactly like the API does
    context_text = " ".join([chunk["text"] for chunk in retrieved_chunks])

    # Build prompt matching the API format
    prompt = f"""Question: {query}

Context: {context_text}

Answer:"""

    print(f"\n🔤 Prompt built: {len(prompt)} chars")

    # Call LLM
    try:
        print("Calling WatsonX LLM...")
        llm_response = llm_model.generate_text(prompt=prompt)

        if isinstance(llm_response, dict) and "results" in llm_response:
            answer = llm_response["results"][0]["generated_text"].strip()
        else:
            answer = str(llm_response).strip()

        print(f"✅ LLM response received: {len(answer)} chars")
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        answer = ""

    # Cleanup
    connections.disconnect("default")

    return {
        "answer": answer,
        "chunks": retrieved_chunks,
        "prompt": prompt,
        "num_chunks": len(retrieved_chunks)
    }


def compare_results(api_result: dict, direct_result: dict, query: str):
    """Compare API vs Direct results."""
    print("\n" + "=" * 80)
    print("📊 COMPARISON RESULTS")
    print("=" * 80)

    print(f"\n🔍 Query: {query}")

    # Compare answers
    print("\n" + "-" * 80)
    print("🤖 API ANSWER:")
    print("-" * 80)
    api_answer = api_result.get("answer", "No answer")
    print(api_answer)
    print(f"\nLength: {len(api_answer)} chars")

    print("\n" + "-" * 80)
    print("🔧 DIRECT MILVUS+WATSONX ANSWER:")
    print("-" * 80)
    direct_answer = direct_result.get("answer", "No answer")
    print(direct_answer)
    print(f"\nLength: {len(direct_answer)} chars")

    # Compare document retrieval
    print("\n" + "-" * 80)
    print("📚 DOCUMENT RETRIEVAL:")
    print("-" * 80)
    api_docs = len(api_result.get("documents", []))
    direct_chunks = direct_result.get("num_chunks", 0)
    print(f"API retrieved: {api_docs} documents")
    print(f"Direct retrieved: {direct_chunks} chunks")

    # Show first document/chunk from each
    if api_result.get("documents"):
        first_api_doc = api_result["documents"][0]
        print(f"\nAPI first document:")
        print(f"  - Source: {first_api_doc.get('source', 'N/A')}")
        print(f"  - Score: {first_api_doc.get('score', 'N/A')}")
        print(f"  - Page: {first_api_doc.get('page_number', 'N/A')}")

    if direct_result.get("chunks"):
        first_direct_chunk = direct_result["chunks"][0]
        print(f"\nDirect first chunk:")
        print(f"  - Document: {first_direct_chunk.get('doc', 'N/A')}")
        print(f"  - Score: {first_direct_chunk.get('score', 'N/A'):.4f}")
        print(f"  - Page: {first_direct_chunk.get('page', 'N/A')}")
        print(f"  - Text preview: {first_direct_chunk.get('text', '')[:200]}...")

    # Analysis
    print("\n" + "-" * 80)
    print("🔬 ANALYSIS:")
    print("-" * 80)

    if api_answer == direct_answer:
        print("✅ Answers are IDENTICAL")
    elif api_answer.strip() == direct_answer.strip():
        print("✅ Answers are IDENTICAL (minor whitespace differences)")
    else:
        print("❌ Answers are DIFFERENT")
        print(f"   API answer starts with: {api_answer[:100]}...")
        print(f"   Direct answer starts with: {direct_answer[:100]}...")

    # Check if answers say "no information"
    api_no_info = any(phrase in api_answer.lower() for phrase in ["not mentioned", "no information", "does not include", "cannot answer"])
    direct_no_info = any(phrase in direct_answer.lower() for phrase in ["not mentioned", "no information", "does not include", "cannot answer"])

    if api_no_info and direct_no_info:
        print("\n⚠️  BOTH say information is not available")
        print("   → The retrieved chunks likely don't contain the answer")
    elif api_no_info and not direct_no_info:
        print("\n⚠️  API says no info, but Direct answered")
        print("   → Pipeline issue in API (maybe CoT or context building)")
    elif not api_no_info and direct_no_info:
        print("\n⚠️  Direct says no info, but API answered")
        print("   → API may be using additional context or processing")


def main():
    """Main comparison script."""
    parser = argparse.ArgumentParser(
        description="Compare API search vs Direct Milvus+WatsonX search",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Using collection ID:
  python test_search_comparison.py --collection-id 0fa6e28b-3b76-494a-97cb-df3c9288747e --query "What percentage of IBM's workforce consists of women?"

  # Using collection name:
  python test_search_comparison.py --collection-name IBM --query "What percentage of IBM's workforce consists of women?"

  # Short form:
  python test_search_comparison.py -i 0fa6e28b-3b76-494a-97cb-df3c9288747e -q "search query"
  python test_search_comparison.py -n IBM -q "search query"
        """
    )

    # Collection identifier (mutually exclusive)
    collection_group = parser.add_mutually_exclusive_group(required=True)
    collection_group.add_argument(
        "--collection-id", "-i",
        help="Collection UUID"
    )
    collection_group.add_argument(
        "--collection-name", "-n",
        help="Collection name (e.g., 'IBM')"
    )

    # Query
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query"
    )

    args = parser.parse_args()

    print("=" * 80)
    print("🔬 SEARCH COMPARISON: API vs Direct Milvus+WatsonX")
    print("=" * 80)

    api_url = os.getenv("API_URL") or "http://localhost:8000"

    # Get collection ID (either provided or looked up from name)
    if args.collection_name:
        print(f"Collection Name: {args.collection_name}")
        print(f"\n🔍 Looking up collection ID from name...")
        collection_id = get_collection_id_from_name(args.collection_name, api_url)
        if not collection_id:
            print(f"\n❌ Could not find collection '{args.collection_name}'")
            sys.exit(1)
    else:
        collection_id = args.collection_id
        print(f"Collection ID: {collection_id}")

    print(f"Query: {args.query}")

    # Get Milvus collection name via API
    print(f"\n🔍 Looking up Milvus collection name via API...")
    collection_name = get_milvus_collection_name(collection_id, api_url)
    print(f"   Milvus collection: {collection_name}")

    # We need a user_id for the API call
    # For now, use a test user ID
    user_id = os.getenv("TEST_USER_ID") or "d1f93297-3e3c-42b0-8da7-09efde032c25"
    print(f"   User ID: {user_id}")

    # Call API search
    api_result = call_api_search(collection_id, args.query, user_id)

    # Call Milvus + WatsonX directly
    direct_result = call_direct_milvus_watsonx(collection_name, args.query, top_k=10)

    # Compare results
    if api_result and direct_result:
        compare_results(api_result, direct_result, args.query)
    else:
        print("\n❌ Comparison failed - one or both methods did not return results")

    print("\n" + "=" * 80)
    print("✅ Comparison complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()
