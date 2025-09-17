#!/usr/bin/env python3
"""Simple CLI test script that demonstrates the CLI functionality.

This script tests the separate RAG CLI workflow:
1. Creates an empty collection using the create_collection endpoint
2. Uploads a document to the collection using the upload_file endpoint
3. Performs a search query using the proper SearchInput schema

Uses the separate create_collection + upload_file workflow to test that
the refactored shared processing logic works correctly for both combined
and separate workflows.
"""

import os
import sys
import time
import traceback
from datetime import datetime

# Add the parent directory to sys.path to enable imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rag_solution.cli.client import RAGAPIClient  # noqa: E402
from rag_solution.cli.commands.collections import CollectionCommands  # noqa: E402
from rag_solution.cli.commands.documents import DocumentCommands  # noqa: E402
from rag_solution.cli.commands.search import SearchCommands  # noqa: E402
from rag_solution.cli.config import RAGConfig  # noqa: E402
from rag_solution.cli.mock_auth_helper import setup_mock_authentication  # noqa: E402


def _print_intro():
    """Print introduction and features."""
    print("🚀 RAG CLI Simple Demonstration")
    print("=" * 60)
    print("Testing CLI with separate create_collection + upload_file workflow")
    print("Features:")
    print("• Configurable mock tokens via environment variables")
    print("• Separate create_collection and upload_file endpoints")
    print("• Background document processing pipeline")
    print("• Proper SearchInput schema format")
    print("• Tests refactored shared processing logic")
    print()


def _setup_cli_environment():
    """Set up CLI configuration and authentication."""
    config = RAGConfig(
        api_url="http://localhost:8000",
        profile="test",
        timeout=30,
        output_format="table",
        verbose=True,
        dry_run=False,
    )

    api_client = RAGAPIClient(config)
    print("🔐 Setting up mock authentication...")
    mock_token = setup_mock_authentication(api_client, verbose=True)

    return config, api_client, mock_token


def _create_collection(api_client, config):
    """Create a new collection."""
    print("\n📁 Step 1: Creating Empty Collection")
    print("-" * 50)
    print("Using create_collection endpoint (POST /api/collections)")
    print("This endpoint will:")
    print("• Create an empty collection")
    print("• Set up collection metadata")
    print("• Prepare collection for document uploads")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    collection_name = f"AI_Agents_Demo_{timestamp}"

    pdf_path = "/Users/mg/Downloads/next-frontier-after-ai-agents.pdf"

    if not os.path.exists(pdf_path):
        print(f"❌ PDF file not found: {pdf_path}")
        print(f"   Expected path: {pdf_path}")
        print("   Note: Update the path to point to an actual PDF file for testing")
        return None, None

    collections_cmd = CollectionCommands(api_client, config)
    print(f"📝 Collection name: {collection_name}")

    result = collections_cmd.create_collection(
        name=collection_name, description="Test collection for CLI demonstration", is_private=False
    )

    if result.success:
        collection_id = result.data.get("id")
        print("✅ Empty collection created successfully!")
        print(f"   Collection Name: {collection_name}")
        print(f"   Collection ID: {collection_id}")
        print(f"   Status: {result.data.get('status', 'unknown')}")
        print(f"   Message: {result.message}")
        return collection_id, pdf_path

    print(f"❌ Failed to create collection: {result.message}")
    if result.data:
        print(f"   Error details: {result.data}")
    return None, None


def _upload_document(api_client, config, collection_id, pdf_path):
    """Upload document to collection."""
    print("\n📤 Step 2: Uploading file to collection")
    print("-" * 50)
    print(f"📤 Uploading file: {os.path.basename(pdf_path)}")

    documents_cmd = DocumentCommands(api_client, config)
    result = documents_cmd.upload_document(collection_id=collection_id, file_path=pdf_path)

    if result.success:
        print("✅ File uploaded successfully!")
        print(f"   File: {os.path.basename(pdf_path)}")
        print(f"   Collection ID: {collection_id}")
        print("   Processing: Background document processing should be triggered")
        print(f"   Message: {result.message}")
        return True

    print(f"❌ Failed to upload file: {result.message}")
    if result.data:
        print(f"   Error details: {result.data}")
    return False


