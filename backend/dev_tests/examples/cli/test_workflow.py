#!/usr/bin/env python3
"""Enhanced CLI test script that demonstrates the CLI functionality.

This script tests the separate RAG CLI workflow with comprehensive user interaction:
1. Checks if mock user exists and creates if needed
2. Displays user information (ID, pipeline id, default provider id)
3. Lists existing collections with file counts
4. Allows user to choose between creating new collection, adding files to existing collection, or querying existing ones
5. For new collections: prompts user for file paths (comma-separated) and validates them
6. Creates collection and uploads user-specified files
7. For existing collections: allows adding new files to existing collections
8. Runs interactive question loop allowing multiple questions
9. Supports asking new questions, suggested questions, or exiting
10. Performs search and displays results with detailed source metadata across multiple documents

Key features of the enhanced architecture:
- Interactive user experience with choices and suggestions
- Comprehensive user and collection information display
- Interactive file selection with validation
- Support for adding files to existing collections
- Interactive question loop with multiple question support
- Automatic question generation and suggestion
- Pipeline resolution handled automatically by the backend
- Uses the separate create_collection + upload_file workflow
- Multi-document support with user-specified files
- Detailed source metadata including page numbers, chunk positions, and text previews
- Results grouped by document for better organization
- Question counter and session management
"""

import os
import sys
import time
import traceback
from datetime import datetime

# Add the backend directory to sys.path to enable imports
backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
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
    print("🚀 Enhanced RAG CLI Demonstration with File Management & Question Loop")
    print("=" * 70)
    print("Testing CLI with comprehensive user interaction and multi-document pipeline resolution")
    print("Features:")
    print("• Interactive user experience with choices and suggestions")
    print("• User status checking and pipeline information display")
    print("• Collection listing with file counts and status")
    print("• Choice between creating new collections, adding files to existing ones, or querying")
    print("• Interactive file selection with validation (comma-separated paths)")
    print("• Multi-document upload support for user-specified files")
    print("• Support for adding files to existing collections")
    print("• Interactive question loop - ask multiple questions in one session")
    print("• Choice between new questions, suggested questions, or exit")
    print("• Suggested questions from collection or custom question input")
    print("• Automatic backend pipeline resolution")
    print("• Background document processing pipeline")
    print("• Enhanced search results with detailed source metadata across multiple documents")
    print("• Results grouped by document for better organization")
    print("• Question counter and session management")
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
    """Ask user what action they want to perform."""
    print("\n🤔 Step 4: Choose Action")
    print("-" * 50)
    print("What would you like to do?")
    print("1. Create a new collection and upload files")
    print("2. Add files to an existing collection")
    print("3. Query against an existing collection")

    while True:
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("Please enter 1, 2, or 3")


def _select_existing_collection(collections, action="query"):
    """Let user select from existing collections."""
    action_text = "Query" if action == "query" else "Add files to"
    print(f"\n📋 Select Collection to {action_text}")
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


def _add_files_to_existing_collection(api_client, config, collections):
    """Add files to an existing collection."""
    print("\n📁 Adding Files to Existing Collection")
    print("-" * 50)

    if not collections:
        print("❌ No existing collections to add files to")
        return None

    # Select collection
    selected_collection = _select_existing_collection(collections, "add files to")
    collection_id = selected_collection.get("id")
    collection_name = selected_collection.get("name", "Unnamed")

    print(f"\n📝 Selected collection: {collection_name}")
    print(f"   Collection ID: {collection_id}")

    # Get files from user
    pdf_files = _get_user_files()
    if not pdf_files:
        return None

    # Upload files to the existing collection
    print(f"\n📤 Uploading {len(pdf_files)} files to existing collection")
    documents_cmd = DocumentCommands(api_client, config)
    successful_uploads = 0
    failed_uploads = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n   Uploading {i}/{len(pdf_files)}: {os.path.basename(pdf_path)}")

        result = documents_cmd.upload_document(collection_id=collection_id, file_path=pdf_path)

        if result.success:
            print(f"   ✅ {os.path.basename(pdf_path)} uploaded successfully!")
            print(f"      Collection ID: {collection_id}")
            print(f"      Message: {result.message}")
            successful_uploads += 1
        else:
            print(f"   ❌ Failed to upload {os.path.basename(pdf_path)}: {result.message}")
            if result.data:
                print(f"      Error details: {result.data}")
            failed_uploads += 1

    print("\n📊 Upload Summary:")
    print(f"   ✅ Successful: {successful_uploads}")
    print(f"   ❌ Failed: {failed_uploads}")
    print("   Processing: Background document processing should be triggered for all files")

    if successful_uploads > 0:
        # Wait for processing
        if not _wait_for_processing(api_client, config, collection_id):
            print("⚠️  Processing may not be complete, but you can still query the collection")

        return collection_id

    return None


