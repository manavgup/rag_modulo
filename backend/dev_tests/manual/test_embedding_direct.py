#!/usr/bin/env python3
"""Direct embedding test bypassing the entire pipeline.

Uses simple credential loading and calls WatsonX directly.

Usage:
    python test_embedding_direct.py <collection_name> "your search query"
    python test_embedding_direct.py collection_0fa6e28b3b76494a97cbdf3c9288747e "What percentage of IBM's workforce consists of women?"
"""

import os
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

from dotenv import load_dotenv  # noqa: E402
from ibm_watsonx_ai import Credentials  # noqa: E402
from ibm_watsonx_ai.foundation_models import Embeddings, Model  # noqa: E402
from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams  # noqa: E402
from pymilvus import Collection, connections  # noqa: E402

# Load environment variables
load_dotenv()


def test_direct_embeddings():
    """Test embeddings and retrieval directly."""

    # Get collection identifier and query from command line
    if len(sys.argv) < 3:
        print('Usage: python test_embedding_direct.py <collection_id_or_name> "query"')
        print("\nExamples:")
        print(
            '  python test_embedding_direct.py 0fa6e28b-3b76-494a-97cb-df3c9288747e "What percentage of IBM\'s workforce consists of women?"'
        )
        print('  python test_embedding_direct.py collection_0fa6e28b3b76494a97cbdf3c9288747e "women workforce"')
        sys.exit(1)

    collection_input = sys.argv[1]
    queries = [" ".join(sys.argv[2:])]

    # Determine if input is a UUID (collection ID) or Milvus collection name
    if collection_input.startswith("collection_"):
        # Already a Milvus collection name
        collection_name = collection_input
    else:
        # Assume it's a UUID - convert to Milvus collection name
        # Remove hyphens from UUID to match Milvus naming convention
        collection_uuid = collection_input.replace("-", "")
        collection_name = f"collection_{collection_uuid}"

    print("=" * 80)
    print("DIRECT EMBEDDING + MILVUS RETRIEVAL TEST")
    print("=" * 80)
    print(f"\nCollection: {collection_name}")
    print(f"Testing {len(queries)} queries\n")

    # Get credentials from environment
    print("Loading WatsonX credentials from environment...")
    api_key = os.getenv("WATSONX_APIKEY") or os.getenv("WATSONX_API_KEY")
    project_id = (
        os.getenv("WATSONX_INSTANCE_ID") or os.getenv("WATSONX_PROJECT_ID") or "3f77f23d-71b7-426b-ae13-bc4710769880"
    )
    url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")

    if not api_key:
        print("❌ Missing WATSONX_APIKEY in environment")
        print("\nRequired environment variables:")
        print("  WATSONX_APIKEY=<your-api-key>")
        print("  WATSONX_URL=<watsonx-url> (optional, defaults to us-south)")
        print("  WATSONX_INSTANCE_ID=<project-id> (optional, uses default)")
        return

    print("✅ Credentials loaded")
    print(f"   URL: {url}")
    print(f"   Project ID: {project_id[:8]}...")

    # Initialize WatsonX embeddings client directly
    print("\nInitializing WatsonX embeddings client...")
    try:
        credentials = Credentials(api_key=api_key, url=url)

        embeddings_client = Embeddings(
            model_id="ibm/slate-125m-english-rtrvr-v2",  # Match .env setting
            credentials=credentials,
            project_id=project_id,
        )
        print("✅ WatsonX embeddings client initialized (ibm/slate-125m-english-rtrvr-v2)")

        # Initialize LLM for text generation
        llm_model = Model(
            model_id="ibm/granite-3-3-8b-instruct",  # Match .env setting
            credentials=credentials,
            project_id=project_id,
            params={
                GenParams.MAX_NEW_TOKENS: 500,
                GenParams.TEMPERATURE: 0.7,
                GenParams.TOP_K: 50,
                GenParams.TOP_P: 0.9,
            },
        )
        print("✅ WatsonX LLM initialized (ibm/granite-3-3-8b-instruct)")

    except Exception as e:
        print(f"❌ Failed to initialize embeddings client: {e}")
        import traceback

        traceback.print_exc()
        return

    # Connect to Milvus
    print("\nConnecting to Milvus at localhost:19530...")
    try:
        connections.connect(
            alias="default",
            host="localhost",
            port=19530,
        )
        print("✅ Connected to Milvus")
    except Exception as e:
        print(f"❌ Failed to connect to Milvus: {e}")
        return

    # Load collection
    print(f"Loading collection '{collection_name}'...\n")
    try:
        collection = Collection(collection_name)
        collection.load()
        print("✅ Collection loaded\n")
    except Exception as e:
        print(f"❌ Failed to load collection: {e}")
        connections.disconnect("default")
        return

    # Test each query
    for i, query in enumerate(queries, 1):
        print("=" * 80)
        print(f"Query {i}: {query}")
        print("=" * 80)

        # Get embeddings for query
        print("Getting embeddings...")
        try:
            result = embeddings_client.embed_documents(texts=[query])
            query_embedding = result[0]

            print("✅ Embeddings generated")
            print(f"   Dimension: {len(query_embedding)}")
            print(f"   Sample (first 5 values): {query_embedding[:5]}")

        except Exception as e:
            print(f"❌ Failed to get embeddings: {e}")
            import traceback

            traceback.print_exc()
            continue

        # Search Milvus directly
        print("\nSearching Milvus...")
        search_params = {"metric_type": "COSINE", "params": {"nprobe": 10}}

        try:
            results = collection.search(
                data=[query_embedding],
                anns_field="embedding",  # Field name is "embedding" (singular)
                param=search_params,
                limit=20,  # Match .env TOP_K setting
                output_fields=["text", "document_name", "page_number", "chunk_number"],
            )
        except Exception as e:
            print(f"❌ Search failed: {e}")
            import traceback

            traceback.print_exc()
            continue

        # Display results
        print("\nTop 20 Results:")
        print("-" * 80)

        if not results or len(results) == 0 or len(results[0]) == 0:
            print("❌ NO RESULTS FOUND")
            print("\n")
            continue

        # Collect chunks for RAG
        retrieved_chunks = []
        for j, hit in enumerate(results[0], 1):
            score = hit.score
            text = hit.entity.get("text") or ""
            doc_name = hit.entity.get("document_name") or "unknown"
            page = hit.entity.get("page_number") or "?"
            chunk = hit.entity.get("chunk_number") or "?"

            print(f"{j}. Score: {score:.4f} | Page: {page} | Chunk: {chunk}")
            print(f"   Doc: {doc_name}")
            print(f"   Text: {text[:150]}...")
            print()

            # Store full text for RAG
            retrieved_chunks.append({"text": text, "score": score, "page": page, "chunk": chunk, "doc": doc_name})

        # Generate LLM response using retrieved chunks
        print("\n" + "=" * 80)
        print("GENERATING LLM RESPONSE")
        print("=" * 80)

        # Format context from top 5 chunks
        context_parts = []
        for idx, chunk in enumerate(retrieved_chunks[:5], 1):
            context_parts.append(f"[Chunk {idx} - Page {chunk['page']}]:\n{chunk['text']}\n")

        context = "\n".join(context_parts)

        # Simple RAG prompt
        rag_prompt = f"""You are a helpful RAG assistant. Answer the user's question based ONLY on the provided context.

Context:
{context}

Question: {query}

Answer:"""

        print(f"\nPrompt length: {len(rag_prompt)} characters")
        print("Calling LLM...")

        try:
            llm_response = llm_model.generate_text(prompt=rag_prompt)

            # Extract text from response
            if isinstance(llm_response, dict) and "results" in llm_response:
                answer = llm_response["results"][0]["generated_text"].strip()
            elif isinstance(llm_response, str):
                answer = llm_response.strip()
            else:
                answer = str(llm_response).strip()

            print("\n" + "-" * 80)
            print("LLM RESPONSE:")
            print("-" * 80)
            print(answer)
            print("-" * 80)

            # Analyze response quality
            print("\n" + "=" * 80)
            print("RESPONSE ANALYSIS:")
            print("=" * 80)

            answer_lower = answer.lower()
            query_lower = query.lower()

            # Check if response contains key terms from query
            query_terms = set(query_lower.split())
            answer_terms = set(answer_lower.split())
            overlap = query_terms & answer_terms

            print(f"✓ Response length: {len(answer)} characters")
            print(f"✓ Word count: {len(answer.split())} words")
            print(f"✓ Query term overlap: {len(overlap)}/{len(query_terms)} terms")

            # Check for COVID-19 specific content
            if "covid" in query_lower:
                has_covid = "covid" in answer_lower or "pandemic" in answer_lower
                print(f"✓ Contains COVID-19 reference: {'YES' if has_covid else 'NO'}")

            # Check if answer says "I don't know" or similar
            uncertain_phrases = ["i don't know", "cannot answer", "not mentioned", "no information"]
            is_uncertain = any(phrase in answer_lower for phrase in uncertain_phrases)
            print(f"✓ Contains uncertainty: {'YES ⚠️' if is_uncertain else 'NO'}")

            # Check if answer cites sources
            has_page_ref = "page" in answer_lower or any(str(chunk["page"]) in answer for chunk in retrieved_chunks[:5])
            print(f"✓ References sources: {'YES' if has_page_ref else 'NO'}")

        except Exception as e:
            print(f"❌ LLM generation failed: {e}")
            import traceback

            traceback.print_exc()

        print("\n")

    # Cleanup
    print("=" * 80)
    print("Disconnecting from Milvus...")
    connections.disconnect("default")
    print("✅ Test complete!")


if __name__ == "__main__":
    test_direct_embeddings()