def _wait_for_processing(api_client, config, collection_id):
    """Wait for document processing to complete."""
    print("\n⏳ Step 3: Waiting for Document Processing")
    print("-" * 40)
    print("Polling collection status until processing completes...")

    collection_cmd = CollectionCommands(api_client, config)
    max_wait_time = 120  # 2 minutes max
    poll_interval = 3  # Check every 3 seconds
    elapsed_time = 0

    while elapsed_time < max_wait_time:
        status_result = collection_cmd.get_collection_status(collection_id)

        if status_result.success and status_result.data:
            status = status_result.data.get("status", "unknown")
            print(f"   Status check ({elapsed_time}s): {status}")

            if status.lower() == "completed":
                print("✅ Document processing completed!")
                return True
            if status.lower() == "error":
                print("❌ Document processing failed!")
                print(f"   Error: {status_result.data.get('message', 'Unknown error')}")
                return False

        time.sleep(poll_interval)
        elapsed_time += poll_interval

    print(f"⚠️  Timeout waiting for processing (waited {max_wait_time}s)")
    print("   Attempting search anyway...")
    return True


def _search_document(api_client, config, collection_id):
    """Search the document."""
    print("\n🔍 Step 4: Searching Document")
    print("-" * 40)
    print("The CLI will get user context from /api/auth/me")

    search_cmd = SearchCommands(api_client, config)
    query = "What technologies does this paper talk about?"

    print(f"   Query: {query}")
    print(f"   Collection ID: {collection_id}")
    print("   User and Pipeline will be determined automatically")

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries + 1):
        result = search_cmd.query(
            collection_id=collection_id,
            query=query,
            pipeline_id=None,  # Let CLI fetch from user context
            max_chunks=5,
        )

        if result.success:
            break
        if attempt < max_retries and "still processing" in str(result.data).lower():
            print(
                f"   Attempt {attempt + 1}/{max_retries + 1}: Collection still processing, "
                f"retrying in {retry_delay}s..."
            )
            time.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff
        else:
            break

    if result.success:
        print("✅ Search completed successfully!")
        print(f"   Query: {query}")
        print("   Schema used: SearchInput (question, collection_id, user_id, pipeline_id)")
        if result.data:
            answer = result.data.get("answer", "No answer returned")
            print(f"   Full Answer: {answer}")
        return True

    print(f"❌ Search failed: {result.message}")
    if result.data:
        print(f"   Error details: {result.data}")
    return False


def _print_summary(mock_token):
    """Print completion summary."""
    print("\n🎉 CLI Demonstration Complete!")
    print("=" * 60)
    print("Summary of operations tested:")
    print("• ✅ Configurable mock token authentication")
    print("• ✅ Separate create_collection + upload_file workflow")
    print("• ✅ Background document processing pipeline")
    print("• ✅ Simplified search without complex pipeline setup")
    print("• ✅ CLI search command handling")
    print("• ✅ Refactored shared processing logic")
    print(f"• ✅ Mock token used: {mock_token}")
    print()
    print("🚀 Separate workflow with simplified CLI search tested successfully!")


def _handle_error(e, mock_token, config):
    """Handle and display error information."""
    print(f"❌ Error during demonstration: {e}")
    print("\nDebugging information:")
    print(f"• Mock token: {mock_token}")
    print(f"• API URL: {config.api_url}")
    print(f"• Testing environment variable: {os.getenv('TESTING', 'not set')}")
    print("\nFull traceback:")
    traceback.print_exc()
    print("\nTroubleshooting:")
    print("1. Ensure the FastAPI server is running on http://localhost:8000")
    print("2. Check that TESTING=true or SKIP_AUTH=true is set")
    print("3. Verify the PDF file path exists")
    print("4. Check server logs for authentication middleware messages")


def main():
    """Main function to demonstrate CLI functionality."""
    _print_intro()

    try:
        config, api_client, mock_token = _setup_cli_environment()

        collection_id, pdf_path = _create_collection(api_client, config)
        if not collection_id:
            return

        if not _upload_document(api_client, config, collection_id, pdf_path):
            return

        if not _wait_for_processing(api_client, config, collection_id):
            return

        if not _search_document(api_client, config, collection_id):
            return

        _print_summary(mock_token)

    except (ConnectionError, FileNotFoundError, ValueError, TypeError) as e:
        _handle_error(e, mock_token, config)


def show_usage():
    """Show usage instructions for the test script."""
    print("RAG CLI Test Script Usage:")
    print("=" * 50)
    print()
    print("Prerequisites:")
    print("1. Start the RAG FastAPI server:")
    print("   cd backend && poetry run uvicorn main:app --host 0.0.0.0 --port 8000")
    print()
    print("2. Set environment variables (optional):")
    print("   export MOCK_TOKEN='my-custom-token'  # Default: dev-0000-0000-0000")
    print("   export TESTING=true                   # Enable auth bypass")
    print()
    print("3. Update PDF file path in the script:")
    print("   Edit line ~84 to point to an actual PDF file")
    print()
    print("4. Run the test:")
    print("   python backend/test_cli_simple.py")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_usage()
    else:
        main()