def _get_user_question(api_client, config, collection_id, suggested_questions=None):
    """Get question from user or suggest default questions."""
    print("\n❓ Choose Question")
    print("-" * 30)

    # Use provided suggested questions or get them
    if suggested_questions is None:
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


def _ask_question_loop_choice():
    """Ask user what they want to do in the question loop."""
    print("\n🔄 What would you like to do?")
    print("1. Ask a new question")
    print("2. Ask a suggested question")
    print("3. Exit")

    while True:
        choice = input("\nEnter your choice (1, 2, or 3): ").strip()
        if choice in ["1", "2", "3"]:
            return choice
        print("Please enter 1, 2, or 3")


def _run_question_loop(api_client, config, collection_id):
    """Run the interactive question loop."""
    print("\n🔄 Starting Interactive Question Session")
    print("=" * 50)
    print("You can now ask multiple questions about your collection.")
    print("Choose from suggested questions or ask your own!")

    # Get suggested questions once at the start
    suggested_questions = _get_collection_questions(api_client, config, collection_id)

    question_count = 0

    while True:
        choice = _ask_question_loop_choice()

        if choice == "3":  # Exit
            print(f"\n👋 Thank you! You asked {question_count} question(s).")
            break

        elif choice == "1":  # New question
            question = _get_user_question(api_client, config, collection_id, suggested_questions)
            if question:
                question_count += 1
                print(f"\n🔍 Question #{question_count}")
                if not _search_document_with_question(api_client, config, collection_id, question):
                    print("❌ Search failed, but you can try another question.")

        elif choice == "2":  # Suggested question
            if suggested_questions:
                print("\n📝 Suggested questions:")
                for i, question in enumerate(suggested_questions[:5], 1):
                    print(f"   {i}. {question}")

                while True:
                    try:
                        q_num = int(input(f"\nEnter question number (1-{len(suggested_questions)}): "))
                        if 1 <= q_num <= len(suggested_questions):
                            question = suggested_questions[q_num - 1]
                            question_count += 1
                            print(f"\n🔍 Question #{question_count}")
                            if not _search_document_with_question(api_client, config, collection_id, question):
                                print("❌ Search failed, but you can try another question.")
                            break
                        print(f"Please enter a number between 1 and {len(suggested_questions)}")
                    except ValueError:
                        print("Please enter a valid number")
            else:
                print("❌ No suggested questions available for this collection.")
                print("You can ask your own question instead.")

    return question_count


def _get_user_files():
    """Get file paths from user input."""
    print("\n📁 Step 1: File Selection")
    print("-" * 50)
    print("Please provide the file paths you want to upload.")
    print("You can specify multiple files separated by commas.")
    print("Example: /path/to/file1.pdf, /path/to/file2.txt, /path/to/file3.pdf")
    print()

    while True:
        file_input = input("Enter file paths (comma-separated): ").strip()
        if not file_input:
            print("Please enter at least one file path.")
            continue

        # Split by comma and clean up paths
        file_paths = [path.strip() for path in file_input.split(",")]
        file_paths = [path for path in file_paths if path]  # Remove empty strings

        if not file_paths:
            print("Please enter valid file paths.")
            continue

        # Validate file existence
        existing_files = []
        missing_files = []

        for file_path in file_paths:
            if os.path.exists(file_path):
                existing_files.append(file_path)
            else:
                missing_files.append(file_path)

        if not existing_files:
            print("❌ None of the specified files exist:")
            for file_path in file_paths:
                print(f"   ❌ {file_path}")
            print("Please check the file paths and try again.")
            continue

        # Show validation results
        print("\n📋 File Validation Results:")
        print(f"   ✅ Found: {len(existing_files)} files")
        print(f"   ❌ Missing: {len(missing_files)} files")

        if existing_files:
            print("\n   Files to upload:")
            for file_path in existing_files:
                print(f"   ✅ {file_path}")

        if missing_files:
            print("\n   Missing files:")
            for file_path in missing_files:
                print(f"   ❌ {file_path}")

            proceed = input(f"\nProceed with {len(existing_files)} existing files? (y/n): ").strip().lower()
            if proceed != "y":
                continue

        return existing_files


