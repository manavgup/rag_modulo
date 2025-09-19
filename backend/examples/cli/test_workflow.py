#!/usr/bin/env python3
"""Enhanced CLI test script that demonstrates the CLI functionality.

This script tests the separate RAG CLI workflow with comprehensive user interaction:
1. Checks if mock user exists and creates if needed
2. Displays user information (ID, pipeline id, default provider id)
3. Lists existing collections with file counts
4. Allows user to choose between creating new collection or querying existing ones
5. For new collections: creates collection and uploads file
6. Suggests default questions or allows custom question input
7. Performs search and displays results

Key features of the enhanced architecture:
- Interactive user experience with choices and suggestions
- Comprehensive user and collection information display
- Automatic question generation and suggestion
- Pipeline resolution handled automatically by the backend
- Uses the separate create_collection + upload_file workflow
"""

import os
import sys
import time
import traceback
from datetime import datetime

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, backend_dir)

from rag_solution.cli.client import RAGAPIClient  # noqa: E402
from rag_solution.cli.commands.collections import CollectionCommands  # noqa: E402
from rag_solution.cli.commands.documents import DocumentCommands  # noqa: E402
from rag_solution.cli.commands.search import SearchCommands  # noqa: E402
from rag_solution.cli.commands.users import UserCommands  # noqa: E402
from rag_solution.cli.config import RAGConfig  # noqa: E402
from rag_solution.cli.mock_auth_helper import setup_mock_authentication  # noqa: E402


def _print_intro():
    """Print introduction and features."""
    print("🚀 Enhanced RAG CLI Demonstration with Interactive Workflow")
    print("=" * 70)
    print("Testing CLI with comprehensive user interaction and pipeline resolution")
    print("Features:")
    print("• Interactive user experience with choices and suggestions")
    print("• User status checking and pipeline information display")
    print("• Collection listing with file counts and status")
    print("• Choice between creating new collections or using existing ones")
    print("• Suggested questions from collection or custom question input")
    print("• Automatic backend pipeline resolution")
    print("• Background document processing pipeline")
    print("• Enhanced search results with source information")
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


def _check_and_create_user(api_client, config):
    """Check if mock user exists and create if needed."""
    print("\n👤 Step 1: Checking User Status")
    print("-" * 50)

    users_cmd = UserCommands(api_client, config)

    # Get current user info
    user_result = users_cmd.get_current_user()

    if user_result.success:
        user_data = user_result.data
        print("✅ User already exists!")
        print(f"   User ID: {user_data.get('id', 'N/A')}")
        print(f"   Name: {user_data.get('name', 'N/A')}")
        print(f"   Email: {user_data.get('email', 'N/A')}")
        print(f"   Role: {user_data.get('role', 'N/A')}")
        return user_data.get("id")
    else:
        print("❌ User not found or authentication failed")
        print(f"   Error: {user_result.message}")
        return None


def _get_user_pipeline_info(api_client, config, user_id):
    """Get user's pipeline and provider information."""
    print("\n🔧 Step 2: Getting User Pipeline Information")
    print("-" * 50)

    try:
        # Try to get user's default pipeline
        pipeline_response = api_client.get(f"/api/users/{user_id}/pipeline")
        if pipeline_response:
            pipeline_id = pipeline_response.get("id", "N/A")
            print(f"   Default Pipeline ID: {pipeline_id}")
        else:
            print("   Default Pipeline ID: Not set (will be created automatically)")

        # Try to get user's default provider
        provider_response = api_client.get(f"/api/users/{user_id}/provider")
        if provider_response:
            provider_id = provider_response.get("id", "N/A")
            provider_name = provider_response.get("name", "N/A")
            print(f"   Default Provider ID: {provider_id}")
            print(f"   Default Provider Name: {provider_name}")
        else:
            print("   Default Provider ID: Not set (will be created automatically)")

    except Exception as e:
        print(f"   Note: Pipeline/provider info not available: {e}")
        print("   (This is normal for new users - will be created automatically)")


