"""Script to check document content in the vector database."""
import sys

# Add backend to path
sys.path.insert(0, "/Users/mg/mg-work/manav/work/ai-experiments/rag_modulo/backend")

from core.config import get_settings
from vectordbs.factory import VectorStoreFactory

settings = get_settings()

# Create vector store instance
factory = VectorStoreFactory(settings)
vector_store = factory.get_datastore(settings.vector_db)

# Try to retrieve some documents with a simple query
print("Searching for IBM-related documents...\n")

results = vector_store.retrieve_documents(
    query="IBM", collection_name="User_Uploaded_Files_20250918_131815", number_of_results=5
)

print(f"Found {len(results)} results\n")

for i, result in enumerate(results, 1):
    print(f"=== Result {i} ===")
    print(f"Score: {result.score}")
    print(f"Chunk ID: {result.chunk.chunk_id if result.chunk else 'N/A'}")
    print("\nContent:")
    if result.chunk and result.chunk.text:
        # Show first 500 chars to check for contamination
        content = result.chunk.text
        print(content[:1000])

        # Check for contamination
        contamination_indicators = ["<instruction>", "Generate", "question-answer pair", "diverse question"]

        found_indicators = [ind for ind in contamination_indicators if ind.lower() in content.lower()]
        if found_indicators:
            print(f"\n⚠️  CONTAMINATION FOUND: {', '.join(found_indicators)}")
        else:
            print("\n✓ Content appears clean")
    print("\n" + "=" * 80 + "\n")