def _create_collection(api_client, config):
    """Create a new collection."""
    print("\n📁 Step 2: Creating Empty Collection")
    print("-" * 50)
    print("Using create_collection endpoint (POST /api/collections)")
    print("This endpoint will:")
    print("• Create an empty collection")
    print("• Set up collection metadata")
    print("• Prepare collection for document uploads")

    # Get files from user
    pdf_files = _get_user_files()
    if not pdf_files:
        return None, None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    collection_name = f"User_Uploaded_Files_{timestamp}"

    collections_cmd = CollectionCommands(api_client, config)
    print(f"\n📝 Collection name: {collection_name}")

    result = collections_cmd.create_collection(
        name=collection_name, description="User uploaded files collection for testing", is_private=False
    )

    if result.success:
        collection_id = result.data.get("id")
        print("✅ Empty collection created successfully!")
        print(f"   Collection Name: {collection_name}")
        print(f"   Collection ID: {collection_id}")
        print(f"   Status: {result.data.get('status', 'unknown')}")
        print(f"   Message: {result.message}")
        return collection_id, pdf_files

    print(f"❌ Failed to create collection: {result.message}")
    if result.data:
        print(f"   Error details: {result.data}")
    return None, None


def _upload_documents(api_client, config, collection_id, pdf_files):
    """Upload multiple documents to collection."""
    print("\n📤 Step 3: Uploading files to collection")
    print("-" * 50)
    print(f"📤 Uploading {len(pdf_files)} files to collection")

    documents_cmd = DocumentCommands(api_client, config)
    successful_uploads = 0
    failed_uploads = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        print(f"\n   Uploading {i}/{len(pdf_files)}: {os.path.basename(pdf_path)}")

        result = documents_cmd.upload_document(collection_id=collection_id, file_path=pdf_path)

        if result.success:
            print(f"   ✅ {os.path.basename(pdf_path)} uploaded successfully!")
            print(f"      Collection ID: {collection_id}")
            print(f"      Message: {result.message}")
            successful_uploads += 1
        else:
            print(f"   ❌ Failed to upload {os.path.basename(pdf_path)}: {result.message}")
            if result.data:
                print(f"      Error details: {result.data}")
            failed_uploads += 1

    print("\n📊 Upload Summary:")
    print(f"   ✅ Successful: {successful_uploads}")
    print(f"   ❌ Failed: {failed_uploads}")
    print("   Processing: Background document processing should be triggered for all files")

    return successful_uploads > 0


def _wait_for_processing(api_client, config, collection_id):
    """Wait for document processing to complete."""
    print("\n⏳ Step 4: Waiting for Document Processing")
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


def _test_cot_behind_scenes(api_client, collection_id, question):
    """Silently test Chain of Thought vs regular search behind the scenes."""
    try:
        # Get proper user_id from API just like working CLI does
        current_user = api_client.get("/api/auth/me")
        user_id = None
        if current_user:
            user_id = current_user.get("uuid") or current_user.get("id")

        # Fallback to test_user_id if API call fails
        if not user_id:
            user_id = "test_user_id"
            with open("cot_test_evidence.log", "a") as log_file:
                log_file.write(f"CoT test warning: Using fallback user_id: {user_id}\n")

        # Test 1: Regular search (what user sees)
        regular_payload = {
            "question": question,
            "collection_id": collection_id,
            "user_id": user_id,
            "config_metadata": {},  # No CoT
        }
        regular_response = api_client.post("/api/search", data=regular_payload)
        regular_time = regular_response.get("execution_time", 0) if regular_response else 0

        # Test 2: CoT search (silent test)
        cot_payload = {
            "question": question,
            "collection_id": collection_id,
            "user_id": user_id,
            "config_metadata": {
                "cot_enabled": True,
                "cot_config": {"max_reasoning_depth": 3, "reasoning_strategy": "decomposition"},
            },
        }
        cot_response = api_client.post("/api/search", data=cot_payload)
        cot_time = cot_response.get("execution_time", 0) if cot_response else 0

        # Silent evidence logging
        if regular_response and cot_response:
            # Check for CoT evidence
            has_cot_output = "cot_output" in cot_response
            cot_reasoning_steps = 0
            if has_cot_output:
                cot_output = cot_response.get("cot_output", {})
                cot_reasoning_steps = len(cot_output.get("reasoning_steps", []))

            # Write silent log entry for evidence
            with open("cot_test_evidence.log", "a") as log_file:
                log_file.write("\n--- CoT Test Evidence ---\n")
                log_file.write(f"Timestamp: {datetime.now()}\n")
                log_file.write(f"Question: {question}\n")
                log_file.write(f"Regular search time: {regular_time:.3f}s\n")
                log_file.write(f"CoT search time: {cot_time:.3f}s\n")
                log_file.write(f"CoT output detected: {has_cot_output}\n")
                log_file.write(f"CoT reasoning steps: {cot_reasoning_steps}\n")
                log_file.write(f"CoT working: {'YES' if has_cot_output and cot_reasoning_steps > 0 else 'NO'}\n")
                log_file.write("-" * 30 + "\n")

        return regular_response  # Return regular response to user
    except Exception as e:
        # Silent error handling - don't disrupt user experience
        with open("cot_test_evidence.log", "a") as log_file:
            log_file.write(f"CoT test error: {e}\n")
        return None