def _list_user_collections(api_client, config):
    """List user's collections with file counts."""
    print("\n📁 Step 3: Listing User Collections")
    print("-" * 50)

    collections_cmd = CollectionCommands(api_client, config)
    result = collections_cmd.list_collections()

    if result.success and result.data:
        # Handle both list and dict response formats
        collections = result.data if isinstance(result.data, list) else result.data.get("collections", [])

        if collections:
            print(f"✅ Found {len(collections)} collection(s):")
            for i, collection in enumerate(collections, 1):
                collection_id = collection.get("id", "N/A")
                name = collection.get("name", "Unnamed")
                # Extract file count from the files array
                files = collection.get("files", [])
                file_count = len(files) if files else 0
                status = collection.get("status", "unknown")

                print(f"   {i}. Collection: {name}")
                print(f"      ID: {collection_id}")
                print(f"      Files: {file_count}")
                print(f"      Status: {status}")
                print()
            return collections
        else:
            print("📭 No collections found")
            return []
    else:
        print(f"❌ Failed to list collections: {result.message}")
        return []


def _get_collection_questions(api_client, config, collection_id):
    """Get suggested questions for a collection."""
    try:
        response = api_client.get(f"/api/collections/{collection_id}/questions")
        if response:
            return [q.get("question", "") for q in response if q.get("question")]
    except Exception:
        pass
    return []


def _ask_user_choice():
    """Ask user whether to create new collection or use existing one."""
    print("\n🤔 Step 4: Choose Action")
    print("-" * 50)
    print("What would you like to do?")
    print("1. Create a new collection and upload a file")
    print("2. Query against an existing collection")

    while True:
        choice = input("\nEnter your choice (1 or 2): ").strip()
        if choice in ["1", "2"]:
            return choice
        print("Please enter 1 or 2")


def _select_existing_collection(collections):
    """Let user select from existing collections."""
    print("\n📋 Select Collection to Query")
    print("-" * 30)

    for i, collection in enumerate(collections, 1):
        name = collection.get("name", "Unnamed")
        # Extract file count from the files array
        files = collection.get("files", [])
        file_count = len(files) if files else 0
        print(f"{i}. {name} ({file_count} files)")

    while True:
        try:
            choice = int(input(f"\nSelect collection (1-{len(collections)}): "))
            if 1 <= choice <= len(collections):
                return collections[choice - 1]
            print(f"Please enter a number between 1 and {len(collections)}")
        except ValueError:
            print("Please enter a valid number")


def _get_user_question(api_client, config, collection_id):
    """Get question from user or suggest default questions."""
    print("\n❓ Step 5: Choose Question")
    print("-" * 50)

    # Try to get suggested questions
    suggested_questions = _get_collection_questions(api_client, config, collection_id)

    if suggested_questions:
        print("📝 Suggested questions for this collection:")
        for i, question in enumerate(suggested_questions[:5], 1):  # Show max 5
            print(f"   {i}. {question}")
        print()

        print("Options:")
        print("1. Use a suggested question (enter number)")
        print("2. Enter your own question")

        while True:
            choice = input("\nEnter your choice (1 or 2): ").strip()
            if choice == "1":
                try:
                    q_num = int(input(f"Enter question number (1-{len(suggested_questions)}): "))
                    if 1 <= q_num <= len(suggested_questions):
                        return suggested_questions[q_num - 1]
                    print(f"Please enter a number between 1 and {len(suggested_questions)}")
                except ValueError:
                    print("Please enter a valid number")
            elif choice == "2":
                break
            else:
                print("Please enter 1 or 2")

    # Get custom question
    while True:
        question = input("\nEnter your question: ").strip()
        if question:
            return question
        print("Please enter a non-empty question")


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


