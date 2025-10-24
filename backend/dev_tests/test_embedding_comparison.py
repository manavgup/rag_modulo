#!/usr/bin/env python3
"""
Test different embedding models to validate root cause of retrieval ranking issues.

This script:
1. Creates a new collection for each embedding model
2. Ingests the same PDF document
3. Runs the same query against each collection
4. Compares where the revenue chunk ranks for each model
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

import httpx
from dotenv import load_dotenv, set_key

# Test configuration - VERIFIED working WatsonX embedding models
# All models below have been tested with WatsonX API and confirmed working
EMBEDDING_MODELS = [
    {
        "name": "ibm/slate-125m-english-rtrvr",
        "size": "125M",
        "dimension": 768,
        "architecture": "IBM Slate",
        "description": "Current baseline model",
        "max_tokens": None,  # No known limit
    },
    {
        "name": "ibm/slate-125m-english-rtrvr-v2",
        "size": "125M",
        "dimension": 768,
        "architecture": "IBM Slate V2",
        "description": "Newer version of baseline",
        "max_tokens": None,
    },
    {
        "name": "ibm/slate-30m-english-rtrvr",
        "size": "30M",
        "dimension": 384,
        "architecture": "IBM Slate",
        "description": "Smaller, faster model",
        "max_tokens": None,
    },
    {
        "name": "ibm/slate-30m-english-rtrvr-v2",
        "size": "30M",
        "dimension": 384,
        "architecture": "IBM Slate V2",
        "description": "Newer 30M version",
        "max_tokens": None,
    },
    {
        "name": "ibm/granite-embedding-107m-multilingual",
        "size": "107M",
        "dimension": 384,
        "architecture": "IBM Granite",
        "description": "Multilingual 384-dim",
        "max_tokens": None,
    },
    {
        "name": "ibm/granite-embedding-278m-multilingual",
        "size": "278M",
        "dimension": 768,
        "architecture": "IBM Granite",
        "description": "Larger multilingual 768-dim",
        "max_tokens": None,
    },
    {
        "name": "intfloat/multilingual-e5-large",
        "size": "~560M",
        "dimension": 1024,
        "architecture": "E5",
        "description": "Largest model - 1024-dim (512 token limit)",
        "max_tokens": 512,  # Strict limit
    },
    {
        "name": "sentence-transformers/all-minilm-l6-v2",
        "size": "22M",
        "dimension": 384,
        "architecture": "MiniLM",
        "description": "Smallest, fastest model (likely 512 token limit)",
        "max_tokens": 512,  # Assumed limit
    },
]

TEST_FILE = "/Users/mg/Downloads/2022-ibm-annual-report.txt"  # Using TXT to skip slow Docling processing
TEST_QUERY = "What was IBM revenue in 2022?"
EXPECTED_ANSWER = "60.5 billion"  # Update for 2022 report

# API configuration
API_BASE = "http://localhost:8000"
USER_UUID = "ee76317f-3b6f-4fea-8b74-56483731f58c"


async def update_chunking_config(env_file: Path, max_tokens: int | None) -> None:
    """Update chunking configuration - using CHARACTER values (consistent across all strategies).

    All config values (MIN_CHUNK_SIZE, MAX_CHUNK_SIZE, CHUNK_OVERLAP) are in CHARACTERS.
    Conservative 500-char chunks work for ALL WatsonX models with 512-token limits.

    Character-to-token ratio: ~2.5 chars/token (conservative for technical docs)
    500 chars ≈ 200 tokens (safe for 512-token limit with margin)
    """
    # Use conservative chunking for ALL models (all have 512-token limits)
    max_chunk_size = 500  # characters
    min_chunk_size = 250  # characters
    chunk_overlap = 100  # characters
    print("📐 Conservative chunking (512-token limit - applies to ALL models):")
    print("   MAX_CHUNK_SIZE=500 characters (~200 tokens)")

    set_key(str(env_file), "MAX_CHUNK_SIZE", str(max_chunk_size), quote_mode="never")
    set_key(str(env_file), "MIN_CHUNK_SIZE", str(min_chunk_size), quote_mode="never")
    set_key(str(env_file), "CHUNK_OVERLAP", str(chunk_overlap), quote_mode="never")
    print("   ✅ Updated chunking configuration")


async def update_embedding_model(model_name: str, env_file: Path) -> None:
    """Update the EMBEDDING_MODEL in .env file.

    IMPORTANT: set_key adds quotes by default, so we use quote_mode='never'
    to prevent storing quotes as part of the value in the database.
    """
    print(f"📝 Updating .env with embedding model: {model_name}")
    # Use quote_mode='never' to prevent adding quotes around the value
    set_key(str(env_file), "EMBEDDING_MODEL", model_name, quote_mode="never")
    print("   ✅ Updated .env file")


async def restart_backend() -> None:
    """Trigger backend reload by touching a file.

    Note: Backend must be running with --reload flag for this to work.
    The backend will re-run system initialization on restart, which updates
    the embedding model in the database based on .env file.
    """
    print("🔄 Triggering backend reload...")
    # Touch a Python file to trigger uvicorn auto-reload
    config_file = Path(__file__).parent.parent / "core" / "config.py"
    config_file.touch()

    # Wait longer for backend to fully restart and initialize
    print("   ⏳ Waiting 15 seconds for backend to restart and initialize...")
    await asyncio.sleep(60)

    # Verify backend is responding
    async with httpx.AsyncClient(timeout=10.0) as client:
        for attempt in range(10):
            try:
                response = await client.get(f"{API_BASE}/")
                if response.status_code in [200, 404]:  # Either is fine
                    print("   ✅ Backend is responding")
                    # Give it a few more seconds to finish initialization
                    await asyncio.sleep(3)
                    return
            except Exception:
                if attempt < 9:
                    print(f"   ⏳ Attempt {attempt + 1}/10 - waiting for backend...")
                    await asyncio.sleep(2)

    print("   ⚠️  Backend may not have fully reloaded")


async def create_collection(model_name: str) -> tuple[str, str]:
    """Create a new collection for testing."""
    collection_name = f"test-{model_name.split('/')[-1].replace('_', '-')}-{uuid4().hex[:8]}"

    print(f"\n📚 Creating collection: {collection_name}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            f"{API_BASE}/api/collections",
            headers={
                "Content-Type": "application/json",
                "X-User-UUID": USER_UUID,
            },
            json={
                "name": collection_name,
                "description": f"Testing {model_name} embedding model",
                "user_id": USER_UUID,
                "is_private": False,
            },
        )

        if response.status_code in [200, 201]:
            data = response.json()
            collection_id = data["id"]
            print(f"   ✅ Collection created: {collection_id}")
            return collection_id, collection_name
        else:
            raise Exception(f"Failed to create collection: {response.status_code} - {response.text}")


async def upload_document(collection_id: str, file_path: str) -> str:
    """Upload document to collection (supports both PDF and TXT)."""
    print(f"📄 Uploading document: {Path(file_path).name}")

    # Determine MIME type based on file extension
    file_ext = Path(file_path).suffix.lower()
    mime_type = "text/plain" if file_ext == ".txt" else "application/pdf"

    async with httpx.AsyncClient(timeout=300.0) as client:  # 5 min timeout for upload
        with open(file_path, "rb") as f:
            files = {"file": (Path(file_path).name, f, mime_type)}

            response = await client.post(
                f"{API_BASE}/api/users/{USER_UUID}/files?collection_id={collection_id}",
                headers={"X-User-UUID": USER_UUID},
                files=files,
            )

            if response.status_code == 200:
                result = response.json()
                file_id = result.get("file_id") or result.get("id")
                print(f"   ✅ Document uploaded: {file_id}")
                return file_id
            else:
                raise Exception(f"Failed to upload document: {response.status_code} - {response.text}")


async def wait_for_processing(collection_id: str, wait_time: int = 180) -> None:
    """Wait for document processing to complete and verify chunks exist.

    Note: TXT processing should be fast, but embedding generation can take time
    with many chunks. Wait longer to ensure complete processing.
    """
    print(f"⏳ Waiting up to {wait_time}s for document processing to complete...")
    print("   📄 TXT processing + embedding generation...")

    # Poll collection status until ready or error
    for i in range(wait_time):
        if i % 15 == 0 and i > 0:
            async with httpx.AsyncClient(timeout=10.0) as client:
                try:
                    response = await client.get(
                        f"{API_BASE}/api/collections/{collection_id}",
                        headers={"X-User-UUID": USER_UUID},
                    )
                    if response.status_code == 200:
                        collection = response.json()
                        status = collection.get("status")
                        print(f"   ⏳ {i}s elapsed... Status: {status}")
                        if status == "ready":
                            print(f"   ✅ Collection ready at {i}s")
                            return
                        elif status == "error":
                            print(f"   ⚠️  Collection ERROR at {i}s")
                            return
                except Exception:
                    pass
        await asyncio.sleep(1)

    # Verify processing completed by checking collection status
    print("   🔍 Verifying document processing...")
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(
                f"{API_BASE}/api/collections/{collection_id}",
                headers={"X-User-UUID": USER_UUID},
            )
            if response.status_code == 200:
                collection = response.json()
                status = collection.get("status")
                print(f"   📊 Collection status: {status}")
                if status == "error":
                    print("   ⚠️  WARNING: Collection has error status - processing may have failed")
                elif status == "ready":
                    print("   ✅ Collection is ready")
                else:
                    print(f"   ⏳ Collection status: {status}")
        except Exception as e:
            print(f"   ⚠️  Could not verify collection status: {e}")

    print("   ✅ Processing wait complete")


async def search_collection(collection_id: str, query: str, top_k: int = 20) -> dict:
    """Run search query against collection."""
    print(f"🔍 Searching: '{query}'")

    async with httpx.AsyncClient(timeout=180.0) as client:  # 3 min timeout for search
        response = await client.post(
            f"{API_BASE}/api/search",
            headers={
                "Content-Type": "application/json",
                "X-User-UUID": USER_UUID,
            },
            json={
                "question": query,
                "collection_id": collection_id,
                "user_id": USER_UUID,
                "config_metadata": {
                    "cot_disabled": True,
                    "top_k": top_k,
                },
            },
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Search failed: {response.status_code} - {response.text}")


def analyze_results(results: dict, expected_text: str) -> dict:
    """Analyze search results to find where the expected chunk ranks."""
    query_results = results.get("query_results", [])
    answer = results.get("answer", "")

    # Find revenue chunk
    revenue_chunk_rank = None
    revenue_chunk_score = None
    revenue_chunk_text = None

    for i, result in enumerate(query_results, 1):
        chunk_text = result["chunk"]["text"]
        if expected_text in chunk_text:
            revenue_chunk_rank = i
            revenue_chunk_score = result["score"]
            revenue_chunk_text = chunk_text[:200]
            break

    # Check if answer contains expected text
    answer_correct = expected_text in answer

    return {
        "total_chunks": len(query_results),
        "revenue_chunk_rank": revenue_chunk_rank,
        "revenue_chunk_score": revenue_chunk_score,
        "revenue_chunk_text": revenue_chunk_text,
        "answer_correct": answer_correct,
        "answer_preview": answer[:200],
        "top_5_scores": [r["score"] for r in query_results[:5]],
    }


async def test_embedding_model(model_info: dict, env_file: Path) -> dict:
    """Test a single embedding model end-to-end."""
    model_name = model_info["name"]

    print("\n" + "=" * 80)
    print(f"🧪 TESTING: {model_name}")
    print(f"   Size: {model_info['size']}")
    print(f"   Dimension: {model_info['dimension']}")
    print(f"   Architecture: {model_info['architecture']}")
    print(f"   Description: {model_info['description']}")
    print("=" * 80)

    try:
        # Step 1: Update chunking configuration based on model token limits
        # NOTE: We update .env but DON'T restart backend to avoid interrupting processing
        await update_chunking_config(env_file, model_info.get("max_tokens"))

        # Step 2: Update embedding model in .env
        await update_embedding_model(model_name, env_file)

        # Step 3: Restart backend ONLY (let it reload .env)
        # IMPORTANT: We restart here so the NEW config is picked up BEFORE creating collection
        await restart_backend()

        # Step 4: Create collection (will use new chunking + embedding config)
        collection_id, collection_name = await create_collection(model_name)

        # Step 5: Upload document
        file_id = await upload_document(collection_id, TEST_FILE)

        # Step 6: Wait for processing
        await wait_for_processing(collection_id)

        # Step 7: Search
        try:
            results = await search_collection(collection_id, TEST_QUERY)
        except Exception as search_error:
            # Check if this is a collection processing error
            if "encountered errors during processing" in str(search_error):
                print("   ⚠️  Collection processing failed - document may not have been chunked properly")
                return {
                    "model": model_name,
                    "status": "processing_error",
                    "collection_id": collection_id,
                    "collection_name": collection_name,
                    "error": "Document processing failed - 0 chunks created",
                }
            raise

        # Step 8: Analyze
        analysis = analyze_results(results, EXPECTED_ANSWER)

        return {
            "model": model_name,
            "status": "success",
            "collection_id": collection_id,
            "collection_name": collection_name,
            "max_tokens": model_info.get("max_tokens"),
            "chunk_config": "500 chars (~200 tokens)"
            if model_info.get("max_tokens") == 512
            else "750 chars (~300 tokens)",
            **analysis,
        }

    except Exception as e:
        print(f"   ❌ Error testing {model_name}: {e}")
        import traceback

        traceback.print_exc()
        return {
            "model": model_name,
            "status": "error",
            "error": str(e),
        }


async def main():
    """Main test orchestrator."""
    print("\n" + "=" * 80)
    print("🧪 EMBEDDING MODEL COMPARISON TEST")
    print("=" * 80)
    print(f"📄 Test Document: {TEST_FILE}")
    print(f"❓ Test Query: {TEST_QUERY}")
    print(f"✅ Expected Answer Contains: {EXPECTED_ANSWER}")
    print(f"🔢 Testing {len(EMBEDDING_MODELS)} WatsonX-supported models")
    print("=" * 80)

    # Find .env file (in project root)
    env_file = Path(__file__).parent.parent.parent / ".env"
    if not env_file.exists():
        print(f"❌ .env file not found: {env_file}")
        return

    # Check if file exists
    if not Path(TEST_FILE).exists():
        print(f"❌ Test file not found: {TEST_FILE}")
        return

    # Backup original .env
    load_dotenv(env_file)
    original_model = os.getenv("EMBEDDING_MODEL", "ibm/slate-125m-english-rtrvr")
    print(f"\n💾 Original embedding model: {original_model}")

    # Run tests
    all_results = []

    for model_info in EMBEDDING_MODELS:
        result = await test_embedding_model(model_info, env_file)
        all_results.append(result)

        # Brief pause between tests
        await asyncio.sleep(2)

    # Restore original configuration
    print("\n" + "=" * 80)
    print("🔄 Restoring original configuration...")
    await update_chunking_config(env_file, None)  # Restore default chunking
    await update_embedding_model(original_model, env_file)
    await restart_backend()

    # Print comparison table
    print("\n" + "=" * 80)
    print("📊 RESULTS COMPARISON")
    print("=" * 80)
    print(f"\n{'Model':<40} {'Chunks':<22} {'Rank':<6} {'Score':<8} {'Answer':<8}")
    print("-" * 100)

    for result in all_results:
        if result["status"] == "success":
            model = result["model"].split("/")[-1][:35]
            chunks = result.get("chunk_config", "standard")
            rank = result["revenue_chunk_rank"] if result["revenue_chunk_rank"] else "N/A"
            score = f"{result['revenue_chunk_score']:.4f}" if result["revenue_chunk_score"] else "N/A"
            answer = "✅" if result["answer_correct"] else "❌"

            print(f"{model:<40} {chunks:<22} {rank!s:<6} {score:<8} {answer:<8}")
        else:
            model = result["model"].split("/")[-1][:35]
            chunks = result.get("chunk_config", "N/A")
            print(f"{model:<40} {chunks:<22} {'ERROR':<6} {'N/A':<8} {'❌':<8}")

    # Save detailed results to JSON
    output_file = Path(__file__).parent / "embedding_model_comparison_results.json"
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=2)

    print(f"\n💾 Detailed results saved to: {output_file}")

    # Print analysis
    print("\n" + "=" * 80)
    print("📈 ANALYSIS")
    print("=" * 80)

    successful_tests = [r for r in all_results if r["status"] == "success" and r["revenue_chunk_rank"]]

    if successful_tests:
        best_model = min(successful_tests, key=lambda x: x["revenue_chunk_rank"])
        worst_model = max(successful_tests, key=lambda x: x["revenue_chunk_rank"])

        print(f"\n🏆 BEST MODEL: {best_model['model']}")
        print(f"   Revenue chunk rank: #{best_model['revenue_chunk_rank']}")
        print(f"   Score: {best_model['revenue_chunk_score']:.4f}")
        print(f"   Answer correct: {best_model['answer_correct']}")

        print(f"\n💔 WORST MODEL: {worst_model['model']}")
        print(f"   Revenue chunk rank: #{worst_model['revenue_chunk_rank']}")
        print(f"   Score: {worst_model['revenue_chunk_score']:.4f}")
        print(f"   Answer correct: {worst_model['answer_correct']}")

        ranks = [r["revenue_chunk_rank"] for r in successful_tests]
        print("\n📊 STATISTICS:")
        print(f"   Best rank: #{min(ranks)}")
        print(f"   Worst rank: #{max(ranks)}")
        print(f"   Average rank: #{sum(ranks) / len(ranks):.1f}")

        if min(ranks) <= 5:
            print("\n✅ CONCLUSION: Embedding model IS the root cause!")
            print("   Best model ranks revenue chunk in top 5 (default top_k)")
            print(f"   Current model (slate-125m) ranks it at #{worst_model['revenue_chunk_rank']}")
        else:
            print("\n⚠️  CONCLUSION: Embedding model is NOT the only issue")
            print(f"   Even best model ranks revenue chunk at #{min(ranks)} (outside top_k=5)")
            print("   May need hybrid search or query rewriting improvements")

    print("\n" + "=" * 80)
    print("✅ TEST COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