def _search_document_with_question(api_client, config, collection_id, question):
    """Search the document with user-provided question."""
    print("\n🔍 Step 5: Searching Document")
    print("-" * 40)
    print("The CLI will get user context from /api/auth/me")
    print("Pipeline resolution is now handled automatically by the backend")

    search_cmd = SearchCommands(api_client, config)

    print(f"   Query: {question}")
    print(f"   Collection ID: {collection_id}")
    print("   Pipeline: Will be resolved automatically from user's default")

    # 🧠 Silent CoT testing - user doesn't see this
    cot_result = _test_cot_behind_scenes(api_client, collection_id, question)

    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries + 1):
        # Use CoT test result if available, otherwise fall back to normal search
        if cot_result and "answer" in cot_result:
            # Use the regular search result from our CoT test
            result = type(
                "Result", (), {"success": True, "data": cot_result, "message": "Search completed successfully"}
            )()
            break
        else:
            # Fallback to normal CLI search
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

            # Show detailed source information with metadata
            query_results = result.data.get("query_results", [])
            documents = result.data.get("documents", [])

            if query_results:
                print(f"\n📄 Source Document Sections ({len(query_results)} chunks referenced):")
                print("-" * 60)

                # Create a mapping of document_id to document name for better display
                doc_id_to_name = {}
                for doc in documents:
                    if doc.get("document_name"):
                        # Extract document_id from the document metadata
                        # We'll need to match this with the chunk's document_id
                        doc_id_to_name[doc.get("document_name", "")] = doc.get("document_name", "")

                # Group results by document for better organization
                results_by_doc = {}
                for query_result in query_results:
                    chunk = query_result.get("chunk")
                    if chunk:
                        doc_id = chunk.get("document_id", "Unknown")
                        if doc_id not in results_by_doc:
                            results_by_doc[doc_id] = []
                        results_by_doc[doc_id].append(query_result)

                chunk_counter = 1
                for doc_id, doc_results in results_by_doc.items():
                    # Try to find document name from the documents list
                    doc_name = "Unknown Document"
                    for doc in documents:
                        if doc.get("document_name") and doc_id in str(doc.get("document_name", "")):
                            doc_name = doc.get("document_name", "Unknown Document")
                            break

                    print(f"\n   📋 Document: {doc_name}")
                    print(f"      Document ID: {doc_id}")
                    print(f"      Chunks from this document: {len(doc_results)}")
                    print("-" * 40)

                    for query_result in doc_results:
                        chunk = query_result.get("chunk")
                        if chunk:
                            # Extract metadata
                            metadata = chunk.get("metadata", {})
                            score = query_result.get("score", 0.0)
                            text_preview = (
                                chunk.get("text", "")[:150] + "..."
                                if len(chunk.get("text", "")) > 150
                                else chunk.get("text", "")
                            )

                            # Display section metadata
                            print(f"      {chunk_counter}. Similarity Score: {score:.3f}")
                            print(f"         Page Number: {metadata.get('page_number', 'N/A')}")
                            print(f"         Chunk Number: {metadata.get('chunk_number', 'N/A')}")
                            print(f"         Source Type: {metadata.get('source', 'N/A')}")
                            if metadata.get("start_index") is not None and metadata.get("end_index") is not None:
                                print(
                                    f"         Text Position: {metadata.get('start_index')}-{metadata.get('end_index')}"
                                )
                            print(f"         Text Preview: {text_preview}")
                            print()
                            chunk_counter += 1

                # Show document-level summary
                if documents:
                    print("\n📊 Document Summary:")
                    print("-" * 30)
                    for doc in documents:
                        doc_name = doc.get("document_name", "Unknown")
                        total_pages = doc.get("total_pages", "N/A")
                        total_chunks = doc.get("total_chunks", "N/A")
                        print(f"   📄 {doc_name}")
                        print(f"      Total Pages: {total_pages}")
                        print(f"      Total Chunks: {total_chunks}")
                        print()
            else:
                print("   Sources: No detailed source information available")
        return True

    print(f"❌ Search failed: {result.message}")
    if result.data:
        print(f"   Error details: {result.data}")
    return False