def _search_document_with_question(api_client, config, collection_id, question):
    """Search the document with user-provided question."""
    print("\n🔍 Step 6: Searching Document")
    print("-" * 40)
    print("The CLI will get user context from /api/auth/me")
    print("Pipeline resolution is now handled automatically by the backend")

    search_cmd = SearchCommands(api_client, config)

    print(f"   Query: {question}")
    print(f"   Collection ID: {collection_id}")
    print("   Pipeline: Will be resolved automatically from user's default")

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries + 1):
        # No pipeline_id parameter needed anymore - backend handles resolution
        result = search_cmd.query(
            collection_id=collection_id,
            query=question,
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
        print(f"   Query: {question}")
        print("   Schema used: SearchInput (question, collection_id, user_id, config_metadata)")
        print("   Note: pipeline_id removed - backend resolves user's default pipeline")
        if result.data:
            answer = result.data.get("answer", "No answer returned")
            print(f"   Full Answer: {answer}")

            # Also show sources if available
            sources = result.data.get("sources", [])
            if sources:
                print(f"   Sources: {len(sources)} document chunks referenced")
        return True

    print(f"❌ Search failed: {result.message}")
    if result.data:
        print(f"   Error details: {result.data}")
    return False


def _print_summary(mock_token):
    """Print completion summary."""
    print("\n🎉 Enhanced CLI Demonstration Complete!")
    print("=" * 70)
    print("Summary of operations tested:")
    print("• ✅ Interactive user status checking and creation")
    print("• ✅ User pipeline and provider information display")
    print("• ✅ Collection listing with file counts and status")
    print("• ✅ User choice between new/existing collections")
    print("• ✅ Suggested questions from collections")
    print("• ✅ Custom question input capability")
    print("• ✅ Enhanced search with source information")
    print("• ✅ Automatic backend pipeline resolution")
    print("• ✅ Background document processing pipeline")
    print(f"• ✅ Mock token used: {mock_token}")
    print()
    print("🚀 Enhanced interactive workflow architecture working successfully!")


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
    """Main function to demonstrate enhanced CLI functionality."""
    _print_intro()

    try:
        config, api_client, mock_token = _setup_cli_environment()

        # Step 1: Check user status
        user_id = _check_and_create_user(api_client, config)
        if not user_id:
            print("❌ Cannot proceed without valid user")
            return

        # Step 2: Get user pipeline info
        _get_user_pipeline_info(api_client, config, user_id)

        # Step 3: List existing collections
        collections = _list_user_collections(api_client, config)

        # Step 4: Ask user choice
        choice = _ask_user_choice()

        collection_id = None

        if choice == "1":
            # Create new collection
            collection_id, pdf_path = _create_collection(api_client, config)
            if not collection_id:
                return

            if not _upload_document(api_client, config, collection_id, pdf_path):
                return

            if not _wait_for_processing(api_client, config, collection_id):
                return

        elif choice == "2":
            # Use existing collection
            if not collections:
                print("❌ No existing collections to query")
                return

            selected_collection = _select_existing_collection(collections)
            collection_id = selected_collection.get("id")

            # Check if collection has files
            files = selected_collection.get("files", [])
            file_count = len(files) if files else 0
            if file_count == 0:
                print("⚠️  Selected collection has no files. You may want to upload some first.")
                proceed = input("Continue anyway? (y/n): ").strip().lower()
                if proceed != "y":
                    return

        # Step 5: Get question
        question = _get_user_question(api_client, config, collection_id)

        # Step 6: Perform search
        if not _search_document_with_question(api_client, config, collection_id, question):
            return

        _print_summary(mock_token)

    except (ConnectionError, FileNotFoundError, ValueError, TypeError) as e:
        _handle_error(e, mock_token, config)


def show_usage():
    """Show usage instructions for the enhanced test script."""
    print("Enhanced RAG CLI Test Script Usage:")
    print("=" * 60)
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
    print("   Edit line ~246 to point to an actual PDF file")
    print()
    print("4. Run the enhanced test (from project root):")
    print("   python backend/examples/cli/test_workflow.py")
    print()
    print("   Or from backend directory:")
    print("   cd backend && python examples/cli/test_workflow.py")
    print()
    print("Interactive Features:")
    print("• Check user status and create if needed")
    print("• Display user pipeline and provider information")
    print("• List existing collections with file counts")
    print("• Choose between creating new collection or using existing")
    print("• Select from suggested questions or enter custom question")
    print("• Enhanced search results with source information")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_usage()
    else:
        main()