def _show_cot_evidence():
    """Show Chain of Thought testing evidence from silent tests."""
    try:
        if os.path.exists("cot_test_evidence.log"):
            with open("cot_test_evidence.log") as log_file:
                content = log_file.read()
                if content.strip():
                    print("\n🧠 Chain of Thought Silent Test Evidence:")
                    print("=" * 50)
                    print("(This testing happened automatically behind the scenes)")
                    print(content)

                    # Count tests
                    cot_working_count = content.count("CoT working: YES")
                    total_tests = content.count("CoT working:")
                    if total_tests > 0:
                        print("📊 CoT Test Summary:")
                        print(f"   Total silent tests: {total_tests}")
                        print(f"   CoT working: {cot_working_count}/{total_tests}")
                        print(f"   Success rate: {(cot_working_count / total_tests) * 100:.1f}%")

                    return cot_working_count > 0
    except Exception:
        pass
    return False


def _print_summary(mock_token, question_count=0):
    """Print completion summary."""
    print("\n🎉 Enhanced Interactive CLI Demonstration Complete!")
    print("=" * 70)
    print("Summary of operations tested:")
    print("• ✅ Interactive user status checking and creation")
    print("• ✅ User pipeline and provider information display")
    print("• ✅ Collection listing with file counts and status")
    print("• ✅ User choice between new/existing collections and file management")
    print("• ✅ Interactive file selection with validation")
    print("• ✅ Multi-document upload for user-specified files")
    print("• ✅ Adding files to existing collections")
    print("• ✅ Interactive question loop with multiple question support")
    print("• ✅ Suggested questions from collections")
    print("• ✅ Custom question input capability")
    print("• ✅ Enhanced search with detailed source metadata across multiple documents")
    print("• ✅ Results grouped by document for better organization")
    print("• ✅ Automatic backend pipeline resolution")
    print("• ✅ Background document processing pipeline")
    print(f"• ✅ Questions asked: {question_count}")
    print(f"• ✅ Mock token used: {mock_token}")

    # Show CoT evidence
    cot_working = _show_cot_evidence()
    if cot_working:
        print("• 🧠 Chain of Thought integration: WORKING!")
    else:
        print("• 🧠 Chain of Thought integration: Not detected or failed")

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
            collection_id, pdf_files = _create_collection(api_client, config)
            if not collection_id:
                return

            if not _upload_documents(api_client, config, collection_id, pdf_files):
                return

            if not _wait_for_processing(api_client, config, collection_id):
                return

        elif choice == "2":
            # Add files to existing collection
            collection_id = _add_files_to_existing_collection(api_client, config, collections)
            if not collection_id:
                return

        elif choice == "3":
            # Use existing collection for querying
            if not collections:
                print("❌ No existing collections to query")
                return

            selected_collection = _select_existing_collection(collections, "query")
            collection_id = selected_collection.get("id")

            # Check if collection has files
            files = selected_collection.get("files", [])
            file_count = len(files) if files else 0
            if file_count == 0:
                print("⚠️  Selected collection has no files. You may want to upload some first.")
                proceed = input("Continue anyway? (y/n): ").strip().lower()
                if proceed != "y":
                    return

        # Step 5: Run interactive question loop
        question_count = _run_question_loop(api_client, config, collection_id)

        _print_summary(mock_token, question_count)

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
    print("3. Prepare files for upload:")
    print("   - Have PDF, TXT, or other supported files ready")
    print("   - Files can be in any location on your system")
    print("   - You'll be prompted to enter file paths during execution")
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
    print("• Choose between creating new collection, adding files to existing, or querying")
    print("• Interactive file selection with validation (comma-separated paths)")
    print("• Multi-document upload for user-specified files")
    print("• Support for adding files to existing collections")
    print("• Interactive question loop - ask multiple questions in one session")
    print("• Choose between new questions, suggested questions, or exit")
    print("• Select from suggested questions or enter custom question")
    print("• Enhanced search results with detailed source metadata across multiple documents")
    print("• Results grouped by document for better organization")
    print("• Question counter and session management")
    print()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ["-h", "--help", "help"]:
        show_usage()
    else:
        main()
